from typing import Optional
from fastapi import APIRouter, Query
from api.schemas import RankingItem, RankingsResponse
from api.services import institution_store

router = APIRouter(prefix="/api/rankings", tags=["rankings"])


@router.get("", response_model=RankingsResponse)
async def get_rankings(
    year: int = Query(112, description="Academic year (e.g. 110, 111, 112)"),
    group: Optional[str] = Query(None, description="Peer group: 市立幼兒園 or 非營利園"),
    min_score: Optional[float] = Query(None, alias="min", description="Minimum risk score threshold"),
):
    """Get sorted and filtered risk rankings."""
    items = institution_store.get_rankings(year=year, peer_group=group, min_score=min_score)
    return RankingsResponse(
        year=year,
        group=group,
        total=len(items),
        items=[RankingItem(**it) for it in items],
    )

