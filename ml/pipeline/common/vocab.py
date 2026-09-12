"""Controlled account vocabularies. Row labels outside them are dropped, never guessed."""
import difflib

from .text import fullwidth_parens

# 決算書 基金來源/用途明細表 — name -> (parent, kind), kind ∈ rev | exp | capex.
CITY = {
    "基金來源": (None, "rev"),
    "財產收入": ("基金來源", "rev"), "利息收入": ("財產收入", "rev"), "財產處分收入": ("財產收入", "rev"),
    "政府撥入收入": ("基金來源", "rev"), "公庫撥款收入": ("政府撥入收入", "rev"),
    "教學收入": ("基金來源", "rev"), "學雜費收入": ("教學收入", "rev"),
    "勞務收入": ("基金來源", "rev"), "服務收入": ("勞務收入", "rev"),
    "徵收及依法分配收入": ("基金來源", "rev"), "違規罰款收入": ("徵收及依法分配收入", "rev"),
    "其他收入": ("基金來源", "rev"), "雜項收入": ("其他收入", "rev"),
    "基金用途": (None, "exp"), "學前教育計畫": ("基金用途", "exp"),
    "用人費用": ("學前教育計畫", "exp"),
    "正式員額薪資": ("用人費用", "exp"), "聘僱及兼職人員薪資": ("用人費用", "exp"),
    "超時工作報酬": ("用人費用", "exp"), "加（夜）班費": ("用人費用", "exp"), "獎金": ("用人費用", "exp"),
    "退休及卹償金": ("用人費用", "exp"), "資遣費": ("用人費用", "exp"), "提繳費": ("用人費用", "exp"),
    "福利費": ("用人費用", "exp"),
    "服務費用": ("學前教育計畫", "exp"),
    "水電費": ("服務費用", "exp"), "郵電費": ("服務費用", "exp"), "旅運費": ("服務費用", "exp"),
    "印刷裝訂與廣告費": ("服務費用", "exp"), "修理保養及保固費": ("服務費用", "exp"),
    "保險費": ("服務費用", "exp"), "一般服務費": ("服務費用", "exp"), "專業服務費": ("服務費用", "exp"),
    "公共關係費": ("服務費用", "exp"),
    "材料及用品費": ("學前教育計畫", "exp"), "使用材料費": ("材料及用品費", "exp"), "用品消耗": ("材料及用品費", "exp"),
    "地租及水租": ("租金", "exp"), "機器租金": ("租金", "exp"),
    "交通及運輸設備租金": ("租金", "exp"), "雜項設備租金": ("租金", "exp"),
    "會費": ("會費捐助", "exp"), "捐助、補助與獎助": ("會費捐助", "exp"), "補貼、獎勵、慰問、照護": ("會費捐助", "exp"),
    "稅捐及規費": ("學前教育計畫", "exp"), "規費": ("稅捐及規費", "exp"),
    "其他": ("學前教育計畫", "exp"), "其他支出": ("其他", "exp"),
    "建築及設備計畫": ("基金用途", "capex"), "購建固定資產": ("建築及設備計畫", "capex"),
    "土地改良物": ("購建固定資產", "capex"), "房屋及建築": ("購建固定資產", "capex"),
    "機械及設備": ("購建固定資產", "capex"), "交通及運輸設備": ("購建固定資產", "capex"),
    "雜項設備": ("購建固定資產", "capex"),
}
_CITY_LONGEST_FIRST = sorted(CITY, key=len, reverse=True)


def city_account(label: str, fuzzy: bool = False) -> str | None:
    """Canonical 決算書 account for a row label.

    Text-layer labels can run into the 備註 column ("公共關係費預算金額"), so match on prefix,
    longest first. OCR labels (fuzzy=True) may also have characters dropped or swapped.
    """
    label = fullwidth_parens(label.lstrip("0123456789"))
    hit = next((name for name in _CITY_LONGEST_FIRST if label.startswith(name)), None)
    if hit or not fuzzy:
        return hit
    return next(iter(difflib.get_close_matches(label, CITY, n=1, cutoff=0.75)), None)


# 非營利園 收支餘絀表 — canonical label -> kind.
NONPROFIT = {
    "教保費收入": "rev", "教保費收入減項": "rev", "延長照顧服務收入淨額": "rev",
    "利息收入": "rev", "其他收入": "rev",
    "收入合計": "rev_total",
    "人事費": "exp", "業務費": "exp", "材料費": "exp", "維護費": "exp", "修繕購置費": "exp",
    "公共事務管理費": "exp", "土地、建物、設施與設備之租金": "exp", "雜支": "exp", "行政管理費": "exp",
    "業務發展費": "exp",
    "延長照顧服務支出": "exp", "其他支出": "exp", "呆帳損失": "exp",
    "支出合計": "exp_total",
    "本期稅前餘絀": "surplus", "所得稅費用": "tax", "本期稅後餘絀": "surplus_after_tax",
}
# Labels from older reports (110–111學年度).
NONPROFIT_ALIASES = {"延後托育收入淨額": "延長照顧服務收入淨額", "延後托育支出": "延長照顧服務支出"}
_NP_LABELS = list(NONPROFIT) + list(NONPROFIT_ALIASES)
_NP_LONGEST_FIRST = sorted(_NP_LABELS, key=len, reverse=True)


def nonprofit_account(label: str) -> str | None:
    """Exact, then closest (OCR drops characters: 修購置費), then prefix (其他收入-其它)."""
    hit = label if label in NONPROFIT or label in NONPROFIT_ALIASES else None
    hit = hit or next(iter(difflib.get_close_matches(label, _NP_LABELS, n=1, cutoff=0.7)), None)
    hit = hit or next((name for name in _NP_LONGEST_FIRST if label.startswith(name)), None)
    return NONPROFIT_ALIASES.get(hit, hit)
