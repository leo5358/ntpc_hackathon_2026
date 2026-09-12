# 第三方來源與授權

本 repo 只散佈我們自己寫的程式碼與文件。下列來源都由 `ml/pipeline/` 在執行時讀取或下載，產出放在 `ml/data/processed/`、`ml/data/labels/`、`ml/models/`，這三個資料夾已列入 `ml/.gitignore`，不隨 repo 散佈。

新增任何資料來源、模型或套件前，先確認授權並補進本檔。

## 資料

| 來源 | 用途 | 權利狀態 | 本 repo 的處理 |
| --- | --- | --- | --- |
| 比賽提供的 `dataset.zip`（新北市決算書、非營利園財務報告） | 財務特徵 | 主辦單位未說明散佈條件 | 不放原檔，也不放由它整理出的 CSV；要公開衍生資料前須先向主辦單位確認 |
| [全國教保資訊網](https://www.ece.moe.edu.tw/)（教育部國民及學前教育署） | 裁罰紀錄、園所名冊 | 網站標示「© 2019 版權所有 – 教育部國民及學前教育署」，未找到開放授權宣告 | 不放任何抓取結果；demo 畫面引用時註明來源與擷取日期，只呈現機構層級，不含人名 |
| [kiang/ap.ece.moe.edu.tw](https://github.com/kiang/ap.ece.moe.edu.tw)（上列網站的每日鏡像，保留官方已下架的裁罰紀錄） | 取得裁罰紀錄與名冊 | MIT License，© 2024 Finjon Kiang | 執行時下載，不複製其檔案；若日後需要收錄其檔案，須一併附上 MIT 授權聲明 |
| Google 新聞 RSS | 輿情新聞標題 | 非正式產品、沒有使用合約；標題著作權屬各家媒體 | 只在本機分析、不散佈；每次查詢間隔 1 秒 |

## 模型

| 模型 | 授權 | 本 repo 的處理 |
| --- | --- | --- |
| [ckiplab/albert-tiny-chinese](https://github.com/ckiplab/ckip-transformers) | GPL-3.0 | 執行時自 Hugging Face 下載並在本機微調。微調後的權重（`ml/models/opinion_topic/`）不得 commit 或以其他方式散佈。在我們自己架設的服務裡使用不構成散佈（GPL-3.0 定義：僅透過網路與使用者互動、未傳遞副本者，不屬於 conveying）。 |
| bert-base-chinese tokenizer | Apache-2.0 | 執行時下載 |
| RapidOCR / PaddleOCR 辨識模型 | Apache-2.0 | 隨 `rapidocr_onnxruntime` 安裝 |
| 主模型（XGBoost / 邏輯迴歸） | 我們自己訓練 | 訓練資料來自上列來源，模型檔同樣不放 repo；需要時幾分鐘即可重建 |

## Python 套件

`ml/requirements.txt` 裡的套件以相依方式安裝，本 repo 不內含它們的原始碼：

- BSD 類：numpy、pandas、scikit-learn、torch
- Apache-2.0：xgboost、transformers、boto3、rapidocr_onnxruntime
- pypdfium2：Apache-2.0 / BSD-3（內含 BSD-3 授權的 PDFium）
- pillow：MIT-CMU（HPND）
- onnxruntime（rapidocr 的相依套件）：MIT

## 尚待決定

- 本 repo 自己的程式碼還沒有選定授權（目前沒有 LICENSE 檔）。
- 比賽資料集及其衍生資料能否公開，須依主辦單位規定。
