from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from api.schemas import InstitutionListItem, InstitutionDetail
from api.services import institution_store

router = APIRouter(prefix="/api/institutions", tags=["institutions"])


@router.get("", response_model=List[InstitutionListItem])
async def list_institutions(
    group: Optional[str] = Query(None, description="Filter by peer group: 市立幼兒園 or 非營利園"),
):
    """List institutions with their latest score and peer group."""
    items = institution_store.get_all_institutions(peer_group=group)
    return [InstitutionListItem(**item) for item in items]


@router.get("/{inst_id}", response_model=InstitutionDetail)
async def get_institution_detail(inst_id: str):
    """Get institution detail: history, SHAP breakdown, flags, penalties, opinion docs."""
    detail = institution_store.get_institution_detail(inst_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Institution '{inst_id}' not found")

    return InstitutionDetail(**detail)

