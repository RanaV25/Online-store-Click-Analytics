"""Sync a selected model version into models/latest."""
import argparse
from pathlib import Path

from config import Config
from mlops_utils import copy_tree_contents


def sync_from_run(model_version=None, dry_run=False):
    runs_dir = Path(Config.MODEL_RUNS_DIR)
    if model_version:
        src = runs_dir / model_version
    else:
        candidates = sorted(runs_dir.glob("category_rf_*"), reverse=True)
        if not candidates:
            raise FileNotFoundError("No model run folders found.")
        src = candidates[0]

    if not src.exists():
        raise FileNotFoundError(f"Model run does not exist: {src}")

    dst = Path(Config.MODEL_LATEST_DIR)
    if dry_run:
        print(f"DRY RUN: would sync {src} -> {dst}")
        return {"source": str(src), "destination": str(dst), "dry_run": True}

    copy_tree_contents(src, dst)
    print(f"Synced latest model from {src} to {dst}")
    return {"source": str(src), "destination": str(dst), "dry_run": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-version")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(sync_from_run(args.model_version, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
