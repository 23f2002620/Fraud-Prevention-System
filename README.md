# Real-time Fraud Prevention System

A secure, end-to-end real-time fraud detection prototype for digital financial transactions:
Kafka → Flink real-time features → FastAPI scoring + case management → Vue dashboard.
Includes: anomaly ML model (MLflow), JWT auth, rate limiting, audit logs, HMAC request signing, and Kafka event signatures.

## Tech Stack
- Streaming: Kafka, Apache Flink (Docker)
- Backend: FastAPI, SQLModel, PostgreSQL
- ML: scikit-learn IsolationForest + MLflow tracking & registry
- Frontend: Vue 3 + Vite (HTML/CSS)
- Security: JWT (OAuth2 password flow), SlowAPI rate limiting, audit logs, HMAC internal signing, Kafka message signing

## Architecture (High-level)
1. txn-generator produces synthetic transactions to Kafka topic: `transactions`
2. Flink job reads `transactions`, computes 60s window features, writes to `txn_features`
3. Backend consumes:
   - `txn_features` → caches latest per user
   - `transactions` → verifies Kafka signature → scores → writes cases to Postgres if high risk → produces `fraud_alerts`
4. Vue dashboard lists cases and lets analyst update status (OPEN / CONFIRMED_FRAUD / FALSE_POSITIVE)

## Security Controls Implemented
- JWT auth for analyst APIs (`/cases`) using FastAPI OAuth2 JWT pattern. (OWASP recommends robust API security controls.) 
- Rate limiting using SlowAPI.
- Audit logging for case actions (avoid logging secrets/PII).
- HMAC-signed internal endpoint `/internal/cases` with timestamp+nonce replay protection.
- Kafka event signatures in headers to detect tampered messages.

## Local Setup (One-command)
Prereqs: Docker Desktop + Maven + Python 3.11 (for training)

### 1) Start infra
docker compose up -d --build

### 2) Build + submit Flink job
cd flink-job
mvn -q -DskipTests package
JAR=$(ls -1 target/*shade*.jar | head -n 1)
docker cp "$JAR" flink-jobmanager:/tmp/fraud-flink-job.jar
docker exec -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 flink-jobmanager \
  flink run -c com.example.fraud.FraudFeaturesJob /tmp/fraud-flink-job.jar

Flink UI: http://localhost:8081

### 3) Train ML model + register in MLflow
MLflow UI: http://localhost:8080

python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
export MLFLOW_TRACKING_URI=http://localhost:8080
python -m backend.app.train

### 4) Run UI
Frontend: http://localhost:5173
Backend Swagger: http://localhost:8000/docs

## Demo Credentials (MVP)
Username: admin
Password: admin123

## Topics
- transactions
- txn_features
- fraud_alerts

## Screenshots to include in report
- Flink job running (Flink UI)
- MLflow experiment + registered model
- Vue dashboard showing incoming cases
- Swagger /docs showing secured endpoints
