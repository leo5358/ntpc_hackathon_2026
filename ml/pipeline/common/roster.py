"""The 60 institutions in scope: 22 市立幼兒園 and 38 非營利園."""
import re
from functools import lru_cache

from ..extract import members

# Name between 新北市立 and 幼兒園 -> 分基金 code, from the FY112 決算書 第一冊 總目錄.
CITY = {
    "板橋": "13601", "三重": "13602", "中和": "13603", "永和": "13604", "新莊": "13605",
    "新店": "13606", "樹林": "13607", "鶯歌": "13608", "三峽": "13609", "淡水": "13610",
    "瑞芳": "13611", "土城": "13612", "蘆洲": "13613", "五股": "13614", "泰山": "13615",
    "林口": "13616", "深坑": "13617", "三芝": "13620", "八里": "13622", "金山": "13626",
    "萬里": "13627", "烏來": "13628",
}

_REPORT_RE = re.compile(r"非營利園財報/(\d{3})學年度/(N\d{2})(.+?)_\d{3}學年度財務報告\.pdf$")
_NP_TITLE_RE = re.compile(r"新北市(?:政府)?(.+?)非營利幼兒園")


def nonprofit_core(title: str) -> str | None:
    """Roster name inside an official title: '新北市政府板橋員工子女非營利幼兒園（委託…）' -> '板橋員工子女'."""
    m = _NP_TITLE_RE.match(title)
    return m.group(1) if m else None


@lru_cache(maxsize=1)
def nonprofit_reports() -> list[tuple[str, str, int, str]]:
    """(N##, 園名, 學年度, archive member) for every 非營利園 report, sorted."""
    return sorted(
        (m.group(2), m.group(3), int(m.group(1)), name)
        for name in members()
        if (m := _REPORT_RE.search(name))
    )


def nonprofit_roster() -> dict[str, str]:
    """園名 -> N## (codes are stable across years)."""
    return {name: code for code, name, _, _ in nonprofit_reports()}
