from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas import CaseCreate, CaseOut
from app.models import Case
from app.internal_auth import verify_internal_signature
from app.audit import audit

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/cases", response_model=CaseOut, dependencies=[Depends(verify_internal_signature)])
def internal_create_case(payload: CaseCreate, session: Session = Depends(get_session)):
    # This endpoint is for internal services only (no JWT).
    c = Case(
        txn_id=payload.txn_id,
        user_id=payload.user_id,
        amount=payload.amount,
        currency=payload.currency,
        risk_score=payload.risk_score,
        reasons=",".join(payload.reasons),
        status="OPEN",
    )
    session.add(c)
    session.commit()
    session.refresh(c)

    audit("internal_case_create", txn_id=c.txn_id, risk_score=c.risk_score)
    return c
