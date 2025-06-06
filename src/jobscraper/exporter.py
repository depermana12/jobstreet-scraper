import csv
from datetime import datetime
import gzip
import logging
import os

logger = logging.getLogger(__name__.capitalize())

EXPORT_DIR = "exports"
MAIN_CSV = [
    "id",
    "job_title",
    "job_location",
    "job_classification",
    "job_type",
    "job_salary_range",
    "job_posted_date",
    "job_apply_link",
    "job_url",
    "company_name",
    "company_rating",
    "company_business_type",
    "company_employees_count",
    "company_benefits",
]

SECONDARY_CSV = [
    "job_id",
    "job_requirements",
]


def _get_timestamp_filename(prefix: str, extension: str) -> str:
    """Generate timestamped filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.{extension}"

    os.makedirs(EXPORT_DIR, exist_ok=True)
    return os.path.join(EXPORT_DIR, filename)


def export_to_csv(jobs_data, filename="jobstreet_jobs"):
    """Export jobs data to CSV file"""

    if not jobs_data:
        no_data_filename = _get_timestamp_filename(filename, "csv")
        with open(no_data_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["No Data. Check log for details."])
        return no_data_filename, None

    main_data = []
    secondary_data = []

    for job in jobs_data:
        main_record = {}
        for column in MAIN_CSV:
            if column == "company_benefits" and isinstance(job.get(column), list):
                main_record[column] = (
                    "; ".join(job[column]) if job.get(column) else None
                )
            else:
                main_record[column] = job.get(column)
        main_data.append(main_record)

        # create secondary record
        if job.get("job_requirements"):
            secondary_data.append(
                {"job_id": job.get("id"), "job_requirements": job["job_requirements"]}
            )
    main_filename = _get_timestamp_filename(f"{filename}_main", "csv")
    with open(main_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MAIN_CSV)
        writer.writeheader()
        writer.writerows(main_data)
    logger.info(f"Exported {len(main_data)} main jobs to {main_filename}")

    secondary_filename = None
    if secondary_data:
        secondary_filename = _get_timestamp_filename(f"{filename}_secondary", "csv")
        with gzip.open(secondary_filename, "wt", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SECONDARY_CSV)
            writer.writeheader()
            writer.writerows(secondary_data)
        logger.info(
            f"Exported {len(secondary_data)} secondary jobs to {secondary_filename}"
        )

    return main_filename, secondary_filename
