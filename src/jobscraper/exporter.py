import csv
from datetime import datetime
import gzip
import logging
import os

logger = logging.getLogger(__name__.capitalize())

EXPORT_DIR = "exports"
MAIN_CSV = [
    "id",
    "search_keyword",
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


def create_timestamped_file(prefix: str, extension: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.{extension}"

    os.makedirs(EXPORT_DIR, exist_ok=True)
    return os.path.join(EXPORT_DIR, filename)


def export_to_csv(
    batch_jobs_data, main_filename, sec_filename, append=True, header_written=False
):

    if not batch_jobs_data:
        return main_filename, sec_filename

    main_data = []
    secondary_data = []

    for job in batch_jobs_data:
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
    write_header = not append or not header_written or not os.path.exists(main_filename)
    with open(main_filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MAIN_CSV)
        if write_header:
            writer.writeheader()
        writer.writerows(main_data)
    logger.info(f"Exported {len(main_data)} main jobs to {main_filename}")

    if secondary_data:
        write_header_sec = (
            not append or not header_written or not os.path.exists(sec_filename)
        )
        with gzip.open(sec_filename, "at", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SECONDARY_CSV)
            if write_header_sec:
                writer.writeheader()
            writer.writerows(secondary_data)
        logger.info(f"Exported {len(secondary_data)} secondary jobs to {sec_filename}")

    return main_filename, sec_filename
