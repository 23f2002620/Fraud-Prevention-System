import os
import random
import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn

from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score


def make_synth(n=8000, seed=42):
    rng = np.random.default_rng(seed)

    # "Normal" behavior
    amount = rng.lognormal(mean=7.3, sigma=0.6, size=n)  # roughly small/medium
    amount = np.clip(amount, 10, 20000)

    has_device = rng.integers(0, 2, size=n)
    has_ip = rng.integers(0, 2, size=n)

    # velocity features (pretend from Flink)
    txn_count_60s = rng.poisson(lam=2.0, size=n)
    total_amount_60s = amount + rng.normal(0, 200, size=n)
    total_amount_60s = np.clip(total_amount_60s, 0, None)

    # Create "fraud-ish" samples (for evaluation only)
    y = np.zeros(n, dtype=int)
    fraud_idx = rng.choice(np.arange(n), size=int(0.08 * n), replace=False)
    y[fraud_idx] = 1
    amount[fraud_idx] = rng.uniform(30000, 150000, size=len(fraud_idx))
    txn_count_60s[fraud_idx] = rng.integers(8, 25, size=len(fraud_idx))
    total_amount_60s[fraud_idx] = amount[fraud_idx] * rng.uniform(1.0, 2.5, size=len(fraud_idx))

    df = pd.DataFrame({
        "amount": amount.astype(float),
        "has_device": has_device.astype(int),
        "has_ip": has_ip.astype(int),
        "txn_count_60s": txn_count_60s.astype(int),
        "total_amount_60s": total_amount_60s.astype(float),
    })

    return df, y


def main():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:8080"))
    mlflow.set_experiment("fraud-anomaly")

    X, y = make_synth()

    # IsolationForest outputs anomaly scores; we'll convert to 0..1 risk
    model = IsolationForest(
        n_estimators=300,
        contamination=0.08,
        random_state=42
    )
    model.fit(X)

    # score_samples: higher = more normal; invert to get "risk"
    normal_score = model.score_samples(X)
    risk = (normal_score.max() - normal_score) / (normal_score.max() - normal_score.min() + 1e-9)

    auc = roc_auc_score(y, risk)

    with mlflow.start_run():
        mlflow.log_params({
            "model": "IsolationForest",
            "n_estimators": 300,
            "contamination": 0.08
        })
        mlflow.log_metric("train_auc_proxy", float(auc))

        # Log model; MLflow sklearn flavor includes pyfunc for inference. [web:112]
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name="fraud_iforest"
        )

    print("Logged model. AUC(proxy):", auc)


if __name__ == "__main__":
    main()
