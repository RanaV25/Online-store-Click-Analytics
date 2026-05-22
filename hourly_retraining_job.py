"""Hourly retraining job driven by active retraining triggers."""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app import app
from backup_database import create_db_backup
from config import Config
from models import RetrainingTrigger, TrainingRun, db


def active_triggers():
    now = datetime.utcnow()
    expired = RetrainingTrigger.query.filter(
        RetrainingTrigger.status == "active",
        RetrainingTrigger.active_until <= now,
    ).all()
    for trigger in expired:
        trigger.status = "expired"
        trigger.last_checked_at = now
    db.session.commit()
    return RetrainingTrigger.query.filter(
        RetrainingTrigger.status == "active",
        RetrainingTrigger.active_until > now,
    ).all()


def run_training_from_backup(backup_path, promote=True, dry_run=False):
    if dry_run:
        print(f"DRY RUN: would train from {backup_path}")
        return None
    cmd = [
        sys.executable,
        "train_category_models.py",
        "--db-path",
        str(backup_path),
    ]
    if promote:
        cmd.append("--promote")
    subprocess.run(cmd, check=True)
    latest_runs = sorted(Path(Config.MODEL_RUNS_DIR).glob("category_rf_*"), reverse=True)
    return latest_runs[0] if latest_runs else None


def run_once(dry_run=False, force=False):
    with app.app_context():
        triggers = active_triggers()
        if not triggers and not force:
            print("No active retraining triggers.")
            return False

        if dry_run:
            print(f"DRY RUN: {len(triggers)} active trigger(s); would backup and train.")
            return True

        backup = create_db_backup()
        source_db = backup.get("main_db_backup")
        if not source_db:
            raise RuntimeError("Main DB backup was not created.")

        run = TrainingRun(
            model_version=f"pending_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            model_type="random_forest",
            status="started",
            source_db_backup=source_db,
            created_by="hourly_retraining_job",
        )
        db.session.add(run)
        db.session.commit()

        try:
            run_dir = run_training_from_backup(source_db, promote=True, dry_run=False)
            run.model_version = run_dir.name if run_dir else run.model_version
            run.status = "completed"
            run.finished_at = datetime.utcnow()
            run.artifact_path = str(run_dir) if run_dir else None
            metrics_path = run_dir / "metrics.json" if run_dir else None
            if metrics_path and metrics_path.exists():
                run.metrics_json = metrics_path.read_text(encoding="utf-8")
            run.promoted_to_latest = True
            for trigger in triggers:
                trigger.last_checked_at = datetime.utcnow()
                trigger.last_training_run_id = run.id
            db.session.commit()
            print(f"Training completed: {run.model_version}")
            return True
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = datetime.utcnow()
            db.session.commit()
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run_once(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
