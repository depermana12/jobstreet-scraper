import csv
from datetime import datetime
import logging
import os

EXPORT_DIR = "exports"

logger = logging.getLogger(__name__.capitalize())


def _get_timestamp_filename(prefix: str, extension: str) -> str:
    """Generate timestamped filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.{extension}"

    os.makedirs(EXPORT_DIR, exist_ok=True)
    return os.path.join(EXPORT_DIR, filename)


def export_to_csv(jobs_data, filename="jobstreet_jobs"):
    """Export jobs data to CSV file"""
    filename = _get_timestamp_filename(filename, "csv")

    if not jobs_data:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["No Data. Check log for details."])
        return filename

    fieldnames = set()
    for job in jobs_data:
        fieldnames.update(job.keys())
    fieldnames = sorted(list(fieldnames))

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs_data)

    logger.info(f"Exported {len(jobs_data)} jobs to {filename}")
    return filename
