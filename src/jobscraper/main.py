from jobscraper.scraper import JobScraper
from jobscraper.configs import init_logging
from jobscraper.exporter import export_to_csv, create_timestamped_file
import argparse


def cli():
    parser = argparse.ArgumentParser(description="Job Scraper CLI")
    parser.add_argument("-e", type=str, required=True, help="Login email for JobStreet")
    parser.add_argument("-k", type=str, required=True, help="Job search keyword")
    parser.add_argument("-l", type=str, required=True, help="Job search location")
    args = parser.parse_args()
    return args


def main():
    init_logging()
    args = cli()
    keywords = [k.strip() for k in args.k.split(",") if k.strip()]

    main_filename = create_timestamped_file("jobstreet_main", "csv")
    sec_filename = create_timestamped_file("jobstreet_sec", "csv.gz")
    header_written = False

    scraper = JobScraper(email=args.e)
    try:
        for batch in scraper.scrape_jobs(keywords=keywords, location=args.l):
            main_csv, secondary_csv = export_to_csv(
                batch,
                main_filename=main_filename,
                sec_filename=sec_filename,
                header_written=header_written,
            )
            header_written = True
            print(f"Batch exported to: {main_csv}")
            if secondary_csv:
                print(f"Secondary data exported to: {secondary_csv}")
            else:
                print("No secondary data to export.")
    except Exception as e:
        print(f"An error occurred: {e}")
        scraper.logger.error(f"An error occurred during scraping: {e}")

    finally:
        scraper.close()
        print("Browser closed.")


if __name__ == "__main__":
    main()
