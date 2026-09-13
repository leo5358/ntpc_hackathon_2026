# 風險預警模型：使用指令

最終模型只用裁罰紀錄與園所名冊，不需要 OCR、也不需要財報。模型說明與驗證結果見 `docs/MODEL_REPORT.md`，各資料檔說明見 `data/README.md`。

產出的模型檔與分數檔由第三方資料衍生，只在團隊內部或私有 S3 流通，不要 commit（`.gitignore` 已排除，理由見 repo 根目錄的 `NOTICE.md`）。

## 1. 環境（第一次）

```bash
python3 -m venv ~/.venvs/ntpc
~/.venvs/ntpc/bin/pip install boto3 numpy pandas scikit-learn xgboost-cpu   # 只用最終模型，這樣就夠
source ~/.venvs/ntpc/bin/activate
cd ~/2609Hackathon/ntpc_hackthon_2026/ml
# 預設由私有 S3 下載 s3://demo-20260912/E_教育局-資料集.zip
# 若改用本機 ZIP，才設定：export DATASET_ZIP=/path/to/dataset.zip
```

Windows PowerShell 可在 repo 根目錄執行：

```powershell
$env:DATASET_S3_URI = "s3://demo-20260912/E_教育局-資料集.zip"
# 已設定具名 AWS profile 時使用；若用環境憑證或 IAM role，省略這行。
$env:AWS_PROFILE = "workshop"
cd ml
python -m pipeline.dataset  # 下載並檢查 ZIP，可先獨立驗證 S3 存取
```

憑證需要對該物件的 `s3:GetObject` 權限；若物件以自訂 KMS key 加密，另需相應解密權限。憑證由 boto3 的標準 AWS 憑證鏈讀取，不放入前端或 repo。區域可用 `AWS_DEFAULT_REGION` 設定。

資料來源優先順序：明確設定的 `DATASET_ZIP` → 明確設定的 `DATASET_S3_URI` → 自動找到的本機 ZIP → 預設 S3。第一次下載後會重用 `~/.cache/ntpc_hackathon/datasets/` 中的 ZIP，不會每次重新下載。同一 S3 key 更新後，請換用新的 `CACHE_DIR` 並重新啟動 pipeline，避免沿用舊 ZIP 與 OCR／解壓快取。

最終模型雖不用財務特徵，現有 `s3_penalties` 仍從 ZIP 的財報檔名建立非營利園名冊，因此仍需這份資料集。

## 2. 產生模型與分數（幾分鐘，需要網路）

```bash
python -m pipeline.s3_penalties        # 下載最新裁罰紀錄
python -m pipeline.s4b_features_all    # 建全新北訓練表
python -m pipeline.s6_validate         # 訓練、驗證，輸出模型與最新一年分數
```

產出：

| 檔案 | 用途 |
| --- | --- |
| `data/processed/risk_scores_latest.csv` | 每間園的風險機率、百分位、`screen_flag`（篩檢）、`priority_flag`（優先稽查）、`top_factors` |
| `models/risk_model_all.json` | 參數與公式，任何語言都能重現 |
| `models/risk_model_all.joblib` | Python 直接載入（需相同版本的 scikit-learn） |
| `models/validation_all.json` | AUC、混淆矩陣等所有驗證數字 |

## 3. 查看結果

```bash
# 優先稽查名單（前 10%）
python -c "import pandas as pd; d=pd.read_csv('data/processed/risk_scores_latest.csv'); print(d[d.priority_flag][['inst','risk_probability','percentile','top_factors']].to_string(index=False))"

# 查詢某間園
python -c "import pandas as pd; d=pd.read_csv('data/processed/risk_scores_latest.csv'); print(d[d.inst.str.contains('園名關鍵字')].to_string(index=False))"

# 驗證數字（跨機構 AUC、時間外推 AUC）
python -c "import json; r=json.load(open('models/validation_all.json')); print(r['cross_validation']['auc'], r['forward']['auc'])"
```

## 4. 給網站 / API 使用

```bash
# 建議：上傳分數檔到私有 S3，API 直接讀取
aws s3 cp data/processed/risk_scores_latest.csv s3://<bucket>/scores/risk_scores_latest.csv --profile workshop --region us-west-2

# 非 Python 環境：交付公式檔，依其中的 formula 欄位計算
cp models/risk_model_all.json <前端或後端專案路徑>/
```

Python 即時計算：

```python
import joblib, numpy as np
m = joblib.load("models/risk_model_all.joblib")
rank = m["ranker"].predict_proba(df[m["features"]])[:, 1]
a, b = m["platt"]
prob = 1 / (1 + np.exp(-(a * np.log(rank / (1 - rank)) + b)))
screen_flag = rank >= m["screen_threshold"]
```

JavaScript 即時計算：

```js
const m = await (await fetch("risk_model_all.json")).json();
const sig = v => 1 / (1 + Math.exp(-v));
function score(row) {                       // row = { prior_penalties: 2, private: 1, ... }
  const z = m.features.map((f, i) =>
    ((row[f] ?? m.impute_median[i]) - m.mean[i]) / m.scale[i]);
  const rank = sig(m.intercept + z.reduce((s, v, i) => s + v * m.coef[i], 0));
  const prob = sig(m.platt.a * Math.log(rank / (1 - rank)) + m.platt.b);
  return { prob, screen: rank >= m.screen_threshold };
}
```

## 5. 定期更新（建議每季）

```bash
crontab -e
# 每季第一天凌晨 3 點重新產生分數
0 3 1 */3 * cd ~/2609Hackathon/ntpc_hackthon_2026/ml && ~/.venvs/ntpc/bin/python -m pipeline.s3_penalties && ~/.venvs/ntpc/bin/python -m pipeline.s4b_features_all && ~/.venvs/ntpc/bin/python -m pipeline.s6_validate
```

## 6. 選用

```bash
python -m pipeline.s5_train --table _all               # 重新比較模型大小（邏輯迴歸 vs XGBoost）
python -m pipeline.s5_train --table _all --sagemaker   # 送 SageMaker；只支援 XGBoost，尚未實測
```

## 7. 重做完整研究（一般使用不需要）

```bash
~/.venvs/ntpc/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
~/.venvs/ntpc/bin/pip install -r requirements.txt
python -m pipeline.s1_city            # 市立決算書（約 5 分鐘）
python -m pipeline.s2_nonprofit       # 非營利財報 OCR（約 1 小時，有快取）
python -m pipeline.nlp.collect        # 輿情語料
python -m pipeline.nlp.train          # 輿情模型（約 1 分鐘）
python -m pipeline.nlp.aggregate
python -m pipeline.s4_features
python -m pipeline.s5_train           # 60 間公共化園的財報模型（結論：無預測力）
```

## 使用上的定位

- 用 `priority_flag` 決定稽查先後：前 10% 的命中率約為隨機的 2 倍。
- 用 `screen_flag` 確保不漏報：名單約涵蓋七成的園，後續需要第二層篩選。
- 顯示「風險機率」或「百分位」，不要寫成「準確率」。
- 公共化園之間的排序不可靠（被罰件數太少）。
