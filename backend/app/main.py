from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session, select

import threading
from app.streaming.consumer import start_consumer


from app.db import create_db_and_tables, get_session
from app.models import Case
from app.schemas import TxnIn, ScoreOut, CaseCreate, CaseOut
from app.core.config import settings
from app.services.scoring import Scorer

app = FastAPI(title="Fraud Backend API", version="0.1.0")

scorer = Scorer(mlflow_model_uri=settings.mlflow_model_uri)
stop_event = threading.Event()
consumer_thread: threading.Thread | None = None



@app.on_event("startup")
def on_startup():
    global consumer_thread
    create_db_and_tables()

    consumer_thread = threading.Thread(
        target=start_consumer,
        args=(stop_event,),
        daemon=True
    )
    consumer_thread.start()



@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/score", response_model=ScoreOut)
def score(txn: TxnIn):
    res = scorer.score(txn)
    return {"txn_id": txn.txn_id, "risk_score": res.risk_score, "reasons": res.reasons}


@app.post("/cases", response_model=CaseOut)
def create_case(payload: CaseCreate, session: Session = Depends(get_session)):
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
