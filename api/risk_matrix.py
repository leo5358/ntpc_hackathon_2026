"""教育部風險管理推動作業原則之評量標準與判斷基準。

資料來源（原文附件）：
- 附件2：教育部風險可能性評量標準表、教育部風險影響程度評量標準表
- 附件3：教育部風險判斷基準及其風險容忍度（風險值(R) = 可能性(L) x 影響程度(I)，R<=4 予以容忍）
- 附件4：教育部現有(殘餘)風險圖像（3x3 矩陣）
- 附件7：風險評估及處理彙總表（本模組提供其風險等級欄位之計算）

本模組只負責「等級 -> 風險值 -> 處理策略」的官方對照，不涉及模型推論；
由模型輸出映射到 L/I 的規則放在 api/services/report_builder.py。
"""
from typing import Any, Dict, List

# ---------------------------------------------------------
# 附件2：風險可能性評量標準表
# ---------------------------------------------------------
LIKELIHOOD_SCALE: List[Dict[str, Any]] = [
    {
        "level": 3,
        "label": "幾乎確定",
        "description": "在大部分的情況下會發生；1年內非常可能發生",
    },
    {
        "level": 2,
        "label": "可能",
        "description": "有些情況下會發生；1年內可能發生",
    },
    {
        "level": 1,
        "label": "幾乎不可能",
        "description": "只會在特殊的情況下發生；1年內不太可能發生",
    },
]

# ---------------------------------------------------------
# 附件2：風險影響程度評量標準表
# ---------------------------------------------------------
IMPACT_SCALE: List[Dict[str, Any]] = [
    {
        "level": 3,
        "label": "非常嚴重",
        "image": "國際新聞媒體報導負面新聞，單位以上主管調職或下臺",
        "personnel": "死亡",
        "protest": "抗議",
        "property_loss": "一億元以上",
        "government_operation": "非常嚴重",
    },
    {
        "level": 2,
        "label": "嚴重",
        "image": "臺灣新聞媒體報導負面新聞，院長口頭告誡",
        "personnel": "重傷",
        "protest": "團體抱怨（30人以上）",
        "property_loss": "一千萬元以上，未達一億元",
        "government_operation": "嚴重",
    },
    {
        "level": 1,
        "label": "輕微",
        "image": "區域新聞媒體報導負面新聞",
        "personnel": "輕傷",
        "protest": "個人抱怨（29人以下5人以上）",
        "property_loss": "未達一千萬元",
        "government_operation": "輕微",
    },
]

LIKELIHOOD_LABELS = {item["level"]: item["label"] for item in LIKELIHOOD_SCALE}
IMPACT_LABELS = {item["level"]: item["label"] for item in IMPACT_SCALE}

# ---------------------------------------------------------
# 附件3：風險判斷基準及其風險容忍度
# 風險容忍度 = 風險值(R) 4 以下予以容忍
# ---------------------------------------------------------
RISK_TOLERANCE_THRESHOLD = 4

RISK_JUDGEMENT: Dict[int, Dict[str, Any]] = {
    1: {
        "risk_level": "低度風險",
        "color": "#ffffff",
        "tolerable": True,
        "response": "予以容忍，以一般步驟處理",
    },
    2: {
        "risk_level": "低度風險",
        "color": "#ffffff",
        "tolerable": True,
        "response": "予以容忍，以一般步驟處理",
    },
    3: {
        "risk_level": "中度風險",
        "color": "#ccf0cc",
        "tolerable": True,
        "response": "予以容忍，並明定管理階層的責任範圍，做必要監視",
    },
    4: {
        "risk_level": "中度風險",
        "color": "#ccf0cc",
        "tolerable": True,
        "response": "予以容忍，並明定管理階層的責任範圍，做必要監視",
    },
    6: {
        "risk_level": "高度風險",
        "color": "#f5a623",
        "tolerable": False,
        "response": "管理階層需督導所屬研擬計畫並提供資源",
    },
    9: {
        "risk_level": "極度風險",
        "color": "#e60000",
        "tolerable": False,
        "response": "需立即採取行動",
    },
}


def clamp_level(level: int) -> int:
    """將任意輸入夾在官方 1~3 級距內。"""
    return max(1, min(3, int(round(level))))


def grade(likelihood: int, impact: int) -> Dict[str, Any]:
    """依附件3 計算風險值與對應處理策略。

    Args:
        likelihood: 可能性(L)，1~3。
        impact: 影響程度(I)，1~3。

    Returns:
        風險等級欄位（可直接餵入附件7 之「現有/殘餘風險等級」欄位）。
    """
    likelihood = clamp_level(likelihood)
    impact = clamp_level(impact)
    risk_value = likelihood * impact
    judgement = RISK_JUDGEMENT[risk_value]
    return {
        "likelihood": likelihood,
        "likelihood_label": LIKELIHOOD_LABELS[likelihood],
        "impact": impact,
        "impact_label": IMPACT_LABELS[impact],
        "risk_value": risk_value,
        "risk_level": judgement["risk_level"],
        "color": judgement["color"],
        "tolerable": judgement["tolerable"],
        "response": judgement["response"],
    }


def build_matrix(cells_rows: Dict[str, List[int]] = None) -> List[Dict[str, Any]]:
    """產生附件4 風險圖像的 3x3 底圖，並可標註各風險項目落點。

    Args:
        cells_rows: key 為 "L,I"，value 為落在該格的附件7 風險項目序號清單。

    Returns:
        9 個格位（由影響程度 3 -> 1、可能性 1 -> 3 排列，與附件4 版面一致）。
    """
    cells_rows = cells_rows or {}
    matrix: List[Dict[str, Any]] = []
    for impact in (3, 2, 1):
        for likelihood in (1, 2, 3):
            cell = grade(likelihood, impact)
            cell["row_seqs"] = cells_rows.get(f"{likelihood},{impact}", [])
            matrix.append(cell)
    return matrix
