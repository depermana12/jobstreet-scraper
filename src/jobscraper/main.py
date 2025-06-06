from jobscraper.scraper import JobScraper
from jobscraper.configs import init_logging
from jobscraper.exporter import export_to_csv


def main():
    init_logging()
    scraper = JobScraper()
    # try:
    jobs_data = scraper.scrape_jobs()
    main_data, secondary_data = export_to_csv(jobs_data)
    print(f"Main data exported to: {main_data}")
    print(f"Secondary data exported to: {secondary_data}")

    # finally:
    #     scraper.close()


if __name__ == "__main__":
    main()
