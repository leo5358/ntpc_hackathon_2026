"""Institutions route: listings and institution detail."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from api.schemas import InstitutionListItem, InstitutionDetail

router = APIRouter(prefix="/api/institutions", tags=["institutions"])


@router.get("", response_model=List[InstitutionListItem])
async def list_institutions(
    group: Optional[str] = Query(None, description="Filter by peer group: 市立幼兒園 or 非營利園"),
):
    """List institutions with their latest score and peer group.

    Infra stub: returns structured schema skeleton.
    """
    # Empty placeholder list or mock infrastructure stub
    return []


@router.get("/{inst_id}", response_model=InstitutionDetail)
async def get_institution_detail(inst_id: str):
    """Get institution detail: history, SHAP breakdown, flags, penalties, opinion docs.

    Infra stub: returns structured schema skeleton.
    """
    if not inst_id:
        raise HTTPException(status_code=404, detail="Institution not found")

    return InstitutionDetail(
        id=inst_id,
        name=f"機構-{inst_id}",
        peer_group="非營利園",
        operator=None,
        latest_score=0.0,
        history=[],
        shap_breakdown=[],
        flags=[],
        penalties=[],
        opinion_doc_count=0,
        source_urls=[],
    )
