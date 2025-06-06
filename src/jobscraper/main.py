from jobscraper.scraper import JobScraper
from jobscraper.configs import init_logging
from jobscraper.exporter import export_to_csv


def main():
    init_logging()
    scraper = JobScraper()
    # try:
    jobs_data = scraper.scrape_jobs()
    export_to_csv(jobs_data)

    # finally:
    #     scraper.close()


if __name__ == "__main__":
    main()
