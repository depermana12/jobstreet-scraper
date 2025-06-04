from jobscraper.scraper import JobScraper
from jobscraper.configs import init_logging


def main():
    init_logging()
    scraper = JobScraper()
    try:
        scraper.scrape_jobs()
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
