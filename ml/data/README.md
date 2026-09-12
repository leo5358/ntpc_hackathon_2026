# 資料說明

這個專案位於 repo 的 `ml/` 目錄，以下所有指令都在 `ml/` 底下執行。只想使用最終模型的話，看 `ml/USAGE.md` 就夠了。

`data/processed/` 的檔案都由 `pipeline/` 產生。原始 PDF 和 OCR 快取放在 `~/.cache/ntpc_hackathon/`，不進 repo。

`data/processed/`、`data/labels/`、`models/` 都列在 `.gitignore`：內容來自第三方資料（比賽資料集、政府網站、新聞標題）或 GPL 授權的模型，只在本機重建，不隨 repo 散佈。每位隊友照下面的順序自己跑一次即可。來源與授權見 `NOTICE.md`。

## 執行順序

```bash
pip install -r requirements.txt       # torch 請用 CPU 版，見 requirements.txt 註解

python -m pipeline.s1_city            # 市立決算書第五冊 → city_fin.csv（約 5 分鐘，含掃描頁 OCR）
python -m pipeline.s2_nonprofit       # 非營利財報 OCR → nonprofit_fin.csv、nonprofit_pages.csv（最耗 CPU，有快取可續跑）
python -m pipeline.s3_penalties       # 裁罰紀錄 → penalties.csv（需網路）
python -m pipeline.nlp.collect        # 輿情語料 → opinion_docs.jsonl（需網路）
python -m pipeline.nlp.train          # 輿情模型 → models/opinion_topic/、opinion_predictions.jsonl
python -m pipeline.nlp.aggregate      # 輿情彙總 → opinion_features.csv
python -m pipeline.s4_features        # 主模型訓練表 → model_table.csv、train.csv、features.json
python -m pipeline.s5_train           # 60 間園財報模型 → scores_main.csv（驗證結果：無預測力，僅作解釋層）
python -m pipeline.s4b_features_all   # 全新北訓練表（不需財報）→ model_table_all.csv、train_all.csv
python -m pipeline.s5_train --table _all   # 全新北：比較模型大小（加 --sagemaker 送 SageMaker）
python -m pipeline.s6_validate        # 最終模型：驗證、校正、輸出 risk_scores_latest.csv（demo 用這份）；報告見 docs/MODEL_REPORT.md
```

## 檔案

| 檔案 | 一列代表 | 主要欄位 |
| --- | --- | --- |
| `city_fin.csv` | 市立園某會計年度、某報表、某科目 | `fiscal_year` `inst_id`(136xx) `table`(來源/用途) `account` `budget` `actual` `page` `source`(text/ocr) `verified` |
| `nonprofit_fin.csv` | 非營利財報某頁收支餘絀表的一列 | `inst_id`(N##) `report_year` `academic_year` `label`(OCR 原文) `account` `budget` `actual` `diff` `row_ok` |
| `nonprofit_pages.csv` | 一頁收支餘絀表 | `rev_total_ok` `exp_total_ok`：各列加總是否等於收入 / 支出合計 |
| `penalties.csv` | 一件裁罰（已去重，不含人名） | `group` `inst_id` `date` `academic_year` `calendar_year` `article` `violation` `fine_ntd` |
| `penalties_all.csv` | 全新北一件裁罰 | `title`（園所全名）+ 同上 |
| `model_table_all.csv` | 全新北主模型的一列：某園第 t 年 | 過去裁罰、規模、月費、立案年數、公私立、延長照顧、準公共化；標籤為 t+1 年是否被罰 |
| `opinion_docs.jsonl` | 一則新聞標題 | `kind`(institution/domain) `inst_id` `title` `published` `weak_topics` `weak_polarity` |
| `opinion_features.csv` | 某園某期的輿情摘要 | `opinion_docs` `opinion_neg_share` `opinion_risk_docs` |
| `model_table.csv` | 主模型的一列：某園第 t 期 | `group` `inst_id` `period` `label_available` `penalized_next` + 特徵 |
| `train.csv` | 同上，只含有標籤的列 | SageMaker 格式：無表頭、第一欄為標籤、空白代表缺值 |
| `features.json` | 特徵名稱與順序 | 推論和 SHAP 解釋都以此為準 |

驗證欄位：`verified` / `row_ok` 表示「決算 − 預算 = 印出的差異」；`rev_total_ok` / `exp_total_ok` 表示各列加總等於合計。`s4_features` 會優先採用通過驗證的頁面。

## 兩個模型的輸入

**輿情模型**：一則標題文字 → 6 個主題的多標籤機率（不當管教、餐食衛生、收費爭議、人力不足、設施安全、行政立案），全部低於門檻視為無關。結果經 `nlp.aggregate` 彙總成 `opinion_features.csv`，成為主模型的特徵。

**主模型**：`model_table.csv` 的一列 → 下一期被裁罰的機率。

| 特徵群 | 欄位 |
| --- | --- |
| 預算執行 | `exec_personnel` `exec_services` `exec_materials` `exec_maintenance` `exec_utilities` `exec_other` `exec_expense` |
| 支出結構 | `share_*` `hhi` `abs_var_share` `n_over_20pct` |
| 財務體質 | `surplus_ratio` `tuition_share` `log_expense` `expense_per_child` |
| 數字鑑識 | `round_share`（整千比例）`benford_mad`（首位數偏離） `n_line_items` |
| 基本資料 | `capacity` `monthly_fee` `years_since_reg` `has_after_care` `is_nonprofit` |
| 歷史 | `prior_penalties`（第 t 期以前的裁罰數） |
| 年變化 | `d_exec_personnel` `d_share_personnel` `d_exec_expense` `expense_growth` |
| 同儕比較 | `z_*`：同群組、同期內的標準分數 |
| 輿情 | `opinion_docs` `opinion_neg_share` `opinion_risk_docs` |

## 期間與標籤

- 市立園的 `period` 是會計年度（民國，曆年）；非營利園是學年度（8 月起）。兩者不直接比較，只在同群組內比較。
- `penalized_next`：第 t+1 期是否被裁罰。`label_available` 為 false 表示 t+1 期還沒結束，這些列只用來產生目前的風險分數。
- 109–111 學年度沒有任何裁罰紀錄（可能是鏡像的收錄範圍，或 111 年修法加重不當對待罰則），早期年份的「沒被罰」只能當弱負樣本。
- `capacity`、`monthly_fee`、`years_since_reg` 來自目前的名冊快照，不是逐年資料。
- 營運單位更換目前沒有納入：名冊看不出換的時間，直接用會把「被罰之後才換」的資訊洩漏給模型。

## 人工標註

`data/labels/opinion_gold_todo.csv`：`topic` 填主題（多個用 `|` 分隔，或填 `無關`），`polarity` 填 -1 / 0 / 1。填好的列會自動被 `nlp.train` 拿來評估模型與關鍵字規則的準確度。

這個檔案含有新聞標題，不進 repo。隊友之間要交換標註結果時，只傳 `id`、`topic`、`polarity`、`annotator` 四欄；標題可以用 `nlp.collect` 重新產生，並用 `id` 對回。
