"""Opinion crawler module.

Collects public mentions from Google News RSS, PTT BabyMother, and Dcard.
"""
import email.utils
import json
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("pipeline.nlp.collect")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


@dataclass
class RawOpinionDoc:
    id: str
    source: str  # google_news, ptt, dcard
    title: str
    url: str
    published_date: str  # YYYY-MM-DD
    snippet: str
    query: str
    raw_content: Optional[str] = None


def parse_rfc822_date(date_str: str) -> str:
    """Convert RFC 822 date string (RSS) to YYYY-MM-DD."""
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def fetch_google_news(query: str, max_results: int = 10) -> List[RawOpinionDoc]:
    """Fetch news articles from Google News RSS by search query."""
    encoded_query = urllib.parse.quote(f"{query} 幼兒園")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    logger.info("Fetching Google News RSS: %s", url)

    docs: List[RawOpinionDoc] = []
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if resp.status_code != 200:
            logger.warning("Google News RSS returned status %d", resp.status_code)
            return docs

        root = ET.fromstring(resp.content)
        items = root.findall("./channel/item")
        for idx, item in enumerate(items[:max_results]):
            title = item.findtext("title", default="").strip()
            link = item.findtext("link", default="").strip()
            pub_date = item.findtext("pubDate", default="").strip()
            desc = item.findtext("description", default="").strip()

            # Clean HTML tags in description
            soup = BeautifulSoup(desc, "html.parser")
            clean_snippet = soup.get_text(separator=" ").strip()

            doc_id = f"gnews_{int(datetime.now().timestamp())}_{idx}"
            docs.append(
                RawOpinionDoc(
                    id=doc_id,
                    source="google_news",
                    title=title,
                    url=link,
                    published_date=parse_rfc822_date(pub_date),
                    snippet=clean_snippet[:500],
                    query=query,
                )
            )
    except Exception as e:
        logger.error("Error fetching Google News for query '%s': %s", query, e)

    return docs


def fetch_ptt_babymother(query: str, max_pages: int = 2) -> List[RawOpinionDoc]:
    """Search and crawl posts from PTT BabyMother board."""
    docs: List[RawOpinionDoc] = []
    base_url = "https://www.ptt.cc"
    cookies = {"over18": "1"}

    try:
        encoded_query = urllib.parse.quote(query)
        search_url = f"{base_url}/bbs/BabyMother/search?q={encoded_query}"
        logger.info("Searching PTT BabyMother: %s", search_url)

        resp = requests.get(search_url, headers=DEFAULT_HEADERS, cookies=cookies, timeout=10)
        if resp.status_code != 200:
            return docs

        soup = BeautifulSoup(resp.text, "html.parser")
        entries = soup.select("div.r-ent")

        for idx, ent in enumerate(entries[: 10 * max_pages]):
            title_tag = ent.select_one("div.title a")
            if not title_tag:
                continue
            title = title_tag.text.strip()
            post_url = base_url + title_tag["href"]
            date_tag = ent.select_one("div.date")
            pub_date = (date_tag.text.strip() if date_tag else "") or datetime.now().strftime("%m/%d")

            # Format to YYYY-MM-DD
            year = datetime.now().year
            parts = [p.strip() for p in pub_date.split("/") if p.strip()]
            if len(parts) == 2:
                formatted_date = f"{year}-{int(parts[0]):02d}-{int(parts[1]):02d}"
            else:
                formatted_date = datetime.now().strftime("%Y-%m-%d")

            doc_id = f"ptt_{int(datetime.now().timestamp())}_{idx}"
            docs.append(
                RawOpinionDoc(
                    id=doc_id,
                    source="ptt",
                    title=title,
                    url=post_url,
                    published_date=formatted_date,
                    snippet=f"PTT 媽寶板討論: {title}",
                    query=query,
                )
            )
    except Exception as e:
        logger.error("Error crawling PTT for query '%s': %s", query, e)

    return docs


def fetch_dcard_posts(query: str, limit: int = 5) -> List[RawOpinionDoc]:
    """Search public posts on Dcard parenting forum."""
    docs: List[RawOpinionDoc] = []
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.dcard.tw/service/api/v2/search/posts?query={encoded_query}&limit={limit}"

    try:
        logger.info("Querying Dcard search API: %s", search_url)
        resp = requests.get(search_url, headers=DEFAULT_HEADERS, timeout=10)
        if resp.status_code == 200:
            posts = resp.json()
            for idx, p in enumerate(posts[:limit]):
                title = p.get("title", "")
                excerpt = p.get("excerpt", "")
                post_id = p.get("id", "")
                created_at = p.get("createdAt", "")[:10] or datetime.now().strftime("%Y-%m-%d")
                doc_id = f"dcard_{post_id}_{idx}"
                docs.append(
                    RawOpinionDoc(
                        id=doc_id,
                        source="dcard",
                        title=title,
                        url=f"https://www.dcard.tw/f/parentchild/p/{post_id}",
                        published_date=created_at,
                        snippet=excerpt[:500],
                        query=query,
                    )
                )
    except Exception as e:
        logger.error("Error querying Dcard for query '%s': %s", query, e)

    return docs


def crawl_institution_opinions(inst_name: str, aliases: Optional[List[str]] = None) -> List[RawOpinionDoc]:
    """Collect opinion docs from Google News, PTT, and Dcard across queries."""
    queries = [inst_name]
    if aliases:
        queries.extend(aliases)

    all_docs: List[RawOpinionDoc] = []
    seen_titles = set()

    for q in queries:
        if not q or len(q) < 2:
            continue
        gnews = fetch_google_news(q, max_results=5)
        ptt = fetch_ptt_babymother(q, max_pages=1)
        dcard = fetch_dcard_posts(q, limit=3)

        for doc in gnews + ptt + dcard:
            cleaned_title = re.sub(r"\s+", "", doc.title)
            if cleaned_title not in seen_titles:
                seen_titles.add(cleaned_title)
                all_docs.append(doc)

    logger.info("Total crawled %d raw documents for %s", len(all_docs), inst_name)
    return all_docs


def save_raw_docs(inst_id: str, docs: List[RawOpinionDoc], output_dir: str = "data/opinion/raw"):
    """Persist crawled raw docs to local directory as JSON."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / f"{inst_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump([asdict(d) for d in docs], f, ensure_ascii=False, indent=2)
    logger.info("Saved raw opinion documents to %s", file_path)
