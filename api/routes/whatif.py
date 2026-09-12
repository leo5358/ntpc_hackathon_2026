"""What-if rescoring route for sandbox simulations."""
from fastapi import APIRouter
from api.schemas import WhatIfRequest, WhatIfResponse

router = APIRouter(prefix="/api/whatif", tags=["whatif"])


@router.post("", response_model=WhatIfResponse)
async def whatif_rescore(req: WhatIfRequest):
    """Simulate risk score changes with custom feature weights.

    Infra stub: returns structured schema skeleton.
    """
    return WhatIfResponse(
        academic_year=req.academic_year or 112,
        weights_applied=req.weights,
        items=[],
    )
