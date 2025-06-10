from datetime import datetime, timedelta
import pytest
from unittest.mock import MagicMock, patch, call
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    NoSuchElementException,
)
from jobscraper.scraper import JobScraper
from selenium.webdriver.common.keys import Keys


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    driver.current_url = "https://id.jobstreet.com/"
    return driver


@pytest.fixture
def scraper(mock_driver):
    with patch("jobscraper.scraper.init_driver", return_value=mock_driver):
        scraper = JobScraper(email="bismillah@email.com")
        scraper.driver = mock_driver
    return scraper


@pytest.mark.unit
class TestClickElement:
    def test_click_element_success(self, scraper):
        element = MagicMock()

        result = scraper._click_element(element)

        assert result is True
        scraper.driver.execute_script.assert_called_once_with(
            "arguments[0].click();", element
        )

    def test_click_element_stale_reference(self, scraper):
        element = MagicMock()
        scraper.driver.execute_script.side_effect = StaleElementReferenceException()

        result = scraper._click_element(element)

        assert result is False

    def test_click_element_intercepted(self, scraper):
        element = MagicMock()
        scraper.driver.execute_script.side_effect = ElementClickInterceptedException()

        result = scraper._click_element(element)

        assert result is False


@pytest.mark.unit
class TestTextCleaning:
    def test_clean_text_unicode_removal(self, scraper):
        dirty_text = "Hello\u2060World\u200b\ufeff"
        result = scraper._clean_text(dirty_text)
        assert result == "HelloWorld"

    def test_clean_text_dash_replacement(self, scraper):
        text_with_dashes = "Range – 5000 — 10000"
        result = scraper._clean_text(text_with_dashes)
        assert result == "Range - 5000 - 10000"

    def test_clean_text_empty_string(self, scraper):
        result = scraper._clean_text("")
        assert result == ""


@pytest.mark.unit
class TestDateParsing:
    def test_parse_posted_date_valid(self, scraper):
        with patch("jobscraper.scraper.datetime") as mock_datetime:
            mock_now = datetime(2023, 6, 15)
            mock_datetime.now.return_value = mock_now

            result = scraper._parse_posted_date("Posted 5 days ago")
            expected_date = (mock_now - timedelta(days=5)).strftime("%d-%m-%Y")
            assert result == expected_date

    def test_parse_posted_date_old(self, scraper):
        result = scraper._parse_posted_date("Posted 30+ days ago")
        assert result is None

    def test_parse_posted_date_today(self, scraper):
        with patch("jobscraper.scraper.datetime") as mock_datetime:
            mock_now = datetime(2023, 6, 15)
            mock_datetime.now.return_value = mock_now

            result = scraper._parse_posted_date("Posted 0 days ago")
            expected_date = mock_now.strftime("%d-%m-%Y")
            assert result == expected_date

    def test_parse_posted_date_empty(self, scraper):
        result = scraper._parse_posted_date("")
        assert result is None

    def test_parse_posted_date_no_posted_text(self, scraper):
        result = scraper._parse_posted_date("5 hours ago")
        assert result is None


@pytest.mark.unit
class TestLogin:
    def test_login_success(self, scraper):
        sign_in_element = MagicMock()
        email_input = MagicMock()
        email_input.get_attribute.return_value = "bismillah@email.com"
        otp_input = MagicMock()

        scraper._find_element_wait = MagicMock(
            side_effect=[sign_in_element, email_input, otp_input]
        )
        scraper._click_element = MagicMock(return_value=True)
        scraper._otp = MagicMock(return_value=True)

        result = scraper._login()

        assert result is True
        scraper._click_element.assert_called_once_with(sign_in_element)
        email_input.send_keys.assert_any_call("bismillah@email.com")

    def test_login_enter_key_not_submit(self, scraper):
        sign_in_element = MagicMock()
        email_input = MagicMock()
        email_input.get_attribute.return_value = scraper.email

        scraper._find_element_wait = MagicMock(
            side_effect=[sign_in_element, email_input, NoSuchElementException]
        )
        scraper._click_element = MagicMock(return_value=True)
        email_input.send_keys = MagicMock()
        scraper._otp = MagicMock()

        result = scraper._login()

        email_input.send_keys.assert_any_call(Keys.ENTER)
        assert result is False

    def test_login_element_not_found(self, scraper):
        scraper._find_element_wait = MagicMock(side_effect=NoSuchElementException())

        result = scraper._login()

        assert result is False

    def test_otp_success(self, scraper):
        otp_input = MagicMock()
        home_page = MagicMock()

        scraper._find_element_wait = MagicMock(
            side_effect=[otp_input, NoSuchElementException(), home_page]
        )

        with patch("builtins.input", return_value="123456"):
            with patch("time.sleep"):
                result = scraper._otp()

        assert result is True
        assert otp_input.send_keys.call_count == 6

    def test_otp_failure_retry(self, scraper):
        otp_input = MagicMock()
        otp_alert = MagicMock()
        otp_alert.text = "invalid code"

        scraper._find_element_wait = MagicMock(
            side_effect=[
                otp_input,
                otp_alert,
                otp_input,
                otp_alert,
                otp_input,
                otp_alert,
            ]
        )

        with patch("builtins.input", return_value="123456"):
            with patch("time.sleep"):
                result = scraper._otp()

        assert result is False
        assert otp_input.send_keys.call_count == 18


