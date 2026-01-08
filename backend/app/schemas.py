from datetime import datetime
from pydantic import BaseModel, Field


class TxnIn(BaseModel):
    txn_id: str
    user_id: str
    amount: float
    currency: str = "INR"
    merchant_id: str | None = None
    country: str | None = None
    device_id: str | None = None
    ip: str | None = None
    ts: datetime | None = None


class ScoreOut(BaseModel):
    txn_id: str
    risk_score: float = Field(ge=0.0, le=1.0)
    reasons: list[str]


class CaseCreate(BaseModel):
    txn_id: str
    user_id: str
    amount: float
    currency: str = "INR"
    risk_score: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = []


class CaseOut(BaseModel):
    id: int
    txn_id: str
    user_id: str
    amount: float
    currency: str
    risk_score: float
    status: str
    reasons: str
    created_at: datetime
