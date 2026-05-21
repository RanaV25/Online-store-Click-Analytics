"""Publish a model run folder to GitHub Releases.

This script supports dry-run validation locally. Actual publishing uses the
GitHub CLI (`gh`) when available and configured.
"""
import argparse
import subprocess
from pathlib import Path


REQUIRED_ASSETS = [
    "model.joblib",
    "features.json",
    "metrics.json",
    "training_summary.json",
    "model_card.md",
]


def validate_run_dir(run_dir):
    run_dir = Path(run_dir)
    missing = [name for name in REQUIRED_ASSETS if not (run_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required model artifacts: {missing}")
    return run_dir


def publish(run_dir, dry_run=True):
    run_dir = validate_run_dir(run_dir)
    tag = run_dir.name
    assets = [str(run_dir / name) for name in REQUIRED_ASSETS]
    cmd = ["gh", "release", "create", tag, *assets, "--title", tag, "--notes", f"Model release {tag}"]
    if dry_run:
        print("DRY RUN: would execute:")
        print(" ".join(cmd))
        return {"tag": tag, "assets": assets, "dry_run": True}
    subprocess.run(cmd, check=True)
    return {"tag": tag, "assets": assets, "dry_run": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(publish(args.run_dir, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
