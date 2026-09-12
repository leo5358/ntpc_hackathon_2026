from fastapi import APIRouter
from api.schemas import RescoredItem, WhatIfRequest, WhatIfResponse
from api.services import institution_store

router = APIRouter(prefix="/api/whatif", tags=["whatif"])


@router.post("", response_model=WhatIfResponse)
async def whatif_rescore(req: WhatIfRequest):
    """Simulate risk score changes with custom feature weights."""
    weights_dict = {
        "penalty": req.weights.penalty,
        "residual": req.weights.residual,
        "isolation_forest": req.weights.isolation_forest,
        "opinion": req.weights.opinion,
        "flags": req.weights.flags,
    }
    items = institution_store.compute_whatif(
        weights=weights_dict,
        year=req.academic_year or 112,
        peer_group=req.peer_group,
    )
    return WhatIfResponse(
        academic_year=req.academic_year or 112,
        weights_applied=req.weights,
        items=[RescoredItem(**it) for it in items],
    )

