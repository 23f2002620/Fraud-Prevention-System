import threading
import time
from sqlmodel import Session, delete
from datetime import datetime, timezone

from app.db import engine
from app.models import UsedNonce

# Keep nonces for 10 minutes (should be > MAX_SKEW_SECONDS in Step 9)
TTL_SECONDS = 10 * 60

def start_nonce_cleanup(stop_event: threading.Event):
    while not stop_event.is_set():
        try:
            cutoff = int(time.time()) - TTL_SECONDS
            with Session(engine) as session:
                session.exec(delete(UsedNonce).where(UsedNonce.ts_epoch < cutoff))
                session.commit()
        except Exception as e:
            print("nonce cleanup error:", str(e))

        # run every minute
        stop_event.wait(60)