@pytest.mark.unit
class TestSearchJobsKeyword:
    def test_search_jobs_success(self, scraper):
        keyword_input = MagicMock()
        location_input = MagicMock()
        search_summary = MagicMock()
        job_count_element = MagicMock()
        job_count_element.text = "1,234 jobs found"
        search_summary.find_element.return_value = job_count_element

        scraper._find_element_wait = MagicMock(
            side_effect=[keyword_input, location_input, search_summary]
        )
        scraper._wait_split_view_loaded = MagicMock(return_value=True)
        scraper._sort_search_by_date = MagicMock()

        result = scraper._search_jobs_keyword("python", "Jakarta Raya")

        assert result == 1234
        keyword_input.send_keys.assert_has_calls([call("python"), call(Keys.ENTER)])
        location_input.send_keys.assert_any_call("Jakarta Raya")

    def test_search_jobs_element_not_found(self, scraper):
        scraper._find_element_wait = MagicMock(side_effect=NoSuchElementException())

        result = scraper._search_jobs_keyword("python", "Jakarta Raya")

        assert result == 0


@pytest.mark.unit
class TestFindJobCards:
    def test_find_job_cards_success(self, scraper):
        card1 = MagicMock()
        card1.get_attribute.return_value = "jobcard-1"
        card2 = MagicMock()
        card2.get_attribute.return_value = "jobcard-2"
        card3 = MagicMock()
        card3.get_attribute.return_value = "jobcard-3"
        job_cards = [card3, card2, card1]
        scraper._find_element_wait = MagicMock(return_value=job_cards)

        results = scraper._find_job_cards()

        assert len(results) == 3
        assert results[0].get_attribute("id") == "jobcard-1"
        assert results[1].get_attribute("id") == "jobcard-2"
        assert results[2].get_attribute("id") == "jobcard-3"

    def test_find_job_cards_missing(self, scraper):
        scraper._find_element_wait = MagicMock(side_effect=NoSuchElementException())

        result = scraper._find_job_cards()

        assert result == []


@pytest.mark.unit
class TestNextPage:
    def test_next_page_success(self, scraper):
        next_btn = MagicMock()
        next_btn.get_attribute.return_value = "false"
        scraper._find_element_wait = MagicMock(return_value=next_btn)
        scraper._click_element = MagicMock(return_value=True)
        scraper._wait_split_view_loaded = MagicMock(return_value=True)

        result = scraper._next_page()

        assert next_btn.get_attribute("aria-hidden") == "false"
        assert result is True
        scraper._click_element.assert_called_once_with(next_btn)

    def test_next_page_end(self, scraper):
        next_btn = MagicMock()
        next_btn.get_attribute.return_value = "true"
        scraper._find_element_wait = MagicMock(return_value=next_btn)

        result = scraper._next_page()

        assert result is False
        assert next_btn.get_attribute("aria-hidden") == "true"

    def test_next_page_missing(self, scraper):
        scraper._find_element_wait = MagicMock(side_effect=NoSuchElementException())

        result = scraper._next_page()

        assert result is False
        scraper._find_element_wait.assert_called_once()
