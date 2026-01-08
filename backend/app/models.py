from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Case(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    txn_id: str = Field(index=True)
    user_id: str = Field(index=True)
    amount: float
    currency: str = "INR"

    risk_score: float = 0.0  # 0..1
    status: str = Field(default="OPEN", index=True)  # OPEN | CONFIRMED_FRAUD | FALSE_POSITIVE
    reasons: str = ""  # comma-separated for MVP

    created_at: datetime = Field(default_factory=datetime.utcnow)
