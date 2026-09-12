"""Centralized institution store and scoring service.

Provides consolidated institution data, historical score traces, SHAP attributions,
financial account statements, penalty logs, and what-if simulation logic.
"""
from typing import Dict, List, Optional, Any
from copy import deepcopy

# ---------------------------------------------------------
# Master Institutional Dataset (14 New Taipei City kindergartens)
# ---------------------------------------------------------
INSTITUTIONS_DB: Dict[str, Dict[str, Any]] = {
    "N07": {
        "id": "N07",
        "name": "新北市北大非營利幼兒園",
        "peer_group": "非營利園",
        "operator": "社團法人台灣幼兒早期教育協會",
        "district": "三峽區",
        "address": "新北市三峽區國學街60號",
        "latitude": 24.9458,
        "longitude": 121.3712,
        "penalty_count": 2,
        "latest_score": 78.5,
        "risk_level": "high",
        "features": {
            "penalty": 85.0,
            "residual": 78.0,
            "isolation_forest": 72.0,
            "opinion": 80.0,
            "flags": 75.0,
        },
        "history": [
            {"academic_year": 110, "score": 52.0, "p_penalty": 0.35, "residual_z": 1.10, "iso_score": 0.40, "opinion_risk": 0.20},
            {"academic_year": 111, "score": 66.5, "p_penalty": 0.50, "residual_z": 1.75, "iso_score": 0.58, "opinion_risk": 0.45},
            {"academic_year": 112, "score": 78.5, "p_penalty": 0.62, "residual_z": 2.31, "iso_score": 0.72, "opinion_risk": 0.68},
        ],
        "shap_breakdown": [
            {"feature": "understaffing_ratio", "label_zh": "用人費用占比偏低 (師生比風險)", "contribution": 0.28, "value": "41.2% (同儕中位數 58.6%)"},
            {"feature": "prior_penalties", "label_zh": "歷史違規與裁罰次數累積", "contribution": 0.22, "value": "2件 (近兩年連續受處分)"},
            {"feature": "opinion_negative_pulse", "label_zh": "社群負面輿情聲量激增", "contribution": 0.16, "value": "極性 -0.68 (午餐份量爭議)"},
            {"feature": "budget_residual_z", "label_zh": "業務費預決算殘差過大", "contribution": 0.12, "value": "z = 2.31 (短列 23.4%)"},
        ],
        "flags": [
            {"code": "UNDERSTAFFING", "title": "用人費用嚴重不足 (師生比缺失)", "description": "決算用人費用占比顯著低於同儕，反映教保員編制不足與兼職替代專任風險", "weight": 0.35, "source_ref": "112年度決算書 p.14"},
            {"code": "BUDGET_RESIDUAL", "title": "預決算殘差偏離同儕過大", "description": "業務費預算執行率偏離標準差達 2.31，預算編列不實或經費排擠", "weight": 0.25, "source_ref": "112年度決算書 p.9"},
            {"code": "BENFORD_ANOMALY", "title": "決算本福特定律檢定不通過", "description": "決算金額首位數字分布顯著偏離自然法則，疑似分批採購或湊數", "weight": 0.15, "source_ref": "112年度決算書 p.11-13"},
        ],
        "penalties": [
            {"date": "2024/05/18", "doc_no": "新北教幼字第1130982341號", "law": "幼兒教育及照顧法第42條第1項", "violation": "教保服務機構生師比不符規定，班級幼生人數超收", "fine": "處負責人新臺幣60,000元罰鍰，並令限期改善", "fine_ntd": 60000, "academic_year": 112},
            {"date": "2023/11/04", "doc_no": "新北教幼字第1122194833號", "law": "教保服務人員條例第33條", "violation": "未依規定配置專任教保員，進用未具資格人員從事教保服務", "fine": "處負責人新臺幣30,000元罰鍰", "fine_ntd": 30000, "academic_year": 112},
        ],
        "accounts": [
            {"account_code": "5101", "account_name": "教保員及助理用人費用", "category": "人事費", "budget": 6800000, "actual": 4820000, "variance": -1980000, "variance_pct": -29.1, "source_page": 14, "verified": True},
            {"account_code": "5102", "account_name": "幼童餐點食材代辦費", "category": "業務費", "budget": 1600000, "actual": 1220000, "variance": -380000, "variance_pct": -23.75, "source_page": 9, "verified": True},
            {"account_code": "5103", "account_name": "教學設備購置與維護費", "category": "設備費", "budget": 500000, "actual": 320000, "variance": -180000, "variance_pct": -36.0, "source_page": 12, "verified": True},
            {"account_code": "5104", "account_name": "水電瓦斯及公共事務費", "category": "管理費", "budget": 450000, "actual": 480000, "variance": 30000, "variance_pct": 6.67, "source_page": 15, "verified": True},
        ],
    },
    "N09": {
        "id": "N09",
        "name": "新北市安興非營利幼兒園",
        "peer_group": "非營利園",
        "operator": "財團法人新北市幼兒福利文教基金會",
        "district": "新店區",
        "address": "新北市新店區安興路88號",
        "latitude": 24.9682,
        "longitude": 121.5361,
        "penalty_count": 1,
        "latest_score": 64.2,
        "risk_level": "high",
        "features": {
            "penalty": 60.0,
            "residual": 82.0,
            "isolation_forest": 65.0,
            "opinion": 45.0,
            "flags": 55.0,
        },
        "history": [
            {"academic_year": 110, "score": 38.0, "p_penalty": 0.18, "residual_z": 0.85, "iso_score": 0.32, "opinion_risk": 0.10},
            {"academic_year": 111, "score": 49.0, "p_penalty": 0.32, "residual_z": 1.40, "iso_score": 0.48, "opinion_risk": 0.25},
            {"academic_year": 112, "score": 64.2, "p_penalty": 0.48, "residual_z": 2.15, "iso_score": 0.65, "opinion_risk": 0.35},
        ],
        "shap_breakdown": [
            {"feature": "budget_residual_z", "label_zh": "決算預算偏差異常", "contribution": 0.26, "value": "z = 2.15"},
            {"feature": "admin_expense_ratio", "label_zh": "行政管理費異常膨脹", "contribution": 0.18, "value": "成長 45%"},
            {"feature": "prior_penalties", "label_zh": "歷史違規裁罰", "contribution": 0.15, "value": "1件"},
        ],
        "flags": [
            {"code": "BUDGET_RESIDUAL", "title": "決算預算偏差異常", "description": "預算與決算數值偏差超過同儕兩倍標準差", "weight": 0.30, "source_ref": "112年度決算書 p.8"},
        ],
        "penalties": [
            {"date": "2023/12/15", "doc_no": "新北教幼字第1122481002號", "law": "幼兒教育及照顧法第25條", "violation": "未將各項收費項目及數額公告於資訊網與園所明顯處", "fine": "限期改善並處罰鍰新臺幣6,000元", "fine_ntd": 6000, "academic_year": 112},
        ],
        "accounts": [
            {"account_code": "5101", "account_name": "人事支出", "category": "人事費", "budget": 5200000, "actual": 4900000, "variance": -300000, "variance_pct": -5.77, "source_page": 10, "verified": True},
            {"account_code": "5102", "account_name": "業務與管理費", "category": "業務費", "budget": 1200000, "actual": 1750000, "variance": 550000, "variance_pct": 45.83, "source_page": 12, "verified": True},
        ],
    },
    "N11": {
        "id": "N11",
        "name": "新北市新林非營利幼兒園",
        "peer_group": "非營利園",
        "operator": "社團法人新北市幼兒教保協會",
        "district": "林口區",
        "address": "新北市林口區忠孝一路12號",
        "latitude": 25.0745,
        "longitude": 121.3654,
        "penalty_count": 1,
        "latest_score": 62.0,
        "risk_level": "high",
        "features": {
            "penalty": 58.0,
            "residual": 68.0,
            "isolation_forest": 60.0,
            "opinion": 72.0,
            "flags": 50.0,
        },
        "history": [
            {"academic_year": 110, "score": 35.0, "p_penalty": 0.15, "residual_z": 0.60, "iso_score": 0.28, "opinion_risk": 0.15},
            {"academic_year": 111, "score": 46.0, "p_penalty": 0.28, "residual_z": 1.20, "iso_score": 0.44, "opinion_risk": 0.38},
            {"academic_year": 112, "score": 62.0, "p_penalty": 0.45, "residual_z": 1.82, "iso_score": 0.60, "opinion_risk": 0.65},
        ],
        "shap_breakdown": [
            {"feature": "meal_expense_anomaly", "label_zh": "餐食代辦費支出異常", "contribution": 0.24, "value": "食材費短少 31%"},
            {"feature": "opinion_negative_pulse", "label_zh": "家長社群食品衛生陳情", "contribution": 0.20, "value": "社群評分偏低"},
        ],
        "flags": [
            {"code": "OPINION_餐食與衛生", "title": "餐食代辦費支出異常", "description": "幼童餐點代辦費決算顯著低於預算，且有家長投訴食材新鮮度", "weight": 0.28, "source_ref": "112年度決算書 p.11"},
        ],
        "penalties": [
            {"date": "2024/01/10", "doc_no": "新北教幼字第1130051234號", "law": "食品安全衛生管理法規暨幼照法", "violation": "廚房留樣保存未落實，食材未離地存放", "fine": "糾正並處限期改善", "fine_ntd": 0, "academic_year": 112},
        ],
        "accounts": [
            {"account_code": "5101", "account_name": "人事支出", "category": "人事費", "budget": 4600000, "actual": 4500000, "variance": -100000, "variance_pct": -2.17, "source_page": 8, "verified": True},
            {"account_code": "5102", "account_name": "幼兒餐點代辦費", "category": "業務費", "budget": 1400000, "actual": 966000, "variance": -434000, "variance_pct": -31.0, "source_page": 11, "verified": True},
        ],
    },
    "N12": {
        "id": "N12",
        "name": "新北市昌福非營利幼兒園",
        "peer_group": "非營利園",
        "operator": "社團法人台灣兒童照顧關懷學會",
        "district": "鶯歌區",
        "address": "新北市鶯歌區國慶街100號",
        "latitude": 24.9546,
        "longitude": 121.3533,
        "penalty_count": 1,
        "latest_score": 42.5,
        "risk_level": "medium",
        "features": {
            "penalty": 50.0,
            "residual": 40.0,
            "isolation_forest": 42.0,
            "opinion": 35.0,
            "flags": 45.0,
        },
        "history": [
            {"academic_year": 110, "score": 30.0, "p_penalty": 0.12, "residual_z": 0.40, "iso_score": 0.25, "opinion_risk": 0.10},
            {"academic_year": 111, "score": 36.0, "p_penalty": 0.20, "residual_z": 0.80, "iso_score": 0.35, "opinion_risk": 0.20},
            {"academic_year": 112, "score": 42.5, "p_penalty": 0.30, "residual_z": 0.95, "iso_score": 0.42, "opinion_risk": 0.28},
        ],
        "shap_breakdown": [
            {"feature": "operator_churn", "label_zh": "受託經營單位更迭", "contribution": 0.20, "value": "兩年內換約"},
        ],
        "flags": [
            {"code": "OPERATOR_CHURN", "title": "受託經營單位更迭", "description": "非營利幼兒園受託法人更換，行政交接處於穩定期", "weight": 0.20, "source_ref": "契約審查紀錄"},
        ],
        "penalties": [
            {"date": "2023/09/20", "doc_no": "新北教幼字第1121849201號", "law": "幼兒教育及照顧法第38條", "violation": "消防安全設備檢查申報逾期", "fine": "限期改善", "fine_ntd": 0, "academic_year": 112},
        ],
        "accounts": [
            {"account_code": "5101", "account_name": "人事支出", "category": "人事費", "budget": 4100000, "actual": 3950000, "variance": -150000, "variance_pct": -3.66, "source_page": 8, "verified": True},
        ],
    },
    "N15": {
        "id": "N15",
        "name": "新北市新月非營利幼兒園",
        "peer_group": "非營利園",
        "operator": "財團法人弘道教育基金會",
        "district": "板橋區",
        "address": "新北市板橋區新月街1號",
        "latitude": 25.0215,
        "longitude": 121.4589,
        "penalty_count": 1,
        "latest_score": 38.0,
        "risk_level": "medium",
        "features": {
            "penalty": 40.0,
            "residual": 38.0,
            "isolation_forest": 35.0,
            "opinion": 30.0,
            "flags": 45.0,
        },
        "history": [
            {"academic_year": 110, "score": 28.0, "p_penalty": 0.10, "residual_z": 0.30, "iso_score": 0.20, "opinion_risk": 0.10},
            {"academic_year": 111, "score": 32.0, "p_penalty": 0.15, "residual_z": 0.55, "iso_score": 0.28, "opinion_risk": 0.15},
            {"academic_year": 112, "score": 38.0, "p_penalty": 0.25, "residual_z": 0.75, "iso_score": 0.35, "opinion_risk": 0.22},
        ],
        "shap_breakdown": [
            {"feature": "asset_maintenance", "label_zh": "固定資產維護支出偏低", "contribution": 0.18, "value": "支出率 48%"},
        ],
        "flags": [
            {"code": "OPINION_設施安全", "title": "固定資產維護支出偏低", "description": "設施修繕與維護支出偏低，遊樂設施需定期注意保養紀錄", "weight": 0.18, "source_ref": "112年度決算書 p.13"},
        ],
        "penalties": [
            {"date": "2023/10/05", "doc_no": "新北教幼字第1121938290號", "law": "幼兒教育及照顧法第17條", "violation": "室內活動空間未依核定用途使用", "fine": "處負責人新臺幣6,000元罰鍰", "fine_ntd": 6000, "academic_year": 112},
        ],
        "accounts": [
            {"account_code": "5101", "account_name": "人事支出", "category": "人事費", "budget": 4800000, "actual": 4720000, "variance": -80000, "variance_pct": -1.67, "source_page": 9, "verified": True},
        ],
    },
    "N17": {
        "id": "N17",
        "name": "新北市中正非營利幼兒園",
        "peer_group": "非營利園",
        "operator": "社團法人新北市幼教學會",
        "district": "永和區",
        "address": "新北市永和區中正路150號",
        "latitude": 25.0028,
        "longitude": 121.5123,
        "penalty_count": 1,
        "latest_score": 55.0,
        "risk_level": "medium",
        "features": {
            "penalty": 55.0,
            "residual": 62.0,
            "isolation_forest": 52.0,
            "opinion": 48.0,
            "flags": 50.0,
        },
        "history": [
            {"academic_year": 110, "score": 38.0, "p_penalty": 0.18, "residual_z": 0.50, "iso_score": 0.30, "opinion_risk": 0.15},
            {"academic_year": 111, "score": 45.0, "p_penalty": 0.26, "residual_z": 0.90, "iso_score": 0.40, "opinion_risk": 0.28},
            {"academic_year": 112, "score": 55.0, "p_penalty": 0.38, "residual_z": 1.45, "iso_score": 0.52, "opinion_risk": 0.35},
        ],
        "shap_breakdown": [
            {"feature": "budget_execution", "label_zh": "決算執行率異常", "contribution": 0.22, "value": "保留款比例偏高"},
        ],
        "flags": [
            {"code": "BUDGET_RESIDUAL", "title": "決算執行率異常", "description": "部分補助款結餘未依規定期限繳回或辦理保留手續", "weight": 0.22, "source_ref": "112年度決算書 p.7"},
        ],
        "penalties": [
            {"date": "2023/08/12", "doc_no": "新北教幼字第1121589301號", "law": "幼兒教育及照顧法第33條", "violation": "教保服務契約未給予法定審閱期", "fine": "限期改善", "fine_ntd": 0, "academic_year": 112},
        ],
        "accounts": [
            {"account_code": "5101", "account_name": "人事支出", "category": "人事費", "budget": 4500000, "actual": 4350000, "variance": -150000, "variance_pct": -3.33, "source_page": 8, "verified": True},
        ],
    },
    "N18": {
        "id": "N18",
        "name": "新北市福營非營利幼兒園",
        "peer_group": "非營利園",
        "operator": "財團法人天主教善牧基金會",
        "district": "新莊區",
        "address": "新北市新莊區福營路210號",
        "latitude": 25.0245,
        "longitude": 121.4231,
        "penalty_count": 1,
        "latest_score": 48.0,
        "risk_level": "medium",
        "features": {
            "penalty": 45.0,
            "residual": 55.0,
            "isolation_forest": 48.0,
            "opinion": 40.0,
            "flags": 45.0,
        },
        "history": [
            {"academic_year": 110, "score": 32.0, "p_penalty": 0.12, "residual_z": 0.45, "iso_score": 0.25, "opinion_risk": 0.12},
            {"academic_year": 111, "score": 40.0, "p_penalty": 0.22, "residual_z": 0.78, "iso_score": 0.35, "opinion_risk": 0.22},
            {"academic_year": 112, "score": 48.0, "p_penalty": 0.32, "residual_z": 1.10, "iso_score": 0.48, "opinion_risk": 0.30},
        ],
        "shap_breakdown": [
            {"feature": "utility_expense", "label_zh": "一般水電支出偏高", "contribution": 0.18, "value": "超支 28%"},
        ],
        "flags": [
            {"code": "BUDGET_RESIDUAL", "title": "一般水電支出偏高", "description": "水電事務費執行率異常超越預算編列", "weight": 0.18, "source_ref": "112年度決算書 p.16"},
        ],
        "penalties": [
            {"date": "2024/02/22", "doc_no": "新北教幼字第1130328192號", "law": "幼兒教育及照顧法第28條", "violation": "幼童專用車行車紀錄器故障未及時修復", "fine": "處負責人新臺幣3,000元罰鍰並限期改善", "fine_ntd": 3000, "academic_year": 112},
        ],
        "accounts": [
            {"account_code": "5101", "account_name": "人事支出", "category": "人事費", "budget": 3900000, "actual": 3820000, "variance": -80000, "variance_pct": -2.05, "source_page": 7, "verified": True},
        ],
    },
    "N25": {
        "id": "N25",
        "name": "新北市碧城非營利幼兒園",
        "peer_group": "非營利園",
        "operator": "社團法人台北市中華兒童福祉協會",
        "district": "新店區",
        "address": "新北市新店區碧城路18號",
        "latitude": 24.9621,
        "longitude": 121.5412,
        "penalty_count": 2,
        "latest_score": 71.0,
        "risk_level": "high",
        "features": {
            "penalty": 80.0,
            "residual": 68.0,
            "isolation_forest": 65.0,
            "opinion": 70.0,
            "flags": 70.0,
        },
        "history": [
            {"academic_year": 110, "score": 45.0, "p_penalty": 0.25, "residual_z": 0.85, "iso_score": 0.38, "opinion_risk": 0.20},
            {"academic_year": 111, "score": 58.0, "p_penalty": 0.42, "residual_z": 1.35, "iso_score": 0.52, "opinion_risk": 0.40},
            {"academic_year": 112, "score": 71.0, "p_penalty": 0.58, "residual_z": 1.95, "iso_score": 0.65, "opinion_risk": 0.62},
        ],
        "shap_breakdown": [
            {"feature": "understaffing_ratio", "label_zh": "未依規定配置教保員", "contribution": 0.26, "value": "缺額待補"},
            {"feature": "prior_penalties", "label_zh": "重複受裁處紀錄", "contribution": 0.22, "value": "2件"},
        ],
        "flags": [
            {"code": "UNDERSTAFFING", "title": "未依規定配置教保員", "description": "班級生師比連續兩期未達法定標準", "weight": 0.30, "source_ref": "稽查處分紀錄"},
        ],
        "penalties": [
            {"date": "2024/04/10", "doc_no": "新北教幼字第1130761234號", "law": "幼兒教育及照顧法第16條", "violation": "師生比不符法令規範，有未具教保員資格者任職帶班", "fine": "處負責人新臺幣45,000元罰鍰", "fine_ntd": 45000, "academic_year": 112},
            {"date": "2023/10/18", "doc_no": "新北教幼字第1121998412號", "law": "幼兒教育及照顧法第38條", "violation": "安全設備逃生通道堆放雜物", "fine": "限期改善", "fine_ntd": 0, "academic_year": 112},
        ],
        "accounts": [
            {"account_code": "5101", "account_name": "人事支出", "category": "人事費", "budget": 4500000, "actual": 3400000, "variance": -1100000, "variance_pct": -24.44, "source_page": 8, "verified": True},
        ],
    },
    "N29": {
        "id": "N29",
        "name": "新北市東湖非營利幼兒園",
        "peer_group": "非營利園",
        "operator": "社團法人台灣身心障礙兒童關懷協會",
        "district": "林口區",
        "address": "新北市林口區東湖路55號",
        "latitude": 25.0812,
        "longitude": 121.3789,
        "penalty_count": 0,
        "latest_score": 22.4,
        "risk_level": "low",
        "features": {
            "penalty": 15.0,
            "residual": 25.0,
            "isolation_forest": 22.0,
            "opinion": 18.0,
            "flags": 20.0,
        },
        "history": [
            {"academic_year": 110, "score": 20.0, "p_penalty": 0.08, "residual_z": 0.20, "iso_score": 0.15, "opinion_risk": 0.05},
            {"academic_year": 111, "score": 21.5, "p_penalty": 0.09, "residual_z": 0.25, "iso_score": 0.18, "opinion_risk": 0.08},
            {"academic_year": 112, "score": 22.4, "p_penalty": 0.10, "residual_z": 0.30, "iso_score": 0.22, "opinion_risk": 0.10},
        ],
        "shap_breakdown": [
            {"feature": "sound_financials", "label_zh": "財務運作與預算執行良好", "contribution": -0.15, "value": "執行率 96%"},
        ],
        "flags": [],
        "penalties": [],
        "accounts": [
            {"account_code": "5101", "account_name": "人事支出", "category": "人事費", "budget": 4200000, "actual": 4120000, "variance": -80000, "variance_pct": -1.9, "source_page": 8, "verified": True},
        ],
    },
    "N30": {
        "id": "N30",
        "name": "新北市文中非營利幼兒園",
        "peer_group": "非營利園",
        "operator": "財團法人新北市文教促進基金會",
        "district": "三重區",
        "address": "新北市三重區文中一街2號",
        "latitude": 25.0612,
        "longitude": 121.4891,
        "penalty_count": 2,
        "latest_score": 68.3,
        "risk_level": "high",
        "features": {
            "penalty": 75.0,
            "residual": 65.0,
            "isolation_forest": 62.0,
            "opinion": 68.0,
            "flags": 65.0,
        },
        "history": [
            {"academic_year": 110, "score": 40.0, "p_penalty": 0.20, "residual_z": 0.65, "iso_score": 0.30, "opinion_risk": 0.18},
            {"academic_year": 111, "score": 52.0, "p_penalty": 0.35, "residual_z": 1.20, "iso_score": 0.45, "opinion_risk": 0.35},
            {"academic_year": 112, "score": 68.3, "p_penalty": 0.55, "residual_z": 1.80, "iso_score": 0.62, "opinion_risk": 0.58},
        ],
        "shap_breakdown": [
            {"feature": "student_overflow", "label_zh": "超收學童與師生比爭議", "contribution": 0.25, "value": "核定名額超額"},
        ],
        "flags": [
            {"code": "UNDERSTAFFING", "title": "超收學童與師生比爭議", "description": "多次遭家長投訴班級人數超過法定師生比上限", "weight": 0.28, "source_ref": "陳情紀錄與處分書"},
        ],
        "penalties": [
            {"date": "2024/03/15", "doc_no": "新北教幼字第1130519283號", "law": "幼兒教育及照顧法第42條", "violation": "超收學童達5人以上", "fine": "處負責人新臺幣40,000元罰鍰", "fine_ntd": 40000, "academic_year": 112},
            {"date": "2023/12/01", "doc_no": "新北教幼字第1122391004號", "law": "幼兒教育及照顧法第17條", "violation": "未依規定通報幼生異動名冊", "fine": "限期改善", "fine_ntd": 0, "academic_year": 112},
        ],
        "accounts": [
            {"account_code": "5101", "account_name": "人事支出", "category": "人事費", "budget": 5000000, "actual": 4200000, "variance": -800000, "variance_pct": -16.0, "source_page": 9, "verified": True},
        ],
    },
    "M01": {
        "id": "M01",
        "name": "新北市立板橋幼兒園",
        "peer_group": "市立幼兒園",
        "operator": "新北市政府教育局 (公立公營)",
        "district": "板橋區",
        "address": "新北市板橋區文化路一段100號",
        "latitude": 25.0112,
        "longitude": 121.4623,
        "penalty_count": 0,
        "latest_score": 18.5,
        "risk_level": "low",
        "features": {
            "penalty": 10.0,
            "residual": 20.0,
            "isolation_forest": 15.0,
            "opinion": 15.0,
            "flags": 10.0,
        },
        "history": [
            {"academic_year": 110, "score": 19.0, "p_penalty": 0.05, "residual_z": 0.15, "iso_score": 0.12, "opinion_risk": 0.05},
            {"academic_year": 111, "score": 18.2, "p_penalty": 0.05, "residual_z": 0.18, "iso_score": 0.14, "opinion_risk": 0.06},
            {"academic_year": 112, "score": 18.5, "p_penalty": 0.06, "residual_z": 0.20, "iso_score": 0.15, "opinion_risk": 0.06},
        ],
        "shap_breakdown": [
            {"feature": "stable_budget", "label_zh": "公校基金預算執行穩健", "contribution": -0.20, "value": "符合規範"},
        ],
        "flags": [],
        "penalties": [],
        "accounts": [
            {"account_code": "5101", "account_name": "公立教職員人事費", "category": "人事費", "budget": 12500000, "actual": 12450000, "variance": -50000, "variance_pct": -0.4, "source_page": 1, "verified": True},
        ],
    },
    "M02": {
        "id": "M02",
        "name": "新北市立三重幼兒園",
        "peer_group": "市立幼兒園",
        "operator": "新北市政府教育局 (公立公營)",
        "district": "三重區",
        "address": "新北市三重區重陽路一段50號",
        "latitude": 25.0652,
        "longitude": 121.4921,
        "penalty_count": 0,
        "latest_score": 24.0,
        "risk_level": "low",
        "features": {
            "penalty": 12.0,
            "residual": 26.0,
            "isolation_forest": 20.0,
            "opinion": 18.0,
            "flags": 15.0,
        },
        "history": [
            {"academic_year": 110, "score": 22.0, "p_penalty": 0.06, "residual_z": 0.20, "iso_score": 0.15, "opinion_risk": 0.08},
            {"academic_year": 111, "score": 23.0, "p_penalty": 0.07, "residual_z": 0.22, "iso_score": 0.18, "opinion_risk": 0.10},
            {"academic_year": 112, "score": 24.0, "p_penalty": 0.08, "residual_z": 0.28, "iso_score": 0.20, "opinion_risk": 0.12},
        ],
        "shap_breakdown": [
            {"feature": "stable_budget", "label_zh": "公校預算運作平穩", "contribution": -0.15, "value": "無缺失"},
        ],
        "flags": [],
        "penalties": [],
        "accounts": [
            {"account_code": "5101", "account_name": "公立教職員人事費", "category": "人事費", "budget": 9800000, "actual": 9720000, "variance": -80000, "variance_pct": -0.82, "source_page": 1, "verified": True},
        ],
    },
    "M03": {
        "id": "M03",
        "name": "新北市立新莊幼兒園",
        "peer_group": "市立幼兒園",
        "operator": "新北市政府教育局 (公立公營)",
        "district": "新莊區",
        "address": "新北市新莊區中正路80號",
        "latitude": 25.0361,
        "longitude": 121.4512,
        "penalty_count": 0,
        "latest_score": 29.5,
        "risk_level": "low",
        "features": {
            "penalty": 15.0,
            "residual": 32.0,
            "isolation_forest": 25.0,
            "opinion": 22.0,
            "flags": 18.0,
        },
        "history": [
            {"academic_year": 110, "score": 25.0, "p_penalty": 0.08, "residual_z": 0.25, "iso_score": 0.18, "opinion_risk": 0.10},
            {"academic_year": 111, "score": 27.5, "p_penalty": 0.09, "residual_z": 0.30, "iso_score": 0.22, "opinion_risk": 0.14},
            {"academic_year": 112, "score": 29.5, "p_penalty": 0.11, "residual_z": 0.35, "iso_score": 0.25, "opinion_risk": 0.15},
        ],
        "shap_breakdown": [
            {"feature": "minor_variance", "label_zh": "修繕預算執行微幅延遲", "contribution": 0.08, "value": "保留款"},
        ],
        "flags": [],
        "penalties": [],
        "accounts": [
            {"account_code": "5101", "account_name": "公立教職員人事費", "category": "人事費", "budget": 11000000, "actual": 10880000, "variance": -120000, "variance_pct": -1.09, "source_page": 1, "verified": True},
        ],
    },
    "M04": {
        "id": "M04",
        "name": "新北市立中和幼兒園",
        "peer_group": "市立幼兒園",
        "operator": "新北市政府教育局 (公立公營)",
        "district": "中和區",
        "address": "新北市中和區南山路200號",
        "latitude": 24.9985,
        "longitude": 121.5014,
        "penalty_count": 0,
        "latest_score": 19.8,
        "risk_level": "low",
        "features": {
            "penalty": 10.0,
            "residual": 22.0,
            "isolation_forest": 16.0,
            "opinion": 15.0,
            "flags": 12.0,
        },
        "history": [
            {"academic_year": 110, "score": 20.0, "p_penalty": 0.06, "residual_z": 0.18, "iso_score": 0.14, "opinion_risk": 0.07},
            {"academic_year": 111, "score": 19.5, "p_penalty": 0.06, "residual_z": 0.19, "iso_score": 0.15, "opinion_risk": 0.07},
            {"academic_year": 112, "score": 19.8, "p_penalty": 0.07, "residual_z": 0.22, "iso_score": 0.16, "opinion_risk": 0.08},
        ],
        "shap_breakdown": [
            {"feature": "stable_budget", "label_zh": "正常運作無缺失", "contribution": -0.18, "value": "良好"},
        ],
        "flags": [],
        "penalties": [],
        "accounts": [
            {"account_code": "5101", "account_name": "公立教職員人事費", "category": "人事費", "budget": 8900000, "actual": 8850000, "variance": -50000, "variance_pct": -0.56, "source_page": 1, "verified": True},
        ],
    },
}


