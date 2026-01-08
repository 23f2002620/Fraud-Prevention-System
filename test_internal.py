import requests, json
from backend.app.internal_client import sign_headers

API = "http://localhost:8000"
API_KEY = "txn-generator"
SECRET = "GENERATOR_SHARED_SECRET_CHANGE_ME"

payload = {
  "txn_id": "signed-1",
  "user_id": "u99",
  "amount": 99999,
  "currency": "INR",
  "risk_score": 0.95,
  "reasons": ["hmac_demo"]
}

headers, body = sign_headers(API_KEY, SECRET, "POST", "/internal/cases", payload)
r = requests.post(f"{API}/internal/cases", headers=headers, data=body)
print(r.status_code, r.text)
