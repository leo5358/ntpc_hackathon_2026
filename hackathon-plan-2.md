# 小小守護員 Smart Watchdog — Engineering Plan

## Context

`/home/shiuintw/2609Hackathon` is a hackathon kit with no code: a problem brief, an AWS/Kiro guide, and
`dataset.zip` (162 PDFs of Taiwanese education-fund financial disclosures). The brief asks for a
**quantifiable, explainable risk score** for childcare institutions (教保機構) that moves inspection from
reactive to proactive.

Two gaps in the original plan are now closed by external open data, researched and verified:

1. **裁罰紀錄 (penalty labels)** — found, with 11 positive labels inside our scope.
2. **輿情分析 (public-opinion model)** — no ready-made labelled corpus exists; a build path is specified.

### Decisions taken

| Decision | Choice |
| --- | --- |
| Scope | Dataset only — 22 市立幼兒園 + 38 非營利園 (~60 institutions) |
| Deployment | Full AWS (S3 + SageMaker + Bedrock/Comprehend + Lambda + S3 static site) |
| Front-end | React + Vite + Tailwind |

---

## Gap 1 closed — 裁罰紀錄 found (this changes the modelling)

`github.com/kiang/ap.ece.moe.edu.tw` (MIT, updated **daily** by cron) is a permanent mirror of
全國教保資訊網. This matters because **the official site deletes penalty records once their display period
expires** — the mirror keeps them. One Tainan preschool shows 2 penalties officially but 15 in the mirror.

Served from `https://kiang.github.io/ap.ece.moe.edu.tw/`:

| Path | Size | Contents |
| --- | --- | --- |
| `punish_all.json` | 1.76 MB | All penalties, **indexed by person** (`行為人：X` / `負責人：X`) |
| `data/punish/新北市/<園名>.json` | — | **Penalties per institution** ← the label source |
| `preschools.json` | 10.4 MB | GeoJSON of 6,807 preschools, geocoded, with basics |
| `data/新北市.csv` | 345 KB | 新北市 institution roster + attributes |
| `data/slip109…slip114/新北市/` | — | **收費明細 by 學年度 109–114** ← the brief's missing fee data |
| `data/punish_note/`, `data/features/` | — | Notes; per-school GeoJSON features |

Per-institution record shape (verified — 新北市北大非營利幼兒園):

```json
[["2024/07/12", "新北府教幼字第1131330490號",
  "幼兒教育及照顧法第58條第1項第5款(111/6/29修正公布)",
  "第17條第1項幼兒園之5歲班級未依規定配置教師。",
  "負責人：邱健凱", "罰鍰：30,000元"]]
```
→ `[date, 文號, 法條, 違規事實, 責任人, 罰鍰]`

### Label overlap with our scope — verified

Of the 38 非營利園 in `dataset.zip`, **11 have penalty records** (29% positive rate):

`N07北大` `N09安興` `N11新林` `N12昌福` `N15新月` `N17中正` `N18福營` `N25碧城` `N29東湖` `N30文中`
(plus 前鋒/中華電信 entries outside our roster)

This list is **complete for 非營利園**: the directory sorts by Unicode codepoint, and every
`新北市…非營利幼兒園` name sorts before `新北市私立…` (私 U+79C1), which is where the listing truncated.
The 市立幼兒園 count is **not yet known** — `新北市立…` (立 U+7ACB) sorts *after* the truncation point and
must be re-listed with pagination on day 1.

**Several 園 appear twice under different 委託 operators** (北大, 安興, 文中, 昌福 each have two files).
Operator turnover is therefore itself an observable feature, not just a naming artefact.

### The signal that validates the whole approach

The 北大 penalty is for **「5歲班級未依規定配置教師」 — understaffing**. The planned financial feature
`personnel_underspend` (under-execution of 用人費用) measures exactly that from the settlement PDFs. This
is a directly testable causal hypothesis, and it is the story to tell in the demo.

### Consequence: supervised learning is now viable

Replaces the previous unsupervised-only design. With 11/38 positives:

- **Target:** did institution *i* receive a penalty during 學年度 *t+1*?
- **Features:** financials + fees + 輿情 from 學年度 *t* — strictly prior, so no leakage.
- **Year alignment (critical):** penalty dates are Gregorian; 學年度 *t* runs Aug *t*+1911 → Jul *t*+1912.
  So 2024/07/12 falls in **112學年度**, not 113. Map every penalty date through `roc.py` before joining.
