import json
import os
import threading
from kafka import KafkaConsumer, KafkaProducer
from app.streaming.feature_cache import get as get_features

import hmac
import hashlib


from app.db import engine
from sqlmodel import Session
from app.schemas import TxnIn
from app.models import Case
from app.services.scoring import Scorer
from app.streaming.topics import TXN_TOPIC, ALERT_TOPIC
from app.core.config import settings

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", settings.kafka_bootstrap_servers)

EVENT_SECRET = os.getenv("EVENT_SIGNING_SECRET", "KAFKA_EVENT_SECRET_CHANGE_ME").encode("utf-8")

def start_consumer(stop_event: threading.Event):
    consumer = KafkaConsumer(
        TXN_TOPIC,
        bootstrap_servers=BOOTSTRAP,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="fraud-backend-consumer",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    scorer = Scorer(mlflow_model_uri=settings.mlflow_model_uri)

    RISK_THRESHOLD = 0.60  # MVP threshold

    while not stop_event.is_set():
        records = consumer.poll(timeout_ms=1000)
        if not records:
            continue

        for _tp, msgs in records.items():
            for msg in msgs:
                try:
                    evt = msg.value
                    if not verify_sig(evt, msg.headers):
                        print("bad event signature; dropping txn_id=", evt.get("txn_id"))
                        continue

                    txn = TxnIn(**evt)

                    feats = get_features(txn.user_id)
                    s = scorer.score(txn, feats=feats)


                    if s.risk_score >= RISK_THRESHOLD:
                        # write case to Postgres
                        with Session(engine) as session:
                            c = Case(
                                txn_id=txn.txn_id,
                                user_id=txn.user_id,
                                amount=txn.amount,
                                currency=txn.currency,
                                risk_score=s.risk_score,
                                reasons=",".join(s.reasons),
                                status="OPEN",
                            )
                            session.add(c)
                            session.commit()
                            session.refresh(c)

                            alert = {
                                "case_id": c.id,
                                "txn_id": c.txn_id,
                                "user_id": c.user_id,
                                "risk_score": c.risk_score,
                                "reasons": s.reasons,
                            }
                            producer.send(ALERT_TOPIC, alert)
                except Exception as e:
                    # Keep MVP robust: don't crash consumer on bad events
                    print("consumer error:", str(e))

    consumer.close()


def header_dict(headers):
    if not headers:
        return {}
    return {k: v for (k, v) in headers}

def verify_sig(evt: dict, headers) -> bool:
    hd = header_dict(headers)
    sig = hd.get("x-sig")
    if not sig:
        return False

    payload = json.dumps(evt, separators=(",", ":"), sort_keys=True).encode("utf-8")
    expected = hmac.new(EVENT_SECRET, payload, hashlib.sha256).hexdigest().encode("utf-8")
    return hmac.compare_digest(expected, sig)
