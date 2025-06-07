from datetime import datetime, timedelta
import pytest
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from jobscraper.scraper import JobScraper


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