- **Small-*n* discipline:** 38 institutions × 4 學年度 ≈ 152 rows. Use stratified group *k*-fold
  **grouped by institution** (never split one 園 across folds), report AUC with confidence intervals, and
  keep the model shallow (`max_depth 3`, heavy regularisation). Treat unsupervised anomaly scores as
  features feeding the supervised model, not as a separate pipeline.

Unsupervised anomaly detection is **retained** for the 22 市立幼兒園, whose label status is unconfirmed.

---

## Gap 2 closed — 輿情分析 module

### Finding: no ready-made dataset exists

Searched thoroughly. There is **no labelled Traditional-Chinese kindergarten-opinion corpus**. What exists
is either generic-domain, Simplified Chinese, or unlabelled. So the plan uses zero-shot models for
production and **builds a small gold set for evaluation** — that gold set is a deliverable in itself.

### Available resources (verified)

| Resource | What it is | Use here |
| --- | --- | --- |
| [NTUSD](https://github.com/ntunlplab/NTUSD) | 11,088 sentiment words (2,812 pos / 8,276 neg), **Traditional Chinese**, free on GitHub | Explainable lexicon baseline |
| ANTUSD (Academia Sinica NLPSA) | 26,021 words + CopeOpi scores, linked to E-HowNet | Richer lexicon; **free but requires application** — apply day 1, it may not arrive in time |
| [Gossiping-Chinese-Corpus](https://github.com/zake7749/Gossiping-Chinese-Corpus) | 774,114 PTT 八卦板 QA pairs, Traditional Chinese, unlabelled | Domain vocabulary, negation/slang patterns |
| `Riyuechang/PTT-Corpus-100K_Gossiping-1400-39400_v2` (HF) | PTT corpus | Same |
| **Amazon Comprehend** `DetectSentiment` | Officially supports **`zh-TW`** (confirmed in AWS docs — Sentiment covers "all supported languages") | Zero-shot polarity, no training |
| **Amazon Bedrock (Claude)** | Zero/few-shot, strong Traditional Chinese, structured JSON output | Primary aspect-based classifier |

Rejected: **`senti_c`** — the one purpose-built Traditional-Chinese sentiment toolkit, but it pins
`transformers==2.11.0` / TensorFlow 2.2 / Python 3.7–3.8. It will not install on Python 3.12. Do not spend
time on it.

### 輿情 data sources

| Source | Access | Realistic yield for ~60 公共化園 |
| --- | --- | --- |
| Google Places API reviews | Official API | **Hard cap of 5 reviews per place** (confirmed, still true in 2026) → ~300 reviews total |
| Google News RSS | `news.google.com/rss/search?q=<園名>+幼兒園&hl=zh-TW` | Sparse but high-severity when present |
| PTT `BabyMother` board | `www.ptt.cc/bbs/BabyMother` | Moderate; parenting discussion |
| Dcard 親子板 | Public JSON API | Moderate |
| 新北市議會 質詢紀錄 | Public | Occasional, high-signal |

**Honest constraint:** individual 公共化園 attract little online discussion — most volume concerns 私立園.
So 輿情 is a **secondary signal with explicit coverage reporting**, never a silent zero. An institution
with no coverage must render as "無輿情資料", not as "low risk".

### Model design (`pipeline/nlp/`)

```
raw text ──► L0 entity match ──► L1 risk-topic ──► L2 polarity ──► L3 aggregate
             園名 + aliases        6 categories      -1..+1          severity × recency
             (preschools.json)     Bedrock Claude    Comprehend      → opinion_risk 0..1
                                                     zh-TW
```

- **L0 — entity matching.** Names are messy (`新北市北大非營利幼兒園(委託明新科技大學辦理)` vs 「北大非營利」).
  Build an alias table from `preschools.json` + the `N##` roster; match on normalised core name; require a
  district match to disambiguate. Log unmatched mentions for manual review.
- **L1 — risk-topic classification.** Six categories, chosen to mirror actual 裁罰 法條:
  `不當管教/體罰`, `餐食與衛生`, `收費爭議`, `師資流動/人力不足`, `設施安全`, `行政與立案`.
  Bedrock Claude with a constrained JSON schema; zero-shot, no training data required.
- **L2 — polarity.** `comprehend.detect_sentiment(LanguageCode="zh-TW")`, plus an NTUSD lexicon score as an
  interpretable cross-check. Disagreement between the two is surfaced, not hidden.
- **L3 — aggregation.** `opinion_risk = Σ (severity_weight[topic] × polarity × exp(-age_days/365)) / coverage`.

**Evaluation — the gold set.** Sample ~400 sentences across sources, label by hand (2 annotators, report
Cohen's κ), and score L1+L2 by macro-F1 against it. This is the only honest way to claim the module works,
and it is cheap. Ship the gold set as `data/gold/opinion_gold.jsonl`.

**Optional distillation.** If latency or cost matters, bootstrap-label ~5k sentences with Claude, then
fine-tune a small Traditional-Chinese BERT on SageMaker. Only worth it after the gold set exists.

---

## Validated technical findings — PDF extraction

Confirmed against the real PDFs:

- **`基金用途明細表` is the core financial feature source.** Every 分基金 section carries 預算數 vs 決算數
  per expense category (用人費用 / 正式員額薪資 / 水電費 / 修理保養及保固費 …).
- **Section anchors:** sections open with `附屬單位決算之分決算`; page headers carry
  `新北市地方教育發展基金—<機構名>`; footers embed the 5-digit code (`13111-9`). FY112 第一冊 has 18
  sections at pages 141, 229, 261, 289, …
- **Naive `extract_text()` scrambles these tables.** Coordinate clustering via pypdf `visitor_text`
  (group by `tm[5]` within ±2pt, sort by `tm[4]`) reconstructs rows correctly.
- **Do not parse the 比較增減 columns** — they float between adjacent rows. Parse `(name, 預算數, 決算數)`
  and derive variance. Cross-checked on 24 consecutive rows of p239–240: derived Δ matched the printed
  value verbatim **24/24**.
- **Do not parse the 用途別 code from the blob** — the previous row's % bleeds into it
  (`4.93` + `5 基金用途` → `4.935`). Account **names** are a controlled vocabulary; map name → code.
- **Throughput:** 752 pages in ~9s; 28 pages (3.7%) hit the known `IndirectObject` font bug — skip them.
- **Amazon Textract does not support Traditional Chinese** (corrects the note in `CLAUDE.md`). Use
  **PaddleOCR `chinese_cht`** in a SageMaker Processing job; Bedrock Claude vision is the fallback.

---

## System architecture

```
 dataset.zip                          kiang/ap.ece.moe.edu.tw            news · PTT · Dcard · Google
   │                                    (daily mirror, MIT)                        │
   ├ 公校決算書 (text) ─► pypdf coord parser      │                                  │
   └ 非營利園財報 (scan) ─► PaddleOCR chinese_cht │                                  │
                    │                            │                                  ▼
                    │                  裁罰 · 收費 · 名冊                    nlp/ L0→L1→L2→L3
                    │                            │                     Bedrock Claude + Comprehend zh-TW
                    ▼                            ▼                                  │
             ┌──────────────── s3://kiro-workshop-<sfx>/curated/*.parquet ──────────┘
             │
             ▼   s4_features.py  — financial + fee + opinion + operator-churn, peer-normalised
             │
     ┌───────┼─────────────────────┬────────────────────────┐
     ▼       ▼                     ▼                        ▼
  XGBoost  XGBoost           IsolationForest            rule flags
 (penalty) (residual)     (市立園, unlabelled)        (Benford, 其他…)
     └───────┴──────────┬──────────┴────────────────────────┘
                        ▼
          composite score + SHAP → scores/latest.parquet
                        │
          FastAPI on Lambda (Function URL) ── SageMaker endpoint (what-if)
                        │
          React + Vite + Tailwind → S3 static site
```

## Repo layout

```
2609Hackathon/
├── config.yaml                     # bucket, region, role, weights, peer groups
├── infra/{bootstrap.py,deploy_api.py}
├── pipeline/
│   ├── common/{pdf_tables.py,accounts.py,roc.py,names.py}
│   ├── s0_ingest.py                # selective unzip → S3 raw/
│   ├── s1_parse_gongxiao.py        # 決算書 → tidy rows            ★
│   ├── s2_ocr_nonprofit.py         # PaddleOCR Processing job
│   ├── s3_external.py              # kiang mirror: 裁罰 + 收費 + 名冊  ★ NEW
│   ├── s4_features.py              # forensic + fee + opinion features ★
│   ├── s5_train.py                 # SageMaker XGBoost (penalty + residual)
│   └── s6_score.py                 # composite + SHAP → scores/
├── pipeline/nlp/                   # ★ NEW
│   ├── collect.py                  # news RSS / PTT / Dcard / Places
│   ├── match.py                    # L0 entity matching
│   ├── classify.py                 # L1 Bedrock, L2 Comprehend, NTUSD baseline
│   └── aggregate.py                # L3 opinion_risk
├── data/gold/opinion_gold.jsonl    # hand-labelled eval set
├── api/{main.py,handler.py}
└── web/                            # React + Vite + Tailwind
```

---

## Stage 1 — PDF table extraction (`pipeline/common/pdf_tables.py`)

```python
"""Coordinate-based table row reconstruction for 決算書 PDFs.

pypdf's extract_text() loses column alignment on these tables; the text-matrix
y/x offsets exposed via visitor_text do not.
"""
import re
import pypdf


def page_lines(page, y_tol: float = 2.0) -> list[str]:
    """Reconstruct visual rows: cluster text runs by y, order within a row by x."""
    parts: list[tuple[float, float, str]] = []

    def visit(text, cm, tm, font_dict, font_size):
        if text.strip():
            parts.append((tm[5], tm[4], text.strip()))

    page.extract_text(visitor_text=visit)
    parts.sort(key=lambda p: (-p[0], p[1]))

    rows, cur, cur_y = [], [], None
    for y, x, t in parts:
        if cur_y is None or abs(y - cur_y) <= y_tol:
            cur.append((x, t))
            cur_y = y if cur_y is None else cur_y
        else:
            rows.append(cur)
            cur, cur_y = [(x, t)], y
    if cur:
        rows.append(cur)
    return ["  ".join(t for _, t in sorted(r)) for r in rows]


# 科目名 + 預算數 + 決算數.  The 比較增減 columns are deliberately NOT captured —
# they float between adjacent rows.  Variance is derived and cross-checked instead.
ROW_RE = re.compile(
    r"(?<!\d)\d{0,4}\s*"                        # bleed-through % + code (discarded)
    r"([一-鿿（(][一-鿿（）()、之及與]{1,14})"    # 科目名
    r"\s+([\d,]{4,})\s+([\d,]{4,})"             # 預算數, 決算數
)

def parse_amount(s: str) -> int:
    return int(s.replace(",", ""))
```

## Stage 2 — Section parsing (`pipeline/s1_parse_gongxiao.py`)

```python
"""決算書 → tidy rows: (inst_id, inst_name, fiscal_year, account, budget, actual)."""
import re
import pypdf
from pipeline.common.pdf_tables import page_lines, ROW_RE, parse_amount
from pipeline.common.accounts import canonical_account

HEADER_RE = re.compile(r"新北市地方教育發展基金[—\-–]\s*(新北市[^\s]{2,15})")
CODE_RE   = re.compile(r"\b(\d{5})-\d+\b")           # footer page label, e.g. 13111-9
TABLE_RE  = re.compile(r"(基金用途明細表|基金來源明細表)")


def parse_book(path: str, fiscal_year: int) -> list[dict]:
    out, name, code, table = [], None, None, None
    reader = pypdf.PdfReader(path)

    for pno, page in enumerate(reader.pages, start=1):
        try:
            lines = page_lines(page)
        except Exception:                 # known IndirectObject font bug (~3.7% of pages)
            continue
        head, whole = "\n".join(lines[:6]), "\n".join(lines)

        if (m := HEADER_RE.search(head)):
            name = m.group(1)
        if (m := CODE_RE.search(whole)):
            code = m.group(1)
        if (m := TABLE_RE.search(head)):
            table = m.group(1)
        elif any(k in head for k in ("總說明", "資產明細表", "決算之分決算")):
            table = None                  # left the statement

        if table != "基金用途明細表" or not code:
            continue

        for line in lines:
            if not (m := ROW_RE.search(line)):
                continue
            acct = canonical_account(m.group(1))
            if acct is None:              # outside the controlled vocabulary — skip, don't guess
                continue
            budget, actual = parse_amount(m.group(2)), parse_amount(m.group(3))
            out.append(dict(
                inst_id=code, inst_name=name, fiscal_year=fiscal_year,
                account_code=acct.code, account_name=acct.name, category=acct.category,
                budget=budget, actual=actual, variance=actual - budget,
                variance_pct=(actual - budget) / budget if budget else None,
                source_page=pno,
                # integrity: the printed Δ must appear verbatim in the same visual row
                verified=f"{abs(actual - budget):,}" in line,
            ))
    return out
```

**Guardrail:** assert `verified` rate > 95% per book, else fail loudly. Silent wrong numbers are worse
than a crash.

## Stage 3 — External data (`pipeline/s3_external.py`)

```python
"""Pull 裁罰 / 收費 / 名冊 from the kiang mirror (MIT, daily cron)."""
BASE = "https://kiang.github.io/ap.ece.moe.edu.tw"
GH   = "https://api.github.com/repos/kiang/ap.ece.moe.edu.tw/contents/docs"

PUNISH_FIELDS = ["date", "doc_no", "law", "violation", "responsible", "fine"]

def fetch_punishments(city: str = "新北市") -> list[dict]:
    """One row per penalty. Paginate the GitHub contents API — the listing is long."""
    files = gh_list(f"{GH}/data/punish/{city}")          # must page: >50 entries
    rows = []
    for f in files:
        for rec in get_json(f["download_url"]):
            r = dict(zip(PUNISH_FIELDS, rec))
            r["inst_name_raw"] = f["name"].removesuffix(".json")
            r["fine_ntd"] = parse_fine(r["fine"])         # "罰鍰：30,000元" → 30000
            r["academic_year"] = date_to_academic_year(r["date"])  # 2024/07/12 → 112學年度
            rows.append(r)
    return rows
```

`names.py` maps `inst_name_raw` → our `N##` roster: strip `(委託…辦理)`, strip `新北市`/`私立`/`非營利幼兒園`
affixes, then exact-match the core name; keep the operator string as its own `operator` field so operator
turnover becomes a feature.

Fee data: `data/slip{109..114}/新北市/` gives 收費明細 per 學年度 — joins directly to the 財報 years.

## Stage 4 — Features (`pipeline/s4_features.py`)

Per (institution, 學年度), peer-normalised within `市立幼兒園` / `非營利園`:

**Financial execution** — `exec_rate[cat]` = 決算/預算; `abs_variance_share` = Σ|var| / total budget;
`n_categories_over_20pct`.

**Structure** — `mix[cat]` (用人 / 服務 / 材料 / 租金 / 購建 / 獎補助 / 其他); `hhi` = Σ mix²;
`other_share` (opacity proxy).

**Safety-relevant underspend** — the highest-value group, and the one the 北大 penalty validates:
`personnel_underspend` = 1 − exec_rate[用人費用] (**understaffing proxy**);
`maintenance_underspend` (deferred maintenance); `utilities_underspend`.

**Fee (new)** — fee level vs peer median; YoY fee jump; fee-to-declared-cost ratio; mismatch between
收費明細 and 財報 revenue.

**Governance (new)** — `operator_changed` (from the duplicate 委託 files); count of distinct operators;
years since last change.

**Opinion (new)** — `opinion_risk`, per-topic sub-scores, and `opinion_coverage` (documents found).

**Digit forensics** — `benford_mad`; `round_number_share`.

**Temporal** — YoY deltas; `volatility` = std of exec_rate; peer z-scores.

All features are computed from 學年度 *t* only, and joined to a label from *t+1*.

## Stage 5 — Models (`pipeline/s5_train.py`)

**A. Penalty classifier (primary, supervised).** SageMaker built-in XGBoost,
`objective=binary:logistic`, `scale_pos_weight` for the 29% base rate, `max_depth=3`, `eta=0.05`,
`num_round=200`, `subsample=0.8`. Grouped stratified *k*-fold by institution. Report AUC + PR-AUC with
bootstrap CIs — with 38 institutions, a point estimate alone is not credible.

**B. Residual model (supervised, abundant targets).** Predicts 決算數 from 預算數 + size + year + peer
context. `residual_z` feeds model A as a feature *and* stands alone for the 市立園.

**C. Isolation Forest** — for the 22 市立幼兒園 whose label status is unconfirmed.

**D. Rule flags** — each with a weight and a plain-Chinese explanation.

```python
import boto3                    # boto3-first per aws_util.pdf; region pinned us-west-2
session = boto3.Session(profile_name="workshop", region_name="us-west-2")
sm = session.client("sagemaker")

sm.create_training_job(
    TrainingJobName=f"kiro-xgb-penalty-{stamp}",
    AlgorithmSpecification={"TrainingImage": xgb_image, "TrainingInputMode": "File"},
    RoleArn=EXECUTION_ROLE_ARN,                        # kiro-sagemaker-execution-role
    InputDataConfig=[{"ChannelName": "train", "DataSource": {"S3DataSource": {
        "S3Uri": f"s3://{BUCKET}/curated/train.csv",   # headerless, label in column 0
        "S3DataDistributionType": "FullyReplicated",
        "S3DataType": "S3Prefix"}}, "ContentType": "text/csv"}],
    OutputDataConfig={"S3OutputPath": f"s3://{BUCKET}/models/"},
    ResourceConfig={"InstanceType": "ml.m5.xlarge", "InstanceCount": 1, "VolumeSizeInGB": 20},
    StoppingCondition={"MaxRuntimeInSeconds": 3600},
    HyperParameters={"objective": "binary:logistic", "num_round": "200",
                     "max_depth": "3", "eta": "0.05", "subsample": "0.8",
                     "scale_pos_weight": "2.5", "eval_metric": "auc"},
)
```

**Composite** (weights in `config.yaml`, tunable live in the demo):

```
risk = 100 * (0.45 * p_penalty + 0.20 * norm(residual_z)
            + 0.15 * iso_score + 0.10 * opinion_risk + 0.10 * flag_weight_sum)
```

Every point traces to a SHAP contribution, a fired flag, or a cited document, each with a source page or URL.

## Stage 6 — Backend (`api/main.py`)

FastAPI reading `scores/latest.parquet` from S3 at cold start (~60 × 4 rows is tiny), on a **Lambda
Function URL** via Mangum — no API Gateway.

```
GET  /api/institutions                → list + latest score + peer group
GET  /api/institutions/{id}           → history, SHAP breakdown, flags, penalties, opinion docs
GET  /api/rankings?year=&group=&min=  → filtered ranking
GET  /api/accounts/{id}/{year}        → 預算 vs 決算 drill-down
GET  /api/opinion/{id}                → matched documents, topics, coverage
POST /api/whatif                      → reweight and rescore
GET  /api/health                      → freshness, parser verified-rate, opinion coverage
```

## Stage 7 — Front-end (`web/`)

- **Ranking** (`/`) — sortable, colour-banded, filter by group/year/score, CSV export of the inspection list.
- **Institution detail** (`/i/:id`) — score gauge; SHAP waterfall; 預算-vs-決算 bars; multi-year trend;
  **penalty timeline**; **opinion panel** with cited sources and an explicit "無輿情資料" state.
- **Methodology** (`/method`) — features, weights, gold-set F1, and a limitations panel stating the score
  is an anomaly indicator, not an accusation.
- **Weight sandbox** — sliders bound to `POST /api/whatif`.

Charts: Recharts. `node` is not installed — install Node 20 before this stage.

---

## AWS specifics

All pinned to **`us-west-2`**, per `aws_util.pdf`:

- Workshop Studio credentials → a **named profile** (`workshop`), never `[default]`; pass `profile_name`
  explicitly. Verify with `sts.get_caller_identity()` before every stage.
- Create `kiro-sagemaker-execution-role` trusting `sagemaker.amazonaws.com` with
  `AmazonSageMakerFullAccess` + `AmazonS3FullAccess`. The service-linked role will not work.
- Bucket `kiro-workshop-<suffix>` with `LocationConstraint=us-west-2`.
- Prefixes: `raw/ curated/ features/ models/ scores/ opinion/ web/`.
- **Verify Bedrock model access on day 1** — Workshop Studio accounts do not always have it enabled.
  Fallback: Comprehend `zh-TW` + NTUSD lexicon only.
- **Delete the SageMaker endpoint when not demoing.** The API serves from Parquet; the endpoint is only
  for live what-if.

## Week schedule

| Day | Work | Done when |
| --- | --- | --- |
| 1 | Bootstrap AWS; **pull kiang mirror, confirm 市立園 penalty count (paginated)**; apply for ANTUSD; verify Bedrock access; `pdf_tables.py` | Label table built; 非營利 11/38 reproduced |
| 2 | 決算書 parsing (第五冊 ×3 years) + OCR job for 非營利園 | verified-rate >95%; OCR reconciliation passing |
| 3 | `s3_external.py` fees + roster; `s4_features.py` | Feature matrix with financial + fee + governance |
| 4 | 輿情 collection + L0–L3; hand-label the 400-sentence gold set | macro-F1 reported on gold set |
| 5 | XGBoost penalty + residual + IsolationForest + flags; composite | `scores/latest.parquet`; AUC with CIs |
| 6 | FastAPI on Lambda + React UI | Endpoints live; ranking + detail + SHAP working |
| 7 | Validation, methodology page, demo script, buffer | Top/bottom-5 face-validity review done |

## Verification

```bash
python -m infra.bootstrap --check                  # credentials, bucket, role, Bedrock access

python -m pipeline.s1_parse_gongxiao --book 第五冊 --year 112 --assert-verified 0.95
python -m pipeline.s3_external --city 新北市 --report-overlap   # expect 11/38 非營利園 matched
python -m pipeline.nlp.classify --eval data/gold/opinion_gold.jsonl   # macro-F1

make pipeline && make score
python -m pipeline.s6_score --report               # top 10 with flags, penalties, source pages

curl "$API_URL/api/health"
curl "$API_URL/api/rankings?year=112&group=非營利園"
cd web && npm run dev
```

**Manual gate before demo:** open the top-3 institutions' source PDF pages and penalty records and confirm
every flagged number matches the source.

## Risks

| Risk | Mitigation |
| --- | --- |
| **38 institutions, 11 positives — very small *n*** | Grouped CV, shallow trees, bootstrap CIs; present as decision support, never as a verdict. Unsupervised score retained as a cross-check |
| 市立幼兒園 penalty count still unknown (listing truncated) | Day-1 task; paginate the contents API. If zero, 市立園 stay unsupervised-only |
| Third-party mirror could stall or vanish | MIT-licensed — **vendor a dated snapshot into S3 on day 1** and pin to it; treat live pulls as refresh, not dependency |
| 輿情 coverage near zero for 公共化園 | Reported explicitly as `opinion_coverage`; low weight (0.10); UI shows "無輿情資料" rather than implying safety |
| Bedrock not enabled on the workshop account | Fallback to Comprehend `zh-TW` + NTUSD lexicon; verified day 1 |
| OCR digit errors on 132 scanned reports | Cross-foot + balance reconciliation; exclude and flag rather than score bad data |
| Workshop Studio session tokens expire | Every step scripted and re-runnable; all state in S3 |
| Naming people in penalty records (負責人/行為人) | Data is public, but **do not surface individuals' names in the UI** — aggregate to institution level |

## Follow-up

Update `CLAUDE.md`: Amazon Textract does not support Traditional Chinese — replace with PaddleOCR
(`chinese_cht`) / Bedrock vision. Also add the kiang mirror as the canonical 裁罰/收費 source.

## Sources

- [政府裁罰資料永久公開！「台灣幼兒園地圖」](https://data.gov.tw/news/27550)
- [kiang/preschools](https://github.com/kiang/preschools) · [kiang/ap.ece.moe.edu.tw](https://github.com/kiang/ap.ece.moe.edu.tw)
- [裁罰紀錄查詢-全國教保資訊網](https://ap.ece.moe.edu.tw/webecems/punishSearch.aspx)
- [NTUSD](https://github.com/ntunlplab/NTUSD) · [ANTUSD paper](https://aclanthology.org/L16-1428/) · [Academia Sinica NLPSA](http://academiasinicanlplab.github.io/)
- [Gossiping-Chinese-Corpus](https://github.com/zake7749/Gossiping-Chinese-Corpus)
- [Amazon Comprehend supported languages](https://docs.aws.amazon.com/comprehend/latest/dg/supported-languages.html)
- [senti_c](https://github.com/hsinmin/senti_c) (rejected — legacy pins)
