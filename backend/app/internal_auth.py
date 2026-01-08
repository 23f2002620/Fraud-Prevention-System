import hmac
import hashlib
import time
from fastapi import Depends, Header, HTTPException, Request
from sqlmodel import Session, select

from app.core.config import settings
from app.db import get_session
from app.models import UsedNonce

# MVP: one internal client
# You can add more keys like {"generator": "...", "flink": "..."}
INTERNAL_KEYS = {
    "txn-generator": "GENERATOR_SHARED_SECRET_CHANGE_ME"
}

MAX_SKEW_SECONDS = 60  # accept +/- 60s


def _canonical(method: str, path: str, ts: str, nonce: str, body_bytes: bytes) -> bytes:
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    msg = f"{method}\n{path}\n{ts}\n{nonce}\n{body_hash}"
    return msg.encode("utf-8")


async def verify_internal_signature(
    request: Request,
    x_api_key: str = Header(..., alias="X-Api-Key"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    x_nonce: str = Header(..., alias="X-Nonce"),
    x_signature: str = Header(..., alias="X-Signature"),
    session: Session = Depends(get_session),
):
    secret = INTERNAL_KEYS.get(x_api_key)
    if not secret:
        raise HTTPException(status_code=401, detail="Unknown internal api key")

    try:
        ts_int = int(x_timestamp)
    except Exception:
        raise HTTPException(status_code=400, detail="Bad timestamp")

    now = int(time.time())
    if abs(now - ts_int) > MAX_SKEW_SECONDS:
        raise HTTPException(status_code=401, detail="Stale request")

    # Replay check: reject if nonce already used for this api key
    exists = session.exec(
        select(UsedNonce).where(UsedNonce.api_key == x_api_key).where(UsedNonce.nonce == x_nonce)
    ).first()
    if exists:
        raise HTTPException(status_code=401, detail="Replay detected")

    body = await request.body()
    msg = _canonical(request.method, request.url.path, x_timestamp, x_nonce, body)

    expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, x_signature):
        raise HTTPException(status_code=401, detail="Bad signature")

    # Store nonce (bounded by time window; you can also cleanup periodically)
    session.add(UsedNonce(api_key=x_api_key, nonce=x_nonce, ts_epoch=ts_int))
    session.commit()

    return x_api_key
