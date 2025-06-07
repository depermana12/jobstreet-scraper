from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium import webdriver

import logging
import os


logger = logging.getLogger(__name__.capitalize())


def init_logging(log_dir="logs", log_file="jobstreet_scraper.log", log_console=False):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)
    handlers = [logging.FileHandler(log_path, encoding="utf-8")]

    if log_console:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S",
        handlers=handlers,
    )


def init_firefox_driver():
    try:
        options = FirefoxOptions()
        firefox_profile = FirefoxProfile()
        options.profile = firefox_profile

        options.set_preference("dom.webnotifications.enabled", False)
        options.set_preference("dom.push.enabled", False)
        options.set_preference("permissions.default.desktop-notification", 2)
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)

        driver = webdriver.Firefox(options=options)
        driver.maximize_window()
        return driver
    except Exception as e:
        logger.error(f"Error initializing Firefox driver: {e}")
        raise


def init_driver():
    try:
        driver = init_firefox_driver()
        logger.info(f"Web driver {driver.name} initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Error initializing web driver: {e}")
        raise
