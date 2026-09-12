"""輿情 corpus -> data/processed/opinion_docs.jsonl, data/labels/opinion_gold_todo.csv

Two kinds of document, both from Google News RSS:
    institution  items returned for an exact-phrase query on one of our 60 institutions (inference set)
    domain       kindergarten news from broad topical queries, nationwide (training set)
Every document gets weak topic and polarity labels from keyword rules. The rules are the fallback
labeller; the hand-labelled gold set (a sample written to data/labels/) is what the model is scored on.
Annotators fill its `topic` column with one or more of TOPICS joined by "|" (or 無關) and `polarity`
with -1 / 0 / 1.
PTT was probed and returns almost nothing for these institutions, so it is not collected.

    python -m pipeline.nlp.collect
"""
import csv
import email.utils
import hashlib
import json
import random
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from ..common.roster import CITY, nonprofit_roster
from ..config import OUT_DIR, REPO

TOPICS = ["不當管教", "餐食衛生", "收費爭議", "人力不足", "設施安全", "行政立案"]  # plus "無關"
KEYWORDS = {
    "不當管教": ["不當對待", "不當管教", "體罰", "虐童", "虐待", "打罵", "罰站", "霸凌", "拉扯", "摑", "推倒", "綁"],
    "餐食衛生": ["衛生保健", "食物中毒", "腸病毒", "諾羅", "餐點", "午餐", "點心", "過期", "蟑螂", "廚房", "群聚感染"],
    "收費爭議": ["收費", "退費", "學費", "雜費", "漲價", "收費數額"],
    "人力不足": ["師生比", "離職", "人力", "缺老師", "缺師", "師資", "未具資格", "配置教師", "代課", "流動率", "廚工"],
    "設施安全": ["受傷", "意外", "跌倒", "娃娃車", "幼童專用車", "遺留", "悶死", "安全相關管理", "設施", "火災", "墜落", "骨折"],
    "行政立案": ["立案", "超收", "招收人數", "評鑑", "未報", "備查", "未經核准", "課後照顧", "負責人"],
}
NEGATIVE = ["不當", "虐", "體罰", "受傷", "投訴", "抗議", "爭議", "違規", "裁罰", "罰鍰", "怒", "控訴", "疑似",
            "調查", "停課", "撤換", "解約", "糾紛", "檢舉", "失職", "涉", "起訴"]
POSITIVE = ["揭牌", "啟用", "開幕", "畢業", "優良", "獲獎", "表揚", "增班", "招生", "親子", "感恩", "溫馨", "特色"]
DOMAIN_QUERIES = [
    "幼兒園 不當對待", "幼兒園 虐童", "幼兒園 體罰", "幼兒園 裁罰", "幼兒園 違規", "幼兒園 食物中毒",
    "幼兒園 腸病毒", "幼兒園 衛生", "幼兒園 收費", "幼兒園 退費", "幼兒園 師資 離職", "幼兒園 師生比",
    "幼兒園 娃娃車", "幼兒園 意外 受傷", "幼兒園 超收", "非營利幼兒園", "公幼", "新北 幼兒園",
    "準公共化 幼兒園", "幼兒園 評鑑",
]
RSS = "https://news.google.com/rss/search?"
HEADERS = {"User-Agent": "Mozilla/5.0 (ntpc-hackathon research crawler)"}


def weak_labels(text: str) -> dict:
    topics = [t for t, words in KEYWORDS.items() if any(w in text for w in words)]
    neg = sum(w in text for w in NEGATIVE)
    pos = sum(w in text for w in POSITIVE)
    return dict(weak_topics=topics, weak_polarity=-1 if neg > pos else (1 if pos > neg else 0))


def search(query: str) -> list[dict]:
    url = RSS + urllib.parse.urlencode({"q": query, "hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as resp:
        channel = ET.fromstring(resp.read())
    items = []
    for item in channel.findall("./channel/item"):
        source = item.findtext("source") or ""
        title = (item.findtext("title") or "").removesuffix(f" - {source}").strip()
        published = email.utils.parsedate_to_datetime(item.findtext("pubDate")).date().isoformat()
        items.append(dict(title=title, source=source, published=published, url=item.findtext("link") or ""))
    return items


def institution_queries() -> list[tuple[str, str, str]]:
    """(inst_id, exact name, query) for the 60 institutions."""
    queries = [(code, f"{core}非營利幼兒園", f'"{core}非營利幼兒園"') for core, code in nonprofit_roster().items()]
    queries += [(code, f"新北市立{name}幼兒園", f'"新北市立{name}幼兒園"') for name, code in CITY.items()]
    return queries


def main():
    docs = {}

    def add(item, **extra):
        key = hashlib.sha1(item["title"].encode()).hexdigest()[:16]  # the same story recurs across queries
        if key not in docs:
            docs[key] = dict(id=key, **item, **extra, **weak_labels(item["title"]))
        elif extra.get("inst_id") and not docs[key].get("inst_id"):
            docs[key].update(extra)

    for inst_id, name, query in institution_queries():
        for item in search(query):
            add(item, kind="institution", inst_id=inst_id, query=query, name_in_title=name in item["title"])
        time.sleep(1)
    for query in DOMAIN_QUERIES:
        for item in search(query):
            add(item, kind="domain", inst_id=None, query=query, name_in_title=False)
        time.sleep(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = sorted(docs.values(), key=lambda d: (d["kind"], d["published"]))
    with open(OUT_DIR / "opinion_docs.jsonl", "w", encoding="utf-8") as f:
        for d in rows:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    gold = REPO / "data" / "labels" / "opinion_gold_todo.csv"
    if not gold.exists():  # never overwrite a file people may already be annotating
        gold.parent.mkdir(parents=True, exist_ok=True)
        inst = [d for d in rows if d["kind"] == "institution"]
        domain = [d for d in rows if d["kind"] == "domain"]
        sample = inst + random.Random(0).sample(domain, min(len(domain), max(0, 400 - len(inst))))
        with open(gold, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "title", "kind", "topic", "polarity", "annotator"])
            for d in sample:
                w.writerow([d["id"], d["title"], d["kind"], "", "", ""])

    inst_docs = [d for d in rows if d["kind"] == "institution"]
    covered = {d["inst_id"] for d in inst_docs if d["name_in_title"]}
    topic_counts = {t: sum(t in d["weak_topics"] for d in rows) for t in TOPICS}
    print(f"opinion_docs.jsonl: {len(rows)} documents ({len(inst_docs)} institution, {len(rows) - len(inst_docs)} domain)")
    print(f"institutions named in at least one headline: {len(covered)}/60")
    print(f"weak topics: {topic_counts}; untagged: {sum(not d['weak_topics'] for d in rows)}")
    print(f"weak polarity: neg {sum(d['weak_polarity'] < 0 for d in rows)}, neutral {sum(d['weak_polarity'] == 0 for d in rows)}, "
          f"pos {sum(d['weak_polarity'] > 0 for d in rows)}")


if __name__ == "__main__":
    main()
