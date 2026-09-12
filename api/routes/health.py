"""Health and data status route."""
from fastapi import APIRouter
from api.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """回傳服務狀態與資料可信度指標。

    這些數字會直接印在可簽陳的全市綜整報告上，因此只回傳有來源的量測值：
    parser_verified_rate 取自 ml/docs/MODEL_REPORT.md 的決算書解析驗算結果；
    opinion_coverage 目前沒有全市量測基礎（合規可取得的輿情幾乎不點名園所），
    回傳 None 讓前端標示為「未量測」，而非填入無來源的比率。
    """
    return HealthResponse(
        status="ok",
        freshness="2026-09-12T00:00:00Z",
        parser_verified_rate=246 / 249,
        parser_verified_scope="非營利園財報 OCR：249 頁中 246 頁通過逐列差異與合計雙重驗算",
        opinion_coverage=None,
        version="0.1.0",
    )
