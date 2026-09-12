"""決算書 第五冊 -> data/processed/city_fin.csv

One row per (fiscal year, 市立幼兒園, statement, account) from the 基金來源/用途明細表.
Pages with a usable text layer are parsed directly. Some sections are scanned or carry a
corrupted text layer (FY113 三峽/五股, FY114 新莊/土城/蘆洲); those fall back to OCR.

    python -m pipeline.s1_city
"""
import csv
import re
from collections import Counter

import pypdfium2 as pdfium

from .common.ocr import group_lines, ocr_page, page_string
from .common.pdf_text import page_lines
from .common.roster import CITY
from .common.text import parse_amount, squash
from .common.vocab import CITY as VOCAB, city_account
from .config import OUT_DIR
from .extract import extract

YEARS = (112, 113, 114)
ORDER = list(CITY)
TABLES = {"基金來源明細表": "來源", "基金用途明細表": "用途"}
ROW_RE = re.compile(r"(?<!\d)\d{0,4}\s*([一-鿿（(][一-鿿（）()、之及與]{1,14})\s+(-|[\d,]+)\s+(-|[\d,]+)")
HEADER_RE = re.compile(r"新北市地方教育發展基金[—\-–─]?新北市立(\S{2,3}?)幼兒園")
FIELDS = ["fiscal_year", "inst_id", "inst", "table", "account", "parent", "kind",
          "budget", "actual", "page", "source", "verified"]


def _row(year, inst, table, account, budget, actual, page, source, verified):
    parent, kind = VOCAB[account]
    return dict(fiscal_year=year, inst_id=CITY[inst], inst=inst, table=table, account=account,
                parent=parent, kind="rev" if table == "來源" else kind, budget=budget, actual=actual,
                page=page, source=source, verified=verified)


def parse_text(pdf, year):
    """Rows from text-layer pages, plus the pages whose header names each institution."""
    rows, mentions = [], {inst: [] for inst in CITY}
    for pno in range(1, len(pdf) + 1):
        lines = page_lines(pdf[pno - 1])
        head = squash("".join(lines[:8]))
        if pno > 2:  # p1–2 are the volume's own cover and table of contents
            for inst in CITY:
                if f"新北市立{inst}幼兒園" in head:
                    mentions[inst].append(pno)
        header = HEADER_RE.search(head)
        table = next((short for title, short in TABLES.items() if title in head), None)
        if not header or not table or header.group(1) not in CITY or "目次" in head:
            continue
        for line in lines:
            m = ROW_RE.search(line)
            if not m or not (account := city_account(m.group(1))):
                continue
            budget, actual = (0 if v == "-" else int(v.replace(",", "")) for v in m.group(2, 3))
            diff = actual - budget
            verified = diff == 0 or f"{abs(diff):,}" in line  # printed 比較增減 sits on the same row
            rows.append(_row(year, header.group(1), table, account, budget, actual, pno, "text", verified))
    return rows, mentions


def parse_ocr_statement(boxes):
    """(account, budget, actual, verified) rows from an OCR'd 來源/用途明細表 page."""
    budget_hdr = next((b for b in boxes if "預算" in b.text), None)
    actual_hdr = next((b for b in boxes if "決算" in b.text), None)
    if not budget_hdr or not actual_hdr:
        return []
    diff_hdr = next((b for b in boxes if ("增減" in b.text or "比較" in b.text) and b.x > actual_hdr.x), None)
    cols = {"budget": budget_hdr.x, "actual": actual_hdr.x,
            "diff": diff_hdr.x if diff_hdr else 2 * actual_hdr.x - budget_hdr.x}
    out = []
    for line in group_lines(boxes):
        labels = [b for b in line if re.search(r"[一-鿿]{2,}", b.text) and b.x < cols["budget"] - 40]
        if not labels or not (account := city_account(labels[0].text, fuzzy=True)):
            continue
        values = {}
        for b in line:
            if b.x > cols["budget"] - 150 and (v := parse_amount(b.text)) is not None:
                values.setdefault(min(cols, key=lambda k: abs(cols[k] - b.x)), v)
        if "budget" not in values and "actual" not in values:
            continue
        budget, actual, diff = values.get("budget", 0), values.get("actual", 0), values.get("diff")
        verified = actual - budget == diff if diff is not None else budget == actual
        out.append((account, budget, actual, verified))
    return out


def section_window(inst, mentions, n_pages):
    """Pages after the previous institution's last header and before the next one's first."""
    i = ORDER.index(inst)
    before = [max(mentions[o]) for o in ORDER[:i] if mentions[o]]
    after = [min(mentions[o]) for o in ORDER[i + 1:] if mentions[o]]
    return range(max(before) + 1 if before else 3, min(after) if after else n_pages + 1)


def parse_ocr(pdf, year, inst, mentions):
    rows = []
    for pno in section_window(inst, mentions, len(pdf)):
        text = page_string(ocr_page(pdf[pno - 1], 1.4))
        table = next((short for title, short in TABLES.items() if title[2:6] in text), None)
        if not table or "目次" in text:
            continue
        named = [other for other in CITY if other in text]
        if named and inst not in named:  # belongs to a neighbouring section that is also being OCR'd
            continue
        for account, budget, actual, ok in parse_ocr_statement(ocr_page(pdf[pno - 1], 3.0)):
            rows.append(_row(year, inst, table, account, budget, actual, pno, "ocr", ok))
    return rows


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        key = (r["fiscal_year"], r["inst_id"], r["table"], r["account"])
        if key not in seen:  # continuation pages repeat the statement's totals
            seen.add(key)
            out.append(r)
    return out


def main():
    out = []
    for year in YEARS:
        pdf = pdfium.PdfDocument(extract(f"資料集/公校/{year}年度決算書/第5冊/{year}年決算書第五冊.pdf"))
        rows, mentions = parse_text(pdf, year)
        found = {r["inst"] for r in rows}
        for inst in CITY:
            if inst not in found and mentions[inst]:
                rows += parse_ocr(pdf, year, inst, mentions)
        rows = dedupe(rows)
        out += rows

        got = {r["inst"] for r in rows}
        absent = [i for i in CITY if not mentions[i]]
        unresolved = [i for i in CITY if i not in got and i not in absent]
        tally = Counter((r["source"], r["verified"]) for r in rows)
        print(f"FY{year}: {len(got)}/{len(CITY)} institutions, {len(rows)} rows | "
              f"text {tally['text', True]}✓ {tally['text', False]}✗ | "
              f"ocr {tally['ocr', True]}✓ {tally['ocr', False]}✗ | "
              f"not in volume: {' '.join(absent) or '-'} | unresolved: {' '.join(unresolved) or '-'}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "city_fin.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)
    print(f"wrote {path} ({len(out)} rows)")


if __name__ == "__main__":
    main()
