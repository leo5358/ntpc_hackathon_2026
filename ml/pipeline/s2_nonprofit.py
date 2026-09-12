"""非營利園 財務報告 (scanned) -> data/processed/nonprofit_fin.csv, nonprofit_pages.csv

Each report carries a 收支餘絀表 for its own 學年度 and, on the next page, the prior year's —
both with 預算數 / 決算數 / 差異數 / 執行率. They are located by low-resolution OCR, read at high
resolution, and self-checked twice: 差異 = 決算 − 預算 on every row, and the rows must sum to
收入合計 / 支出合計. Results are cached per report, so a rerun only OCRs what is new.

    python -m pipeline.s2_nonprofit --workers 6
"""
import argparse
import csv
import json
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import pypdfium2 as pdfium

from .common import ocr
from .common.ocr import group_lines, ocr_page, page_string
from .common.roster import nonprofit_reports
from .common.text import parse_amount
from .common.vocab import NONPROFIT, nonprofit_account
from .config import CACHE_DIR, OUT_DIR
from .extract import extract

CACHE = CACHE_DIR / "nonprofit_ocr"
MARKERS = ("預算", "決算", "執行率", "人事費", "支出合計", "收入合計", "餘絀")
PERIOD_RE = re.compile(r"(\d{3})\.(\d{1,2})\.(\d{1,2})[~～\-至]+(\d{3})\.(\d{1,2})\.(\d{1,2})")
ROW_FIELDS = ["inst_id", "inst", "report_year", "page", "academic_year", "label", "account", "kind",
              "budget", "actual", "diff", "row_ok"]
PAGE_FIELDS = ["inst_id", "inst", "report_year", "page", "academic_year", "period", "n_rows", "n_rows_ok",
               "rev_total_ok", "exp_total_ok"]


def _is_statement(pdf, idx, scale):
    return sum(k in page_string(ocr_page(pdf[idx], scale)) for k in MARKERS) >= 5


def locate(pdf) -> list[int]:
    """0-based indices of the 收支餘絀表 pages (current year, then prior year when present).

    Nearly every report has them on p6–p7, straight after the 資產負債表, so likely positions are
    tried first, and once one statement is found only its neighbours are checked for the other.
    A typical report costs three low-resolution OCR passes.
    """
    n = len(pdf)

    def is_statement(i, scale):
        return 0 <= i < n and _is_statement(pdf, i, scale)

    for scale in (1.3, 1.8):
        for i in (5, 6, 4, 7, 3, 8, 2, 9, 10, 11, 12, 13):
            if is_statement(i, scale):
                for j in (i + 1, i - 1):
                    if is_statement(j, 1.3) or is_statement(j, 1.8):
                        return sorted([i, j])
                return [i]  # a first-year 園 has no prior-year statement
    return []


def parse_statement(boxes):
    """(rows, period match) from an OCR'd 收支餘絀表, or None if its column header is not found."""
    budget_hdr = next((b for b in boxes if "預算" in b.text), None)
    if budget_hdr is None:
        return None
    header_band = [b for b in boxes if abs(b.y - budget_hdr.y) <= 4 * budget_hdr.h]
    cols = {"budget": budget_hdr.x}
    for key, col in (("決算", "actual"), ("差", "diff"), ("執行", "rate"), ("率", "rate")):
        hit = next((b for b in header_band if key in b.text and b.x > budget_hdr.x), None)
        if hit and col not in cols:
            cols[col] = hit.x
    if "actual" not in cols:
        return None

    rows = []
    for line in group_lines(boxes):
        labels = [b for b in line if re.search(r"[一-鿿]{2,}", b.text) and b.x < cols["budget"] - 60]
        if not labels:
            continue
        values = {}
        for b in line:
            if b.x > cols["budget"] - 150 and (v := parse_amount(b.text)) is not None:
                col = min(cols, key=lambda k: abs(cols[k] - b.x))
                if col != "rate":
                    values.setdefault(col, v)
        if values:
            rows.append(dict(label=labels[0].text, account=nonprofit_account(labels[0].text),
                             budget=values.get("budget"), actual=values.get("actual"), diff=values.get("diff")))
    return rows, PERIOD_RE.search(page_string(boxes))


def row_ok(r) -> bool:
    budget, actual, diff = r["budget"], r["actual"], r["diff"]
    if actual is not None and diff is not None:
        return actual - (budget or 0) == diff
    return budget is not None and budget == actual


def total_checks(rows) -> tuple[bool, bool]:
    def check(part, total):
        stated = next((r["actual"] for r in rows if r["account"] == total), None)
        summed = sum(r["actual"] or 0 for r in rows if NONPROFIT.get(r["account"]) == part)
        return stated is not None and stated == summed
    return check("rev", "收入合計"), check("exp", "支出合計")


def finalize(rows: list[dict]) -> list[dict]:
    """Re-derive accounts and checks from the OCR'd labels and figures.

    Applied to cached results as well, so a vocabulary fix takes effect without OCRing again.
    A 決算數 printed as "-" reads as blank; with 預算數 and 差異數 both present it is recovered.
    """
    out = []
    for r in rows:
        actual = r["actual"]
        if actual is None and r["budget"] is not None and r["diff"] is not None:
            actual = r["budget"] + r["diff"]
        row = dict(label=r["label"], account=nonprofit_account(r["label"]),
                   budget=r["budget"], actual=actual, diff=r["diff"])
        row["ok"] = row_ok(row)
        out.append(row)
    return out


