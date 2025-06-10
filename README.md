# JobScraper - JobStreet Job Listings Scraper

A Python cli tool to scrape **job vacancies based on keywords and location** from JobStreet Indonesia. This tool handles authentication, search filtering, pagination, and exports comprehensive job data to csv.

### Extracted Data Fields

The scraped data separates into two csv files. First csv file contains job listings with detailed information, while the second csv file contains job requirements linked by job id.

please note that the second csv is compressed with gzip format, so you need to decompress it first before using it.

optional means that the field may not be available for all job.

- **Main CSV**: Contains detailed information

  - id
  - search keyword
  - job title
  - job location
  - job classification
  - job type
  - job salary range (optional)
  - job posted date
  - job apply link
  - job URL
  - company name
  - company rating (optional)
  - company business type (optional)
  - company employees size (optional)
  - company benefits (optional)

- **Secondary CSV**: Contains job requirements
  - job id
  - job requirements

---

## Requirements

- **Python**: 3.11 or higher
- **Firefox**: Latest version recommended
- **JobStreet Account**: Valid email credentials
- **Internet Connection**: Stable connection required

---

## Installation

1. **Install Poetry** (if not already installed)

   ```bash
   # Windows (PowerShell)
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

   # macOS/Linux
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Clone the repository**

   ```bash
   git clone https://github.com/depermana12/jobstreet-scraper.git
   cd jobstreet-scraper
   ```

3. **Install dependencies**
   ```bash
   poetry install
   ```

---

## Usage

you can put one or more keyword position separated by comma. It will take longer to scrape if you put more than one keyword.

```bash
# Basic usage

poetry run jobscraper -e youremail@example.com -k "python developer, data analyst, data scientist" -l "Jakarta Raya"
```

The scraper provides a simple CLI with three required arguments:

- `-e`: your jobstreet email
- `-k`: job search keyword (one or more keywords separated by commas)
- `-l`: job search location

### Example Workflow

1. **Start the scraper**
   ```bash
   poetry run jobscraper -e youremail@example.com -k "senior python" -l "Jakarta Raya"
   ```
2. **Firefox will open**
   ```
   The scraper will automatically navigate to the JobStreet login page with your email pre-filled.
   ```
3. **Complete OTP verification** when prompted

   ```
   Please enter the 6-digit OTP sent to your email in the **terminal**.
   ```

4. **Monitor progress**

   ```
   Total jobs found: 1,234
   Processing job card 1/20 on page 1
   Processing job card 2/20 on page 1
   ...
   ```

5. **Check output files**
   ```
   Main data exported to: jobstreet_jobs_20231215_143022.csv
   Secondary data exported to: company_profiles_20231215_143022.csv
   ```

## Important Notes

- The scraper requires you to manually enter the OTP sent to your email.
- The scraper uses Selenium to automate Firefox. Ensure you have the latest Firefox version
- Not supported on headless mode
- The scraper may take some time to complete depending on the number of jobs found.

## Disclaimer

- This tool is for personal use and learning purposes only
- Do not use for commercial scraping or violate JobStreet's terms of service
- The scraper may break if JobStreet changes its website structure
- Ensure your browser drivers are up to date for compatibility
- Use responsibly and respect rate limits
