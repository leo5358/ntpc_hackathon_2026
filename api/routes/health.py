"""Health and data status route."""
from fastapi import APIRouter
from api.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Return system freshness, parser verified-rate, and opinion coverage.

    Infra stub: returns initialized telemetry structure.
    """
    return HealthResponse(
        status="ok",
        freshness="2026-09-12T00:00:00Z",
        parser_verified_rate=0.965,
        opinion_coverage=0.35,
        version="0.1.0",
    )
