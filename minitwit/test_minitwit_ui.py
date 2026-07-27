"""
    UI and End-to-End Tests for MiniTwit (FastAPI version)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Adapted from session_07/test_itu_minitwit_ui.py for our FastAPI + PostgreSQL app.
    Original used Selenium + MongoDB; adapted to use Selenium + SQLAlchemy.

    Session 07 Task 0: UI and end-to-end tests.

    Dependencies:
        pip install selenium pytest
        # geckodriver must be in PATH (installed in CI via apt)

    Run:
        pytest test_minitwit_ui.py -v
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")


def get_driver():
    """Create a headless Firefox driver."""
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    return webdriver.Firefox(options=firefox_options)


def register_user(driver, username, email, password):
    """Helper: register a user via the UI."""
    driver.get(f"{BASE_URL}/register")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.NAME, "username")))

    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "email").send_keys(email)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.NAME, "password2").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "flashes")))
    return driver.find_element(By.CLASS_NAME, "flashes").text


def test_public_timeline_visible():
    """
    UI test: the public timeline is visible without login.
    """
    driver = get_driver()
    try:
        driver.get(f"{BASE_URL}/public")
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h2")))
        assert "Public Timeline" in driver.page_source
    finally:
        driver.quit()


def test_register_user_via_gui():
    """
    UI test: registers a user via the UI and checks the success flash message.
    Adapted from session_07/test_itu_minitwit_ui.py for our FastAPI app.
    """
    driver = get_driver()
    try:
        msg = register_user(driver, "uitestuser", "uitest@example.com", "testpass123")
        assert "successfully registered" in msg.lower()
    finally:
        driver.quit()


def test_register_and_login_via_gui():
    """
    End-to-end test: registers a user via the UI, logs in, and checks
    that the private timeline is accessible.
    Adapted from session_07/test_itu_minitwit_ui.py for our FastAPI app.
    """
    driver = get_driver()
    try:
        # Register
        register_user(driver, "e2euser", "e2e@example.com", "testpass123")

        # Login
        driver.get(f"{BASE_URL}/login")
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.NAME, "username")))

        driver.find_element(By.NAME, "username").send_keys("e2euser")
        driver.find_element(By.NAME, "password").send_keys("testpass123")
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "flashes")))
        assert "logged in" in driver.page_source.lower()

        # Check private timeline accessible
        assert "my timeline" in driver.page_source.lower() or \
               "what's on your mind" in driver.page_source.lower()
    finally:
        driver.quit()
