from jobscraper.scraper import JobScraper
from jobscraper.configs import init_logging
from jobscraper.exporter import export_to_csv


def main():
    init_logging()
    scraper = JobScraper()
    try:
        jobs_data = scraper.scrape_jobs()
        main_data, secondary_data = export_to_csv(jobs_data)
        print(f"Main data exported to: {main_data}")

        if secondary_data:
            print(f"Secondary data exported to: {secondary_data}")
        else:
            print("No secondary data to export.")
    except Exception as e:
        print(f"An error occurred: {e}")
        scraper.logger.error(f"An error occurred during scraping: {e}")

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
