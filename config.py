import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'shoppulse.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "+919999999999")
    EXPORT_DIR = BASE_DIR / "exports"
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    DATA_DIR = BASE_DIR / "data"
    BACKUP_DIR = Path(os.getenv("BACKUP_DIR", BASE_DIR / "data" / "backups"))
    PREDICTION_DB_PATH = Path(
        os.getenv("PREDICTION_DB_PATH", BASE_DIR / "data" / "prediction_analytics.db")
    )
    MODEL_DIR = Path(os.getenv("MODEL_DIR", BASE_DIR / "models"))
    MODEL_RUNS_DIR = Path(os.getenv("MODEL_RUNS_DIR", BASE_DIR / "models" / "runs"))
    MODEL_LATEST_DIR = Path(os.getenv("MODEL_LATEST_DIR", BASE_DIR / "models" / "latest"))
    LEGACY_MODEL_PATH = BASE_DIR / "models" / "category_random_forest_model.joblib"
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PREDICTION_QUEUE = os.getenv("REDIS_PREDICTION_QUEUE", "shoppulse:prediction_jobs")
    GITHUB_REPO = os.getenv("GITHUB_REPO", "")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
