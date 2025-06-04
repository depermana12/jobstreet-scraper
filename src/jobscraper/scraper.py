import logging
import time
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    TimeoutException,
    NoSuchElementException,
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

    def _find_element(self, by, value):
        try:
            return WebDriverWait(self.driver, self.long_wait).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            self.logger.error(f"Error finding element {value}: not found")
            raise NoSuchElementException(f"Element not found: {value}")

    def _login(self):
        try:
            sign_in = self._find_element(
                By.CSS_SELECTOR, "a[data-automation='sign in']"
            )
            self._click_element(sign_in)
            self.logger.info("Clicked on Sign In button")
            email_input = self._find_element(By.ID, "emailAddress")
            email_input.send_keys(self.email)
            time.sleep(0.3)
            email_input.send_keys(Keys.ENTER)
            return self._otp()
        except NoSuchElementException as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def _otp(self):
        try:
            otp = input("Enter the OTP sent to your email: ").strip()
            otp_input = self._find_element(
                By.CSS_SELECTOR, "input[aria-label='verification input']"
            )
            otp_input.click()
            for digit in otp:
                otp_input.send_keys(digit)
                time.sleep(0.2)
                # no otp error checking
            self._find_element(By.ID, "SearchBar")
            return True
        except NoSuchElementException as e:
            self.logger.error(f"OTP input failed: {e}")
            return False

    def _job_keyword(self, keyword="linux", location="Jakarta Raya"):
        try:
            keyword_input = self._find_element(By.ID, "keywords-input")
            keyword_input.click()
            keyword_input.clear()
            keyword_input.send_keys(keyword)
            time.sleep(0.2)
            location_input = self._find_element(By.ID, "SearchBar__Where")
            location_input.click()
            location_input.clear()
            location_input.send_keys(location)
            location_input.send_keys(Keys.ENTER)
            time.sleep(2)  # wait for search results to load
            self.logger.info(
                f"Searching for jobs with keyword: {keyword} in {location}"
            )
            job_found_counts = self._find_element(By.ID, "SearchSummary")

            # select sort by date
            job_sort_by = WebDriverWait(self.driver, self.long_wait).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "span[data-automation='active-sortBy']")
                )
            )
            job_sort_by.click()
            sort_by_tanggal = self._find_element(
                By.CSS_SELECTOR, "a[data-automation='sortby-1']"
            )
            time.sleep(0.2)
            self._click_element(sort_by_tanggal)
            self.logger.info(
                f"Sorting jobs by: {job_sort_by.text} - {sort_by_tanggal.text}"
            )

            self.logger.info(f"Jobs found: {job_found_counts.text}")
            job_count_text = job_found_counts.text.split()[0]
            print(f"Total jobs found: {job_count_text}")
            return int(job_count_text)
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

    def scrape_jobs(self):
        try:
            self.driver.get(self.url)
            time.sleep(2)  # wait for page to load
            if not self._login():
                self.logger.error("Login failed, cannot scrape jobs")
                return

            job_count = self._job_keyword()
            self.logger.info(f"Total jobs found: {job_count}")
            self._find_job_cards()
        except Exception as e:
            self.logger.error(f"Error during job scraping: {e}")
            return

    def close(self):
        self.logger.info("Closing the driver")
        self.driver.quit()
