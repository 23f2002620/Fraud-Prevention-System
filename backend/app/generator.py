import json
import os
import random
import time
from datetime import datetime, timezone
from kafka import KafkaProducer
import hmac
import hashlib
import os

EVENT_SECRET = os.getenv("EVENT_SIGNING_SECRET", "KAFKA_EVENT_SECRET_CHANGE_ME").encode("utf-8")


from app.streaming.topics import TXN_TOPIC

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

MERCHANTS = ["m_amazon", "m_flipkart", "m_uber", "m_netflix", "m_grocery", "m_travel"]
COUNTRIES = ["IN", "IN", "IN", "IN", "SG", "AE", "US"]  # mostly IN, some foreign
DEVICES = ["d1", "d2", "d3", "d4", None]
IPS = ["1.2.3.4", "10.0.0.8", "172.16.0.2", None]


def synth_txn(i: int) -> dict:
    # 90% normal, 10% fraudulent-ish spikes
    fraudish = (i % 10 == 0)

    amount = random.uniform(50, 5000)
    if fraudish:
        # high amount spike
        amount = random.uniform(50000, 120000)

    user_id = f"u{random.randint(1, 25)}"
    txn_id = f"txn_{int(time.time()*1000)}_{i}"

    country = random.choice(COUNTRIES) if fraudish else "IN"
    device_id = random.choice(DEVICES) if fraudish else f"d{random.randint(1,10)}"
    ip = random.choice(IPS) if fraudish else f"192.168.1.{random.randint(2,254)}"

    return {
        "txn_id": txn_id,
        "user_id": user_id,
        "amount": round(amount, 2),
        "currency": "INR",
        "merchant_id": random.choice(MERCHANTS),
        "country": country,
        "device_id": device_id,
        "ip": ip,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def main():
    i = 0
    while True:
        evt = synth_txn(i)
        payload = json.dumps(evt, separators=(",", ":"), sort_keys=True).encode("utf-8")
        sig = hmac.new(EVENT_SECRET, payload, hashlib.sha256).hexdigest().encode("utf-8")

        producer.send(
            TXN_TOPIC,
            value=evt,
            headers=[
                ("x-sig", sig),
                ("x-sig-alg", b"hmac-sha256"),
            ],
        )

        producer.flush()
        print("sent:", evt)
        i += 1
        time.sleep(0.4)


if __name__ == "__main__":
    main()