def refresh(result: dict) -> dict:
    for page in result["pages"]:
        page["rows"] = finalize(page["rows"])
        page["rev_total_ok"], page["exp_total_ok"] = total_checks(page["rows"])
    return result


def academic_year(period, fallback: int) -> int:
    if not period:
        return fallback
    start_year, start_month = int(period.group(1)), int(period.group(2))
    return start_year if start_month >= 8 else start_year - 1


def process_report(job) -> dict:
    inst_id, inst, year, member = job
    cache = CACHE / f"{inst_id}_{year}.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass  # left half-written by an interrupted run; redo the report

    started = time.perf_counter()
    pdf = pdfium.PdfDocument(extract(member))
    pages = []
    for idx in locate(pdf):
        parsed = parse_statement(ocr_page(pdf[idx], 3.0))
        if parsed is None:
            continue
        rows, period = parsed
        if not any(r["account"] == "支出合計" for r in rows):
            continue
        rev_ok, exp_ok = total_checks(rows)
        pages.append(dict(page=idx + 1, academic_year=academic_year(period, year - len(pages)),
                          period=period.group(0) if period else "", rev_total_ok=rev_ok, exp_total_ok=exp_ok,
                          rows=[dict(r, ok=row_ok(r)) for r in rows]))

    result = dict(inst_id=inst_id, inst=inst, report_year=year, n_pages=len(pdf), pages=pages,
                  seconds=round(time.perf_counter() - started, 1))
    CACHE.mkdir(parents=True, exist_ok=True)
    partial = cache.with_suffix(".tmp")
    partial.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    partial.replace(cache)
    return result


def write_outputs(results):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "nonprofit_fin.csv", "w", newline="", encoding="utf-8") as rf, \
         open(OUT_DIR / "nonprofit_pages.csv", "w", newline="", encoding="utf-8") as pf:
        rows_out = csv.DictWriter(rf, fieldnames=ROW_FIELDS)
        pages_out = csv.DictWriter(pf, fieldnames=PAGE_FIELDS)
        rows_out.writeheader()
        pages_out.writeheader()
        for res in results:
            base = dict(inst_id=res["inst_id"], inst=res["inst"], report_year=res["report_year"])
            for p in res["pages"]:
                pages_out.writerow(dict(base, page=p["page"], academic_year=p["academic_year"], period=p["period"],
                                        n_rows=len(p["rows"]), n_rows_ok=sum(r["ok"] for r in p["rows"]),
                                        rev_total_ok=p["rev_total_ok"], exp_total_ok=p["exp_total_ok"]))
                for r in p["rows"]:
                    rows_out.writerow(dict(base, page=p["page"], academic_year=p["academic_year"],
                                           label=r["label"], account=r["account"] or "",
                                           kind=NONPROFIT.get(r["account"], ""), budget=r["budget"],
                                           actual=r["actual"], diff=r["diff"], row_ok=r["ok"]))


def _init_worker(threads: int) -> None:
    ocr.configure(intra_op_num_threads=threads, inter_op_num_threads=1)


def main():
    parser = argparse.ArgumentParser(description="OCR the 非營利園 收支餘絀表 pages.")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--threads", type=int, default=2, help="onnxruntime threads per worker")
    parser.add_argument("--limit", type=int, help="only the first N reports (smoke test)")
    args = parser.parse_args()

    jobs = nonprofit_reports()[: args.limit]
    results = []
    with ProcessPoolExecutor(args.workers, initializer=_init_worker, initargs=(args.threads,)) as pool:
        futures = [pool.submit(process_report, job) for job in jobs]
        for n, future in enumerate(as_completed(futures), 1):
            res = refresh(future.result())
            results.append(res)
            pages = ", ".join(f"p{p['page']}→{p['academic_year']}"
                              f"{'✓' if p['rev_total_ok'] and p['exp_total_ok'] else '✗'}" for p in res["pages"])
            took = f" ({res['seconds']:.0f}s)" if "seconds" in res else ""
            print(f"[{n}/{len(jobs)}] {res['inst_id']}{res['inst']} {res['report_year']}: "
                  f"{pages or 'NO STATEMENT FOUND'}{took}", flush=True)

    results.sort(key=lambda r: (r["inst_id"], r["report_year"]))
    write_outputs(results)
    pages = [p for r in results for p in r["pages"]]
    rows = [row for p in pages for row in p["rows"]]
    print(f"\n{len(results)} reports, {sum(not r['pages'] for r in results)} without a statement; "
          f"{len(pages)} pages, {sum(p['rev_total_ok'] and p['exp_total_ok'] for p in pages)} with both totals "
          f"reconciling; {len(rows)} rows, {sum(r['ok'] for r in rows)} self-verified, "
          f"{sum(r['account'] is None for r in rows)} with an unknown label")


if __name__ == "__main__":
    main()
