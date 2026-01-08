from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session, select

from app.streaming.features_consumer import start_features_consumer
features_thread: threading.Thread | None = None

import threading
from app.streaming.consumer import start_consumer

from app.auth import router as auth_router, CurrentUser
from app.audit import audit

from app.streaming.nonce_cleanup import start_nonce_cleanup
nonce_cleanup_thread: threading.Thread | None = None


from app.internal_routes import router as internal_router
from app.db import create_db_and_tables, get_session
from app.models import Case
from app.schemas import TxnIn, ScoreOut, CaseCreate, CaseOut
from app.core.config import settings
from app.services.scoring import Scorer

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded


app = FastAPI(title="Fraud Backend API", version="0.1.0")
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth_router)
app.include_router(internal_router)

scorer = Scorer(mlflow_model_uri=settings.mlflow_model_uri)
stop_event = threading.Event()
consumer_thread: threading.Thread | None = None


@app.on_event("startup")
def on_startup():
    global consumer_thread, features_thread
    create_db_and_tables()

    features_thread = threading.Thread(
        target=start_features_consumer,
        args=(stop_event,),
        daemon=True
    )
    features_thread.start()

    consumer_thread = threading.Thread(
        target=start_consumer,
        args=(stop_event,),
        daemon=True
    )
    consumer_thread.start()

    nonce_cleanup_thread = threading.Thread(
    target=start_nonce_cleanup,
    args=(stop_event,),
    daemon=True
    )
    nonce_cleanup_thread.start()





@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/score", response_model=ScoreOut)
def score(txn: TxnIn):
    res = scorer.score(txn)
    return {"txn_id": txn.txn_id, "risk_score": res.risk_score, "reasons": res.reasons}


@app.post("/cases", response_model=CaseOut)
def create_case(payload: CaseCreate, user: CurrentUser, session: Session = Depends(get_session)):
    audit("case_create", user=user, txn_id=payload.txn_id, risk_score=payload.risk_score)
    c = Case(
        txn_id=payload.txn_id,
        user_id=payload.user_id,
        amount=payload.amount,
        currency=payload.currency,
        risk_score=payload.risk_score,
        reasons=",".join(payload.reasons),
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


@app.get("/cases", response_model=list[CaseOut])
def list_cases(status: str | None = None, session: Session = Depends(get_session)):
    stmt = select(Case).order_by(Case.created_at.desc())
    if status:
        stmt = stmt.where(Case.status == status)
    return list(session.exec(stmt).all())


@app.patch("/cases/{case_id}", response_model=CaseOut)
def update_case_status(case_id: int, status: str, session: Session = Depends(get_session)):
    c = session.get(Case, case_id)
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")
    c.status = status
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


@app.on_event("shutdown")
def on_shutdown():
    stop_event.set()
