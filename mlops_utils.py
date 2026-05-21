"""Small MLOps helpers shared by admin, training, and scheduled jobs."""
import json
import shutil
from datetime import datetime
from pathlib import Path

from config import Config


def utc_version(prefix="category_rf"):
    return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def copy_tree_contents(src, dst):
    src = Path(src)
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def current_model_path():
    latest = Config.MODEL_LATEST_DIR / "model.joblib"
    if latest.exists():
        return latest
    return Config.LEGACY_MODEL_PATH
