import hmac, hashlib, json, time, uuid
import requests

def sign_headers(api_key: str, secret: str, method: str, path: str, body_obj: dict):
    ts = str(int(time.time()))
    nonce = str(uuid.uuid4())
    body_bytes = json.dumps(body_obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body_hash = hashlib.sha256(body_bytes).hexdigest()

    msg = f"{method}\n{path}\n{ts}\n{nonce}\n{body_hash}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    return {
        "X-Api-Key": api_key,
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": sig,
        "Content-Type": "application/json",
    }, body_bytes
