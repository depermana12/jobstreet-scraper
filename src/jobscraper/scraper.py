from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from jobscraper.configs import init_driver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    TimeoutException,
    NoSuchElementException,
)

from datetime import datetime, timedelta
import logging
import re
import time


class JobScraper:
    def __init__(self, email: str):
        self.logger = logging.getLogger(__name__)
        self.driver = init_driver()
        self.jobs_data = []
        self.email = email
        self.url = "https://id.jobstreet.com/"
        self.long_wait = 10
        self.short_wait = 5

    def _click_element(self, element):
        try:
            self.driver.execute_script("arguments[0].click();", element)
            return True
        except (StaleElementReferenceException, ElementClickInterceptedException) as e:
            self.logger.warning(f"Element not clickable: {e}")
            return False

    def _find_element_wait(self, by, value, condition=None):
        if condition is None:
            condition = EC.presence_of_element_located((by, value))
        else:
            condition = condition((by, value))

        try:
            return WebDriverWait(self.driver, self.long_wait).until(condition)
        except TimeoutException:
            self.logger.error(f"Timeout finding element: {value}")
            raise NoSuchElementException(f"Element not found: {value}")

    def _clean_text(self, text):
        cleaned = re.sub(r"[\u2060\u200B-\u200F\uFEFF]", "", text)
        cleaned = cleaned.replace("–", "-").replace("—", "-")
        return cleaned

    def _parse_posted_date(self, date_text: str):
        if not date_text or "Posted" not in date_text:
            self.logger.warning(
                "Posted date text is empty or does not contain 'Posted'"
            )
            return None
        text = date_text.replace("Posted", "").strip()
        if "30+" in text:
            return None  # too old
        else:
            match = re.search(r"\d+", text)
            days_ago = int(match.group())

        posted_date = datetime.now() - timedelta(days=days_ago)
        return posted_date.strftime("%d-%m-%Y")

    def _login(self):
        try:
            sign_in = self._find_element_wait(
                By.CSS_SELECTOR, "a[data-automation='sign in']"
            )
            self._click_element(sign_in)
            email_input = self._find_element_wait(By.ID, "emailAddress")
            email_input.send_keys(self.email)
            for _ in range(3):
                if email_input.get_attribute("value") == self.email:
                    email_input.send_keys(Keys.ENTER)
                    break
                time.sleep(0.3)

            try:
                otp_input = self._find_element_wait(
                    By.CSS_SELECTOR, "input[aria-label='verification input']"
                )
            except NoSuchElementException:
                self.logger.error("OTP input not found after submitting email.")
                return False

            return self._otp()

        except NoSuchElementException as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def _otp(self):
        max_attempts = 3
        attempts = 0
        while attempts < max_attempts:
            otp = input("Enter OTP: ").strip()
            if not otp.isdigit() or len(otp) != 6:
                print("Invalid OTP, enter 6-digit numeric")
                continue

            try:
                otp_input = self._find_element_wait(
                    By.CSS_SELECTOR, "input[aria-label='verification input']"
                )
            except NoSuchElementException:
                self.logger.error("OTP input not found")
                return False

            otp_input.click()
            for digit in otp:
                otp_input.send_keys(digit)
                time.sleep(0.2)

            # wait for failed otp
            time.sleep(2)
            try:
                error_alert = self._find_element_wait(
                    By.CSS_SELECTOR, "[aria-live='polite']"
                )
                if "invalid code" in error_alert.text.strip().lower():
                    print("Invalid OTP, please try again.")
                    attempts += 1
                    continue
            except NoSuchElementException:
                pass

            # wait until it redirects to home page
            self._find_element_wait(By.CSS_SELECTOR, "div[data-automation='homePage']")
            return True

        self.logger.error("OTP failed 3 times. Aborting login")
        return False

    def _sort_search_by_date(self):
        try:
            sort_btn = self._find_element_wait(
                By.CSS_SELECTOR, "[data-automation='trigger'][role='button']"
            )

            self._click_element(sort_btn)
            self._find_element_wait(
                By.CSS_SELECTOR, "div[role='menu']", EC.visibility_of_element_located
            )
            sort_by_date = self._find_element_wait(
                By.CSS_SELECTOR,
                "a[role='menuitem'][data-automation='sortby-1']",
                EC.element_to_be_clickable,
            )
            self._click_element(sort_by_date)

            if not self._wait_split_view_loaded():
                self.logger.error("Failed to load split view after sorting")
                time.sleep(2)

            self.logger.info("Successfully sorted jobs by date")
        except NoSuchElementException as e:
            self.logger.error(f"Failed to sort jobs by date: {e}")
            raise

    def _wait_split_view_loaded(self):
        try:
            self._find_element_wait(By.CSS_SELECTOR, "[data-automation='initialView']")
            WebDriverWait(self.driver, self.long_wait).until(
                EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, "[data-automation='initialView'] h3"),
                    "Pilih lowongan kerja",
                )
            )
            self._find_element_wait(
                By.CSS_SELECTOR,
                "article[id^='jobcard-']",
                EC.presence_of_all_elements_located,
            )
            return True

        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"wait split view failed: {e}")
            return False

    def _search_jobs_keyword(self, keyword: str, location: str):
        try:
            # input keyword
            keyword_input = self._find_element_wait(By.ID, "keywords-input")
            keyword_input.click()
            keyword_input.clear()
            keyword_input.send_keys(keyword)

            # input location
            location_input = self._find_element_wait(By.ID, "SearchBar__Where")
            location_input.click()
            location_input.clear()
            location_input.send_keys(location)
            keyword_input.send_keys(Keys.ENTER)

            self.logger.info(
                f"Searching for jobs with keyword: {keyword} in {location}"
            )

            if not self._wait_split_view_loaded():
                self.logger.error("Failed to load split view after searching")
                time.sleep(2)

            # sort to date, alternative using search query
            self._sort_search_by_date()

            # find job counts
            search_summary = self._find_element_wait(
                By.ID,
                "aria-search-bar",
                EC.presence_of_element_located,
            )

            job_count_selectors = [
                "[data-automation='totalJobsCount']",
                "[data-automation='totalJobsCountBcues']",
            ]

            job_count_text = None
            for selector in job_count_selectors:
                try:
                    job_count_element = search_summary.find_element(
                        By.CSS_SELECTOR, selector
                    )
                    job_count_text = job_count_element.text.strip()
                    break
                except NoSuchElementException:
                    self.logger.warning(f"Job count selector not found: {selector}")
                    continue

            match = re.search(r"[\d,]+", job_count_text)
            job_count_str = match.group().replace(",", "")
            job_count = int(job_count_str)
            print(f"Total jobs found: {job_count}")
            return job_count

        except NoSuchElementException as e:
            self.logger.error(f"Job keyword search failed: {e}")
            return 0

    def _find_job_cards(self):
        try:
            job_cards = self._find_element_wait(
                By.CSS_SELECTOR,
                "article[id^='jobcard-']",
                EC.presence_of_all_elements_located,
            )

            def get_idx(card):
                job_id = card.get_attribute("id")
                return int(job_id.split("-")[-1])

            return sorted(job_cards, key=get_idx)
        except NoSuchElementException as e:
            self.logger.error(f"Job cards not found: {e}")
            return []

    def _get_element_text(self, parent, selector, fallback=None):
        try:
            return parent.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return fallback

    def _extract_company_profile(self, details):
        company_profile = {
            "company_business_type": None,
            "company_employees_count": None,
            "company_benefits": None,
        }
        try:
            company_card = details.find_element(
                By.CSS_SELECTOR, "[data-automation='company-profile']"
            )

            try:
                business_section = company_card.find_element(
                    By.XPATH, ".//div[1]/section[2]/div[1]"
                )
                spans = business_section.find_elements(By.XPATH, "./span")

                if len(spans) >= 1:
                    business_type = self._clean_text(spans[0].text.strip())
                    company_profile["company_business_type"] = business_type
                if len(spans) >= 2:
                    employee_count = self._clean_text(
                        spans[1].text.strip().split(" ")[0]
                    )
                    company_profile["company_employees_count"] = employee_count

            except NoSuchElementException:
                self.logger.info("Business type and size not specified")

            try:
                benefits_container = company_card.find_element(
                    By.XPATH, "./div[2]/section/div/div"
                )
                benefit_spans = benefits_container.find_elements(By.XPATH, "./span")

                benefits_list = []
                for span in benefit_spans:
                    try:
                        benefit_div = span.find_element(By.XPATH, "./div")
                        benefit_text = self._clean_text(benefit_div.text.strip())
                        if benefit_text:
                            benefits_list.append(benefit_text)
                    except NoSuchElementException:
                        continue

                company_profile["company_benefits"] = benefits_list

            except NoSuchElementException:
                self.logger.info("Benefits not specified")

            return company_profile

        except NoSuchElementException:
            self.logger.info("Company profile not specified")
            return company_profile

    def _extract_job_details(self, card):
        if not self._click_element(card):
            return None

        job_data = {
            "job_title": None,
            "company_name": None,
            "company_rating": None,
            "job_location": None,
            "job_classification": None,
            "job_type": None,
            "job_salary_range": None,
            "job_requirements": None,
            "job_posted_date": None,
            "job_apply_link": None,
            "job_url": None,
            "company_business_type": None,
            "company_employees_count": None,
            "company_benefits": None,
        }
        details = self._find_element_wait(
            By.CSS_SELECTOR, "[data-automation='jobDetailsPage']"
        )
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

        job_data["job_title"] = self._get_element_text(details, selectors["title"])
        job_data["company_name"] = self._get_element_text(details, selectors["company"])
        job_data["company_rating"] = self._get_element_text(
            details, selectors["rating"]
        )
        job_data["job_location"] = self._get_element_text(
            details, selectors["location"]
        )
        job_data["job_classification"] = self._get_element_text(
            details, selectors["classification"]
        )
        job_data["job_type"] = self._get_element_text(details, selectors["type"])
        job_data["job_requirements"] = self._get_element_text(
            details, selectors["description"]
        )

        salary_text = self._get_element_text(details, selectors["salary"])
        if salary_text:
            job_data["job_salary_range"] = self._clean_text(
                salary_text.replace("per month", "")
            )

        try:
            posted_elem = details.find_element(
                By.XPATH, ".//span[contains(text(), 'Posted ')]"
            )
            job_data["job_posted_date"] = self._parse_posted_date(
                self._clean_text(posted_elem.text.strip())
            )
        except NoSuchElementException:
            pass

        try:
            apply_link = details.find_element(
                By.CSS_SELECTOR, selectors["apply_link"]
            ).get_attribute("href")
            job_data["job_apply_link"] = apply_link
            job_data["job_url"] = apply_link.split("apply")[0] if apply_link else None
        except NoSuchElementException:
            pass

        company_profile = self._extract_company_profile(details)
        job_data.update(company_profile)

        return job_data

    def _next_page(self):
        try:
            next_btn = self._find_element_wait(
                By.CSS_SELECTOR,
                f"a[aria-label='Selanjutnya']",
            )
            next_attr = next_btn.get_attribute("aria-hidden")
            if next_attr == "true":
                self.logger.info("No more pages to navigate")
                return False

        except NoSuchElementException:
            self.logger.error("Failed to find next page button")
            return False

        if not self._click_element(next_btn):
            self.logger.error("Failed to click next page button")
            return False

        if not self._wait_split_view_loaded():
            self.logger.error("Next page did not load properly")
            return False

        self.logger.info("Navigated to the next page")
        return True

    def scrape_jobs(self, keywords: list[str], location: str):
        try:
            start_scrape_time = time.time()
            self.driver.get(self.url)
            self._find_element_wait(By.CSS_SELECTOR, "a[data-automation='sign in']")

            if not self._login():
                self.logger.error("Login failed, cannot scrape jobs")
                raise Exception("Login failed")

            time.sleep(2)
            total_keywords = len(keywords)
            total_jobs_scraped = 0
            for idx, keyword in enumerate(keywords, start=1):
                print(
                    f"Searching with keyword {idx}/{total_keywords}: {keyword} in {location}"
                )
                job_count = self._search_jobs_keyword(
                    keyword=keyword, location=location
                )
                if job_count == 0:
                    self.logger.warning(f"No jobs found for keyword: {keyword}")
                    continue

                page_num = 0
                while True:
                    page_num += 1
                    job_cards = self._find_job_cards()
                    for idx, card in enumerate(job_cards, start=1):
                        print(
                            f"Processing job card {idx}/{len(job_cards)} on page {page_num}"
                        )
                        job_start_time = time.time()
                        job_info = {
                            "id": len(self.jobs_data) + 1,
                            "search_keyword": keyword,
                        }
                        job_details = self._extract_job_details(card)
                        elapsed = time.time() - job_start_time
                        job_record = {**job_info, **job_details}
                        self.jobs_data.append(job_record)
                        total_jobs_scraped += 1
                        print(f"Job card {idx} processed in {elapsed:.2f}s")

                    print(
                        f"Completed page {page_num}, total jobs: {total_jobs_scraped}"
                    )
                    if not self._next_page():
                        print("No more pages to scrape.")
                        break

        except Exception as e:
            self.logger.error(f"Error during job scraping: {e}")
        finally:
            elapsed_time = time.time() - start_scrape_time
            print(
                f"Total jobs scraped: {len(self.jobs_data)}, took {elapsed_time:.2f}s"
            )

        return self.jobs_data

    def close(self):
        self.driver.quit()
