from datetime import datetime, timedelta
import logging
import re
import time
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from jobscraper.configs import init_driver


class JobScraper:
    def __init__(
        self, url="https://id.jobstreet.com/", email="deddiapermana97@gmail.com"
    ):
        self.logger = logging.getLogger(__name__.capitalize())
        self.driver = init_driver()
        self.jobs_data = []
        self.email = email
        self.url = url
        self.long_wait = 10
        self.short_wait = 5

    def _click_element(self, element):
        try:
            self.driver.execute_script("arguments[0].click();", element)
            return True
        except (StaleElementReferenceException, ElementClickInterceptedException) as e:
            self.logger.warning(f"Element not clickable: {e}")
            return False

    def _find_element_wait(self, by, value):
        try:
            return WebDriverWait(self.driver, self.long_wait).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            self.logger.error(f"Timeout finding element: {value}")
            raise NoSuchElementException(f"Element not found: {value}")

    def _clean_text(self, text):
        if not text:
            return text

        # remove invisible characters (zero-width space, word joiner, etc.)
        cleaned = re.sub(r"[\u2060\u200B-\u200F\uFEFF]", "", text)
        cleaned = cleaned.replace("–", "-").replace("—", "-")
        return cleaned

    def _parse_posted_date(self, date_text: str):
        if not date_text or "Posted" not in date_text:
            return None

        text = date_text.replace("Posted", "").strip()
        if "30+" in text:
            return "30+ days ago"

        if match := re.search(r"\d+", text):
            days_ago = int(match[0])
            posted_date = datetime.now() - timedelta(days=days_ago)
            return posted_date.strftime("%d-%m-%Y")
        return None

    def _login(self):
        try:
            sign_in = self._find_element_wait(
                By.CSS_SELECTOR, "a[data-automation='sign in']"
            )
            self._click_element(sign_in)
            # enter email
            email_input = self._find_element_wait(By.ID, "emailAddress")
            email_input.send_keys(self.email)
            if email_input.get_attribute("value") == self.email:
                email_input.send_keys(Keys.ENTER)
            return self._otp()

        except NoSuchElementException as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def _otp(self):
        try:
            otp = input("Enter OTP: ").strip()
            if not otp.isdigit() or len(otp) != 6:
                self.logger.error("Invalid OTP format. Please enter a 6-digit code.")
                return False

            otp_input = self._find_element_wait(
                By.CSS_SELECTOR, "input[aria-label='verification input']"
            )
            otp_input.click()
            for digit in otp:
                otp_input.send_keys(digit)
                time.sleep(0.2)
            # wait until it redirects to home page
            self._find_element_wait(By.CSS_SELECTOR, "div[data-automation='homePage']")
            return True

        except NoSuchElementException as e:
            self.logger.error(f"OTP input failed: {e}")
            return False

    def _sort_search_by_date(self):
        try:
            sort_selectors = [
                "div[data-automation='trigger'][role='button']",
                "button[data-automation='sortedByButtonIconBcues']",
            ]

            sort_btn = None
            for selector in sort_selectors:
                try:
                    sort_btn = self._find_element_wait(By.CSS_SELECTOR, selector)
                    self.logger.info(f"Found sort button with: {selector}")
                    break
                except NoSuchElementException:
                    self.logger.warning(f"Sort button not found: {selector}")
                    continue

            self._click_element(sort_btn)
            WebDriverWait(self.driver, self.short_wait).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='menu']"))
            )
            sort_by_date = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "a[role='menuitem'][data-automation='sortby-1']",
                    )
                )
            )

            self._click_element(sort_by_date)

            if not self._wait_split_view_loaded():
                self.logger.error("wait failed, fallback to sleep")
                time.sleep(2)

            self.logger.info("Successfully sorted jobs by date")
        except Exception as e:
            self.logger.error(f"Failed to sort jobs by date: {e}")
            raise

    def _wait_split_view_loaded(self):
        try:
            WebDriverWait(self.driver, self.long_wait).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-automation='initialView']")
                )
            )

            WebDriverWait(self.driver, self.long_wait).until(
                EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, "[data-automation='initialView'] h3"),
                    "Pilih lowongan kerja",
                )
            )

            WebDriverWait(self.driver, self.long_wait).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "article[id^='jobcard-']")
                )
            )
            return True

        except TimeoutException as e:
            self.logger.error(f"wait split view failed: {e}")
            return False

    def _search_jobs_keyword(self, keyword="linux", location="Jakarta Raya"):
        try:
            # input keyword
            keyword_input = self._find_element_wait(By.ID, "keywords-input")
            keyword_input.click()
            keyword_input.send_keys(keyword)

            # input location
            location_input = self._find_element_wait(By.ID, "SearchBar__Where")
            location_input.click()
            location_input.send_keys(location)
            keyword_input.send_keys(Keys.ENTER)

            self.logger.info(
                f"Searching for jobs with keyword: {keyword} in {location}"
            )

            if not self._wait_split_view_loaded():
                self.logger.error("wait failed, fallback to sleep")
                time.sleep(2)

            # sort to date, alternative using search query
            self._sort_search_by_date()

            # find job counts
            job_count_selectors = [
                "span[data-automation='totalJobsCount']",
                "div[data-automation='totalJobsCountBcues']",
                "h1[data-automation='totaljobsMessage']",
                "h1[id='SearchSummary']",
            ]
            job_count_text = None
            for selector in job_count_selectors:
                try:
                    self.logger.info(f"Trying job count selector: {selector}")
                    job_count_element = self._find_element_wait(
                        By.CSS_SELECTOR, selector
                    )
                    job_count_text = job_count_element.text.strip()
                    self.logger.info(
                        f"Found job count with selector '{selector}': {job_count_text}"
                    )
                    break
                except NoSuchElementException:
                    self.logger.warning(f"Job count selector not found: {selector}")
                    continue

            if not job_count_text:
                self.logger.error("Job count not found with any selector")
                return 0

            # Parse job count
            try:
                if match := re.search(r"[\d,]+", job_count_text):
                    job_count_str = match.group().replace(",", "")
                    job_count = int(job_count_str)
                    self.logger.info(f"Total jobs found: {job_count}")
                    print(f"Total jobs found: {job_count}")
                    return job_count
                else:
                    self.logger.error(
                        f"No numbers found in job count text: {job_count_text}"
                    )
                    return 0
            except ValueError as e:
                self.logger.error(f"Error parsing job count '{job_count_text}': {e}")
                return 0

        except NoSuchElementException as e:
            self.logger.error(f"Job keyword search failed: {e}")
            return 0

    def _find_job_cards(self):
        try:
            job_cards = WebDriverWait(self.driver, self.long_wait).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "article[id^='jobcard-']")
                )
            )

            def get_idx(card):
                job_id = card.get_attribute("id")
                return int(job_id.split("-")[-1])

            self.logger.info(f"Found {len(job_cards)} job cards")
            return sorted(job_cards, key=get_idx)
        except TimeoutException as e:
            self.logger.error(f"Job cards not found: {e}")
            return []

    def _get_element_text(self, parent, selector, fallback=None):
        try:
            return parent.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            self.logger.warning(f"Element with selector '{selector}' not found")
            return fallback

    def _extract_company_profile(self, details):
        try:
            company_card = details.find_element(
                By.CSS_SELECTOR, "[data-automation='company-profile']"
            )
            company_profile = {
                "company_business_type": None,
                "company_employees_count": None,
                "company_benefits": None,
            }

            try:
                business_section_xpath = ".//div[1]/section[2]/div[1]"
                business_section = company_card.find_element(
                    By.XPATH, business_section_xpath
                )

                spans = business_section.find_elements(By.XPATH, "./span")

                if len(spans) >= 1:
                    business_type = self._clean_text(spans[0].text.strip())
                    if business_type:
                        company_profile["company_business_type"] = business_type
                        self.logger.info(f"Extracted business type: {business_type}")

                if len(spans) >= 2:
                    employee_count = self._clean_text(
                        spans[1].text.strip().split(" ")[0]
                    )
                    if employee_count:
                        company_profile["company_employees_count"] = employee_count
                        self.logger.info(f"Extracted employee count: {employee_count}")

            except NoSuchElementException:
                self.logger.info("Business type and employee count section not found")

            # benefits
            try:
                benefits_section_xpath = "./div[2]/section/div/div"
                benefits_container = company_card.find_element(
                    By.XPATH, benefits_section_xpath
                )
                benefit_spans = benefits_container.find_elements(By.XPATH, "./span")
                if benefit_spans:
                    benefits_list = []
                    for idx, span in enumerate(benefit_spans, start=1):
                        try:
                            benefit = span.find_element(By.XPATH, "./div")
                            benefit_text = self._clean_text(benefit.text.strip())
                            if benefit_text:
                                benefits_list.append(benefit_text)

                        except NoSuchElementException:
                            self.logger.warning(f"Benefit div not found in span {idx}")

                    if benefits_list:
                        company_profile["company_benefits"] = benefits_list
                        self.logger.info(
                            f"Successfully extracted {len(benefits_list)} benefit"
                        )

            except NoSuchElementException:
                self.logger.info("Benefits section not found")

            return company_profile

        except NoSuchElementException:
            self.logger.info("No company profile card found")
            return {
                "company_business_type": None,
                "company_employees_count": None,
                "company_benefits": None,
            }

    def _extract_job_details(self, card):
        if not self._click_element(card):
            return None

        details = self._find_element_wait(
            By.CSS_SELECTOR, "[data-automation='jobDetailsPage']"
        )
        if not details:
            self.logger.error("Job details not found after clicking the card")
            return None

        # selectors for job details
        selectors = {
            "title": "h1[data-automation='job-detail-title']",
            "company": "span[data-automation='advertiser-name']",
            "rating": "span[data-automation='company-review']",
            "location": "span[data-automation='job-detail-location']",
            "classification": "span[data-automation='job-detail-classifications']",
            "type": "span[data-automation='job-detail-work-type']",
            "salary": "span[data-automation='job-detail-salary']",
            "apply_link": "a[data-automation='job-detail-apply']",
            "description": "div[data-automation='jobAdDetails']",
        }

        try:
            # extract fixed fields
            job_data = {
                "job_title": self._get_element_text(details, selectors["title"]),
                "company_name": self._get_element_text(details, selectors["company"]),
                "job_location": self._get_element_text(details, selectors["location"]),
                "job_classification": self._get_element_text(
                    details, selectors["classification"]
                ),
                "job_type": self._get_element_text(details, selectors["type"]),
                "job_requirements": self._get_element_text(
                    details, selectors["description"]
                ),
            }

            # extract optional fields
            job_data["company_rating"] = self._get_element_text(
                details, selectors["rating"]
            )
            salary_text = self._get_element_text(details, selectors["salary"])
            if salary_text:
                job_data["job_salary_range"] = self._clean_text(
                    salary_text.replace("per month", "")
                )
            else:
                job_data["job_salary_range"] = None

            try:
                posted_elem = details.find_element(
                    By.XPATH, ".//span[contains(text(), 'Posted ')]"
                )
                job_data["job_posted_date"] = self._parse_posted_date(
                    self._clean_text(posted_elem.text.strip())
                )
            except NoSuchElementException:
                job_data["job_posted_date"] = None

            apply_link = details.find_element(
                By.CSS_SELECTOR, selectors["apply_link"]
            ).get_attribute("href")
            job_data["job_apply_link"] = apply_link
            job_data["job_url"] = apply_link.split("apply")[0] if apply_link else None

            company_profile = self._extract_company_profile(details)
            job_data.update(company_profile)

            return job_data

        except NoSuchElementException as e:
            self.logger.error(f"Failed to extract job details: {e}")
            return None

    def _next_page(self):
        try:
            current_url = self.driver.current_url
            next_button = self._find_element_wait(
                By.CSS_SELECTOR,
                f"a[aria-label='Selanjutnya']",
            )
            self._click_element(next_button)
            WebDriverWait(self.driver, self.short_wait).until(
                lambda d: d.current_url != current_url
            )
            self._find_element_wait(By.CSS_SELECTOR, "article[id^='jobcard-']")
            self.logger.info("Navigated to the next page")
            return True
        except (NoSuchElementException, ElementClickInterceptedException) as e:
            self.logger.error(f"Failed to navigate to next page: {e}")
            return False

    def scrape_jobs(self):
        try:
            start_scrape_time = time.time()
            self.driver.get(self.url)
            WebDriverWait(self.driver, self.long_wait).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a[data-automation='sign in']")
                )
            )

            if not self._login():
                self.logger.error("Login failed, cannot scrape jobs")
                raise Exception("Login failed")

            time.sleep(2)

            job_count = self._search_jobs_keyword(
                keyword="linux", location="Jakarta Raya"
            )
            if job_count == 0:
                self.logger.error(
                    "Job search failed or no jobs found, cannot scrape jobs"
                )
                raise Exception("Job search failed")

            self.logger.info(f"Found {job_count} total jobs to process")

            page_num = 0
            total_jobs_scraped = 0
            while True:
                page_num += 1
                job_cards = self._find_job_cards()
                for idx, card in enumerate(job_cards, start=1):
                    self.logger.info(
                        f"Processing job card {idx}/{len(job_cards)} on page {page_num}"
                    )
                    print(
                        f"Processing job card {idx}/{len(job_cards)} on page {page_num}"
                    )
                    job_start_time = time.time()
                    job_info = {
                        "id": len(self.jobs_data) + 1,
                        "job_platform": "JobStreet",
                    }
                    job_details = self._extract_job_details(card)
                    elapsed = time.time() - job_start_time
                    if job_details:
                        job_record = {**job_info, **job_details}
                        self.jobs_data.append(job_record)
                        total_jobs_scraped += 1
                        self.logger.info(
                            f"Job {job_details.get('job_title')} processed in {elapsed:.2f} seconds"
                        )

                print(f"Completed page {page_num}, total jobs: {total_jobs_scraped}")
                self.logger.info(
                    f"Completed page {page_num}, total jobs: {total_jobs_scraped}"
                )

                if not self._next_page():
                    self.logger.info("No more pages to scrape")
                    break

        except Exception as e:
            self.logger.error(f"Error during job scraping: {e}")
            raise
        finally:
            elapsed_time = time.time() - start_scrape_time
            print(
                f"Total jobs scraped: {len(self.jobs_data)}, took {elapsed_time:.2f}s"
            )
            self.logger.info(
                f"Total jobs scraped: {len(self.jobs_data)}, took {elapsed_time:.2f}s"
            )
            return self.jobs_data

    def close(self):
        self.logger.info("Closing the driver")
        self.driver.quit()