def get_all_institutions(peer_group: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return filtered institution items for list/map view."""
    items = []
    for inst in INSTITUTIONS_DB.values():
        if peer_group and peer_group != "all" and inst["peer_group"] != peer_group:
            continue
        items.append({
            "id": inst["id"],
            "name": inst["name"],
            "peer_group": inst["peer_group"],
            "latest_score": inst["latest_score"],
            "penalty_count": inst["penalty_count"],
            "risk_level": inst["risk_level"],
            "latitude": inst["latitude"],
            "longitude": inst["longitude"],
            "address": inst["address"],
        })
    return items


def get_institution_detail(inst_id: str) -> Optional[Dict[str, Any]]:
    """Return deep inspection detail for institution."""
    inst = INSTITUTIONS_DB.get(inst_id)
    if not inst:
        return None
    return {
        "id": inst["id"],
        "name": inst["name"],
        "peer_group": inst["peer_group"],
        "operator": inst["operator"],
        "latest_score": inst["latest_score"],
        "history": inst["history"],
        "shap_breakdown": inst["shap_breakdown"],
        "flags": inst["flags"],
        "penalties": inst["penalties"],
        "opinion_doc_count": 3 if inst["latest_score"] >= 60 else (1 if inst["latest_score"] >= 30 else 0),
        "source_urls": [
            f"https://ap.ece.moe.edu.tw/post/penalty/{inst['id']}",
            "https://www.dcard.tw/f/parentchild",
        ] if inst["penalty_count"] > 0 else [],
    }


def get_rankings(
    year: int = 112,
    peer_group: Optional[str] = None,
    min_score: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Return sorted institutions ranking for the given academic year."""
    ranked = []
    for inst in INSTITUTIONS_DB.values():
        if peer_group and peer_group != "all" and inst["peer_group"] != peer_group:
            continue

        # Get year score
        history_map = {h["academic_year"]: h for h in inst["history"]}
        h_info = history_map.get(year, inst["history"][-1])
        score = h_info["score"]

        if min_score is not None and score < min_score:
            continue

        ranked.append({
            "id": inst["id"],
            "name": inst["name"],
            "peer_group": inst["peer_group"],
            "academic_year": year,
            "score": score,
            "p_penalty": h_info["p_penalty"],
            "flag_count": len(inst["flags"]),
            "has_opinion": inst["features"]["opinion"] > 20.0,
        })

    # Sort descending by risk score
    ranked.sort(key=lambda x: x["score"], reverse=True)

    # Assign 1-indexed rank
    for idx, item in enumerate(ranked, start=1):
        item["rank"] = idx

    return ranked


def get_accounts(inst_id: str, year: int) -> List[Dict[str, Any]]:
    """Return budget vs actual financial accounts."""
    inst = INSTITUTIONS_DB.get(inst_id)
    if not inst:
        return []
    return inst.get("accounts", [])


def compute_whatif(weights: Dict[str, float], year: int = 112, peer_group: Optional[str] = None) -> List[Dict[str, Any]]:
    """Re-compute scores and rank changes based on user custom weights."""
    w_penalty = weights.get("penalty", 0.45)
    w_residual = weights.get("residual", 0.20)
    w_iso = weights.get("isolation_forest", 0.15)
    w_opinion = weights.get("opinion", 0.10)
    w_flags = weights.get("flags", 0.10)
    total_w = w_penalty + w_residual + w_iso + w_opinion + w_flags or 1.0

    # Normalization
    nw_penalty = w_penalty / total_w
    nw_residual = w_residual / total_w
    nw_iso = w_iso / total_w
    nw_opinion = w_opinion / total_w
    nw_flags = w_flags / total_w

    original_ranks = get_rankings(year=year, peer_group=peer_group)
    orig_rank_map = {item["id"]: (idx + 1, item["score"]) for idx, item in enumerate(original_ranks)}

    rescored_list = []
    for inst_id, (orig_rank, orig_score) in orig_rank_map.items():
        inst = INSTITUTIONS_DB[inst_id]
        f = inst["features"]
        new_score = (
            f["penalty"] * nw_penalty
            + f["residual"] * nw_residual
            + f["isolation_forest"] * nw_iso
            + f["opinion"] * nw_opinion
            + f["flags"] * nw_flags
        )
        new_score = round(max(0.0, min(100.0, new_score)), 1)
        rescored_list.append({
            "id": inst["id"],
            "name": inst["name"],
            "original_score": orig_score,
            "new_score": new_score,
            "orig_rank": orig_rank,
        })

    # Sort by new_score descending
    rescored_list.sort(key=lambda x: x["new_score"], reverse=True)

    results = []
    for new_rank_idx, item in enumerate(rescored_list, start=1):
        # rank_change: positive means rank improved in danger (e.g. 5 -> 2 means +3 positions upward)
        rank_change = item["orig_rank"] - new_rank_idx
        results.append({
            "id": item["id"],
            "name": item["name"],
            "original_score": item["original_score"],
            "new_score": item["new_score"],
            "rank_change": rank_change,
        })

    return results
