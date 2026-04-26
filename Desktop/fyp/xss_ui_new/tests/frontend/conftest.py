"""
tests/frontend/conftest.py — Playwright fixtures for XSSniper frontend tests.

SETUP (run once before first test run):
    pip install pytest-playwright playwright
    playwright install chromium

RUN:
    pytest tests/frontend/ -v --headed          # see the browser
    pytest tests/frontend/ -v                   # headless (CI)
    pytest tests/frontend/test_auth_ui.py -v    # single file

The server must be running at BASE_URL before tests execute:
    uvicorn app.main:app --port 8080
"""

import pytest
from playwright.sync_api import Page, Browser, BrowserContext, sync_playwright

BASE_URL      = "http://localhost:8080"
TEST_USERNAME = "admin"
TEST_PASSWORD = "Admin@1234"


# ─── session-scoped login ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_session():
    """Single Playwright browser for the whole test session."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="session")
def logged_in_state(browser_session: Browser):
    """
    Log in once, capture storage_state (cookies + localStorage), and reuse it
    across every test.  If this fixture fails the whole suite will skip auth.

    DIAGNOSE: check BASE_URL is reachable, credentials are correct, and
    /login form has #login-input / #login-pass / #login-btn.
    """
    ctx  = browser_session.new_context()
    page = ctx.new_page()
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")

    page.fill("#login-input", TEST_USERNAME)
    page.fill("#login-pass", TEST_PASSWORD)
    page.click("#login-btn")

    # Wait for redirect to dashboard
    page.wait_for_url(f"{BASE_URL}/", timeout=20_000)

    state = ctx.storage_state()
    ctx.close()
    return state


@pytest.fixture
def auth_page(browser_session: Browser, logged_in_state: dict):
    """
    Authenticated Page fixture — each test gets a fresh context pre-loaded with
    the session state so no re-login is needed.
    """
    ctx  = browser_session.new_context(storage_state=logged_in_state)
    page = ctx.new_page()
    yield page
    ctx.close()


@pytest.fixture
def unauth_page(browser_session: Browser):
    """Unauthenticated Page fixture for testing login/register pages."""
    ctx  = browser_session.new_context()
    page = ctx.new_page()
    yield page
    ctx.close()
