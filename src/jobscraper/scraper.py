import logging
import time
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from jobscraper.configs import init_driver


class JobScraper:
    def __init__(self, url="https://id.jobstreet.com/", email=None):
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
            return None

    def _login(self):
        sign_in = self._find_element(By.CSS_SELECTOR, "a[data-automation='sign in']")
        if sign_in:
            self._click_element(sign_in)
            self.logger.info("Clicked on Sign In button")
        email_input = self._find_element(By.ID, "emailAddress")
        if email_input:
            email_input.send_keys(self.email)
            time.sleep(0.3)
            email_input.send_keys(Keys.ENTER)
            return self._otp()

    def _otp(self):
        try:
            otp = input("Enter the OTP sent to your email: ").strip()
            otp_input = self._find_element(
                By.CSS_SELECTOR, "input[aria-label='verification input']"
            )
            if otp_input:
                otp_input.click()
                for digit in otp:
                    otp_input.send_keys(digit)
                    time.sleep(0.2)
                    # no otp error checking here, assuming user inputs correctly
                WebDriverWait(self.driver, self.long_wait).until(
                    EC.presence_of_element_located((By.ID, "SearchBar"))
                )
                return True
        except TimeoutException:
            self.logger.error("OTP input field not found or timed out")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during OTP input: {e}")
            return False
