"""新北市 penalty records -> data/processed/penalties_all.csv (every 新北 園) and penalties.csv (our 60)

Source: github.com/kiang/ap.ece.moe.edu.tw, a daily mirror of 全國教保資訊網 that keeps records the
official site drops once their display period ends. The raw records are snapshotted into
CACHE_DIR under today's date so the labels can be reproduced. One output row per distinct penalty;
the responsible person's name is never written out.

    python -m pipeline.s3_penalties
"""
import csv
import datetime
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from .common.roc import academic_year
from .common.roster import CITY, nonprofit_core, nonprofit_roster
from .config import CACHE_DIR, OUT_DIR

LISTING = "https://api.github.com/repos/kiang/ap.ece.moe.edu.tw/contents/docs/data/punish/新北市"
EVENT_FIELDS = ["date", "academic_year", "calendar_year", "doc_no", "law", "violation", "article", "fine_ntd"]
ALL_FIELDS = ["title"] + EVENT_FIELDS
FIELDS = ["group", "inst_id", "inst", "operator"] + EVENT_FIELDS


def fetch_json(url: str):
    request = urllib.request.Request(urllib.parse.quote(url, safe=":/%?=&"),  # download URLs carry raw CJK
                                     headers={"User-Agent": "ntpc-hackathon-pipeline"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def match(filename: str, np_roster: dict[str, str]):
    """(group, inst_id, inst, operator) if the file belongs to one of our 60 institutions."""
    stem = filename.removesuffix(".json")
    op = re.search(r"[（(]委託(.+?)辦理[）)]", stem)
    operator = op.group(1) if op else None
    if (core := nonprofit_core(stem)) in np_roster:
        return "非營利", np_roster[core], core, operator
    if (m := re.match(r"新北市立(.+?)幼兒園", stem)) and m.group(1) in CITY:  # 分班 files fold into the parent 園
        return "市立", CITY[m.group(1)], m.group(1), operator
    return None


def parse_record(record: list[str]) -> dict:
    """Event fields by content, not position: some records put the institution name where 罰鍰 usually sits."""
    fields = {"date": record[0]}
    for field in record[1:]:
        if "字第" in field:
            fields.setdefault("doc_no", field)
        elif field.startswith("幼兒教育及照顧法"):
            fields.setdefault("law", field)
        elif re.match(r"第\d+條", field):
            fields.setdefault("violation", field)
        elif "罰鍰" in field:
            fields.setdefault("fine", field)
    fine = re.search(r"([\d,]+)元", fields.get("fine", ""))
    article = re.match(r"第\d+條", fields.get("violation", ""))
    return dict(date=fields["date"], academic_year=academic_year(fields["date"]), calendar_year=int(fields["date"][:4]),
                doc_no=fields.get("doc_no"), law=fields.get("law"), violation=fields.get("violation"),
                article=article.group(0) if article else None,
                fine_ntd=int(fine.group(1).replace(",", "")) if fine else None)


def write(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    listing = fetch_json(LISTING)
    with ThreadPoolExecutor(16) as pool:
        records = dict(zip((e["name"] for e in listing), pool.map(lambda e: fetch_json(e["download_url"]), listing)))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.date.today().strftime("%Y%m%d")
    (CACHE_DIR / f"punish_新北市_{stamp}.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

    np_roster = nonprofit_roster()
    everything, ours, seen_all, seen_ours = [], [], set(), set()
    for name, recs in records.items():
        title, hit = name.removesuffix(".json"), match(name, np_roster)
        for record in recs:
            event = parse_record(record)
            # identical records repeat, within a file and (for our 60) across operator files
            if (key := (title, event["doc_no"], event["violation"])) not in seen_all:
                seen_all.add(key)
                everything.append(dict(title=title, **event))
            if hit and (key := (hit[1], event["doc_no"], event["violation"])) not in seen_ours:
                seen_ours.add(key)
                ours.append(dict(zip(("group", "inst_id", "inst", "operator"), hit), **event))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write(OUT_DIR / "penalties_all.csv", ALL_FIELDS, sorted(everything, key=lambda e: (e["title"], e["date"])))
    write(OUT_DIR / "penalties.csv", FIELDS, sorted(ours, key=lambda e: (e["inst_id"], e["date"])))
    per_group = Counter(e["group"] for e in ours)
    print(f"penalties_all.csv: {len(everything)} distinct penalties across {len(records)} 新北 園")
    print(f"penalties.csv: {len(ours)} for our roster (非營利 {per_group['非營利']}, 市立 {per_group['市立']}) "
          f"across {len({e['inst_id'] for e in ours})} institutions")


if __name__ == "__main__":
    main()
