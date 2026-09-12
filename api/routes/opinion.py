"""Public opinion analysis route."""
from fastapi import APIRouter
from api.schemas import OpinionResponse

router = APIRouter(prefix="/api/opinion", tags=["opinion"])


@router.get("/{inst_id}", response_model=OpinionResponse)
async def get_institution_opinion(inst_id: str):
    """Return sentiment and topic classification details for institution.

    Infra stub: returns structured schema skeleton.
    """
    return OpinionResponse(
        inst_id=inst_id,
        inst_name=f"機構-{inst_id}",
        opinion_risk=0.0,
        coverage=0,
        has_opinion=False,
        topic_distribution={},
        documents=[],
    )
