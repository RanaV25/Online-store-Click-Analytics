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
