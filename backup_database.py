"""Create timestamped SQLite backups for model training."""
import argparse
import shutil
from datetime import datetime
from pathlib import Path

from config import Config
from mlops_utils import write_json


def sqlite_path_from_url(database_url):
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// DATABASE_URL values are supported by this backup script.")
    return Path(database_url.replace(prefix, "", 1))


def create_db_backup(source_db_path=None, prediction_db_path=None, backup_dir=None):
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(backup_dir or Config.BACKUP_DIR) / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    source_db_path = Path(source_db_path or sqlite_path_from_url(Config.SQLALCHEMY_DATABASE_URI))
    prediction_db_path = Path(prediction_db_path or Config.PREDICTION_DB_PATH)

    outputs = {}
    if source_db_path.exists():
        dest = backup_dir / f"shoppulse_{stamp}.db"
        shutil.copy2(source_db_path, dest)
        outputs["main_db_backup"] = str(dest)
    if prediction_db_path.exists():
        dest = backup_dir / f"prediction_analytics_{stamp}.db"
        shutil.copy2(prediction_db_path, dest)
        outputs["prediction_db_backup"] = str(dest)

    metadata = {
        "created_at": datetime.utcnow().isoformat(),
        "source_db": str(source_db_path),
        "prediction_db": str(prediction_db_path),
        **outputs,
    }
    write_json(backup_dir / "backup_metadata.json", metadata)
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-db")
    parser.add_argument("--prediction-db")
    parser.add_argument("--backup-dir")
    args = parser.parse_args()
    metadata = create_db_backup(args.source_db, args.prediction_db, args.backup_dir)
    print(metadata)


if __name__ == "__main__":
    main()
