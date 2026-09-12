from fastapi import APIRouter, HTTPException
from api.schemas import AccountItem, AccountStatementResponse
from api.services import institution_store

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("/{inst_id}/{year}", response_model=AccountStatementResponse)
async def get_accounts_drilldown(inst_id: str, year: int):
    """Return budget vs actual financial statement items for institution and fiscal year."""
    detail = institution_store.get_institution_detail(inst_id)
    name = detail["name"] if detail else f"機構-{inst_id}"
    items = institution_store.get_accounts(inst_id, year)
    return AccountStatementResponse(
        inst_id=inst_id,
        inst_name=name,
        fiscal_year=year,
        items=[AccountItem(**item) for item in items],
    )

