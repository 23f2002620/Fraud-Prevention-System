from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str = "postgresql+psycopg://fraud:fraud@postgres:5432/frauddb"
    kafka_bootstrap_servers: str = "kafka:9092"
    jwt_secret_key: str = "CHANGE_ME_DEV_ONLY"
    admin_username: str = "admin"
    admin_password: str = "admin123"


    # Optional: later you can point this to an MLflow model uri
    # Examples: "models:/fraud_model/Production" or a local path like "./models/model"
    mlflow_model_uri: str | None = None


settings = Settings()
