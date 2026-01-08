import json
import os
import threading
from kafka import KafkaConsumer

from app.core.config import settings
from app.streaming.topics import FEATURES_TOPIC
from app.streaming.feature_cache import UserFeatures, upsert

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", settings.kafka_bootstrap_servers)


def start_features_consumer(stop_event: threading.Event):
    consumer = KafkaConsumer(
        FEATURES_TOPIC,
        bootstrap_servers=BOOTSTRAP,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="fraud-features-consumer",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    while not stop_event.is_set():
        records = consumer.poll(timeout_ms=1000)
        if not records:
            continue

        for _tp, msgs in records.items():
            for msg in msgs:
                try:
                    evt = msg.value
                    # evt fields come from Flink TxnFeature JSON
                    feat = UserFeatures(
                        window_end_epoch_ms=int(evt["window_end_epoch_ms"]),
                        txn_count_60s=int(evt["txn_count_60s"]),
                        total_amount_60s=float(evt["total_amount_60s"]),
                        avg_amount_60s=float(evt["avg_amount_60s"]),
                    )
                    upsert(evt["user_id"], feat)
                except Exception as e:
                    print("features consumer error:", str(e))

    consumer.close()
