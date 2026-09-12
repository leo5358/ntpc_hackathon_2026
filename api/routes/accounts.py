"""Accounts drill-down route: budget vs actual financials."""
from fastapi import APIRouter
from api.schemas import AccountStatementResponse

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("/{inst_id}/{year}", response_model=AccountStatementResponse)
async def get_accounts_drilldown(inst_id: str, year: int):
    """Return budget vs actual financial statement items for institution and fiscal year.

    Infra stub: returns structured schema skeleton.
    """
    return AccountStatementResponse(
        inst_id=inst_id,
        inst_name=f"機構-{inst_id}",
        fiscal_year=year,
        items=[],
    )
