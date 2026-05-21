"""Process Redis prediction jobs for product_view events."""
import argparse
import json
from datetime import datetime

from app import app
from models import PredictionJob, Product, db
from prediction_store import build_prediction_for_product_view, save_prediction_row
from queue_client import pop_prediction_job


def process_payload(payload, job_id=None):
    with app.app_context():
        audit = None
        if job_id:
            audit = PredictionJob.query.filter_by(job_id=job_id).first()
        try:
            if audit:
                audit.status = "processing"
                audit.attempts = (audit.attempts or 0) + 1
                audit.updated_at = datetime.utcnow()
                db.session.commit()

            product = Product.query.get(payload.get("product_id"))
            if not product:
                raise ValueError(f"Product {payload.get('product_id')} not found.")
            row = build_prediction_for_product_view(product, payload)
            save_prediction_row(row)

            if audit:
                audit.status = "completed"
                audit.completed_at = datetime.utcnow()
                audit.updated_at = datetime.utcnow()
                db.session.commit()
            return True
        except Exception as exc:
            if audit:
                audit.status = "failed"
                audit.error_message = str(exc)
                audit.updated_at = datetime.utcnow()
                db.session.commit()
            raise


def run_once(timeout=1):
    job = pop_prediction_job(timeout=timeout)
    if not job:
        print("No prediction job available.")
        return False
    payload = job.get("payload") or job
    job_id = job.get("job_id") or payload.get("job_id")
    process_payload(payload, job_id=job_id)
    print(f"Processed prediction job {job_id}.")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--timeout", type=int, default=1)
    args = parser.parse_args()

    if args.once:
        run_once(timeout=args.timeout)
        return

    while True:
        try:
            run_once(timeout=args.timeout)
        except Exception as exc:
            print(f"Prediction worker error: {exc}")


if __name__ == "__main__":
    main()
