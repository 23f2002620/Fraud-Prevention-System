from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.schemas import TxnIn


@dataclass
class ScoreResult:
    risk_score: float
    reasons: list[str]


class Scorer:
    """
    MVP scorer: deterministic rules.
    Later: load MLflow model (pyfunc) and blend rule + model.
    """

    def __init__(self, mlflow_model_uri: Optional[str] = None):
        self.mlflow_model_uri = mlflow_model_uri
        self.model = None

        # NOTE: keep MLflow optional so the API starts even without a model.
        if mlflow_model_uri:
            try:
                import mlflow.pyfunc
                self.model = mlflow.pyfunc.load_model(mlflow_model_uri)
            except Exception:
                self.model = None

    def score(self, txn: TxnIn) -> ScoreResult:
        reasons: list[str] = []
        score = 0.0

        # Rule 1: very high amount (demo threshold)
        if txn.amount >= 50000:
            score += 0.55
            reasons.append("high_amount")

        # Rule 2: suspicious country (example)
        if txn.country and txn.country.upper() not in {"IN", "INDIA"}:
            score += 0.25
            reasons.append("foreign_country")

        # Rule 3: missing device/ip signals
        if not txn.device_id or not txn.ip:
            score += 0.10
            reasons.append("missing_device_or_ip")

        # Optional ML: if model exists, blend it
        if self.model is not None:
            # Expecting model to accept a pandas.DataFrame
            import pandas as pd

            df = pd.DataFrame([{
                "amount": txn.amount,
                "country": (txn.country or ""),
                "has_device": 1 if txn.device_id else 0,
                "has_ip": 1 if txn.ip else 0,
            }])

            try:
                pred = self.model.predict(df)
                # Handle typical outputs: array([p]) or list
                p = float(pred[0])
                # Blend: 70% ML + 30% rules (simple)
                score = 0.3 * score + 0.7 * max(0.0, min(1.0, p))
                reasons.append("ml_model")
            except Exception:
                pass

        score = max(0.0, min(1.0, score))
        if score == 0.0:
            reasons.append("low_risk_baseline")

        return ScoreResult(risk_score=score, reasons=reasons)
