import json
import os
import threading
import time
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

from app.db import engine
from sqlmodel import Session
from app.schemas import TxnIn
from app.models import Case
from app.services.scoring import Scorer
from app.streaming.topics import TXN_TOPIC, ALERT_TOPIC
from app.core.config import settings

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", settings.kafka_bootstrap_servers)

def start_consumer(stop_event: threading.Event):
    # 🔁 Retry until Kafka is ready
    while True:
        try:
            consumer = KafkaConsumer(
                TXN_TOPIC,
                bootstrap_servers=BOOTSTRAP,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                group_id="fraud-backend-consumer",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                api_version_auto_timeout_ms=10000,
            )

            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )

            print("✅ Connected to Kafka")
            break

        except NoBrokersAvailable:
            print("⏳ Kafka not ready yet, retrying in 5 seconds...")
            time.sleep(5)

    scorer = Scorer(mlflow_model_uri=settings.mlflow_model_uri)
    RISK_THRESHOLD = 0.60

    while not stop_event.is_set():
        records = consumer.poll(timeout_ms=1000)
        if not records:
            continue

        for _tp, msgs in records.items():
            for msg in msgs:
                try:
                    evt = msg.value
                    txn = TxnIn(**evt)
                    s = scorer.score(txn)

                    if s.risk_score >= RISK_THRESHOLD:
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
                    print("consumer error:", str(e))

    consumer.close()
