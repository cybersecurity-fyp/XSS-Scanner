"""
tests/frontend/test_auth_ui.py — Login / register / logout UI tests.

Each test has a DIAGNOSE comment explaining what a failure means and how to fix it.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.frontend.conftest import BASE_URL, TEST_USERNAME, TEST_PASSWORD


# ─── Login page ──────────────────────────────────────────────────────────────

class TestLoginPage:

    def test_login_page_loads(self, unauth_page: Page):
        """
        WHAT: /login returns 200 and renders the login form.
        DIAGNOSE: If this fails — server is not running at BASE_URL, or /login
        route threw an exception.  Check `uvicorn` output for errors.
        """
        unauth_page.goto(f"{BASE_URL}/login")
        expect(unauth_page).to_have_url(f"{BASE_URL}/login")
        expect(unauth_page.locator("#login-input")).to_be_visible()
        expect(unauth_page.locator("#login-pass")).to_be_visible()
        expect(unauth_page.locator("#login-btn")).to_be_visible()

    def test_login_page_title(self, unauth_page: Page):
        """
        WHAT: <title> tag contains 'XSSniper'.
        DIAGNOSE: base.html title block or Jinja template rendering broken.
        """
        unauth_page.goto(f"{BASE_URL}/login")
        expect(unauth_page).to_have_title(lambda t: "XSSniper" in t)

    def test_empty_form_shows_validation(self, unauth_page: Page):
        """
        WHAT: Clicking Login with empty fields shows a visible error message.
        DIAGNOSE: #login-error is not appearing — check doLogin() in
        frontend/static/js/pages/auth.js for the empty-field guard.
        """
        unauth_page.goto(f"{BASE_URL}/login")
        unauth_page.click("#login-btn")
        error = unauth_page.locator("#login-error")
        expect(error).to_be_visible(timeout=4_000)
        assert error.text_content().strip() != "", (
            "#login-error appeared but has no text — the error message is empty. "
            "Check doLogin() in auth.js to ensure it sets error text."
        )

    def test_wrong_password_shows_error(self, unauth_page: Page):
        """
        WHAT: Wrong credentials display an error, NOT a redirect.
        DIAGNOSE: If we get redirected, /login is not validating passwords.
        If #login-error stays hidden, auth.js isn't updating the error element.
        """
        unauth_page.goto(f"{BASE_URL}/login")
        unauth_page.fill("#login-input", TEST_USERNAME)
        unauth_page.fill("#login-pass", "definitely_wrong_password_123")
        unauth_page.click("#login-btn")

        # Must stay on login page
        expect(unauth_page).to_have_url(f"{BASE_URL}/login", timeout=5_000)
        expect(unauth_page.locator("#login-error")).to_be_visible(timeout=5_000)

    def test_successful_login_redirects_to_dashboard(self, unauth_page: Page):
        """
        WHAT: Valid credentials redirect to / (dashboard).
        DIAGNOSE: If we stay on /login — credentials are wrong, the DB is down,
        or the session cookie isn't being set.  Check TEST_USERNAME/TEST_PASSWORD
        in conftest.py and server logs.
        """
        unauth_page.goto(f"{BASE_URL}/login")
        unauth_page.fill("#login-input", TEST_USERNAME)
        unauth_page.fill("#login-pass", TEST_PASSWORD)
        unauth_page.click("#login-btn")
        expect(unauth_page).to_have_url(f"{BASE_URL}/", timeout=15_000)

    def test_password_toggle_shows_plain_text(self, unauth_page: Page):
        """
        WHAT: The eye icon toggles password field between type=password / type=text.
        DIAGNOSE: If type stays 'password' — togglePassword() in app.js couldn't
        find the eye button.  Verify [data-eye='login-pass'] or the onclick
        attribute on the toggle button in login.html.
        """
        unauth_page.goto(f"{BASE_URL}/login")
        pwd_input = unauth_page.locator("#login-pass")
        assert pwd_input.get_attribute("type") == "password", (
            "#login-pass should start as type='password'. "
            "If it's already 'text', the template default is wrong."
        )

        # Click the eye icon
        toggle_btn = unauth_page.locator("[data-eye='login-pass'], [onclick*=\"togglePassword('login-pass')\"]").first
        toggle_btn.click()
        assert pwd_input.get_attribute("type") == "text", (
            "After clicking the eye icon, #login-pass type should become 'text'. "
            "togglePassword() in app.js may not be finding the input."
        )

    def test_unauthenticated_redirect_to_login(self, unauth_page: Page):
        """
        WHAT: Visiting / without a session redirects to /login.
        DIAGNOSE: If this goes to dashboard without auth — get_session_user()
        in app/routers/pages.py is not enforcing the auth check.
        """
        unauth_page.goto(f"{BASE_URL}/")
        expect(unauth_page).to_have_url(lambda u: "/login" in u, timeout=8_000)

    def test_unauthenticated_scan_redirects(self, unauth_page: Page):
        """
        WHAT: /scan without session redirects to /login.
        DIAGNOSE: same as above — pages.py scan route missing auth guard.
        """
        unauth_page.goto(f"{BASE_URL}/scan")
        expect(unauth_page).to_have_url(lambda u: "/login" in u, timeout=8_000)

    def test_register_page_loads(self, unauth_page: Page):
        """
        WHAT: /register renders the registration form.
        DIAGNOSE: 404 means the /register route is missing in pages.py.
        """
        unauth_page.goto(f"{BASE_URL}/register")
        assert unauth_page.url.endswith("/register") or "/login" in unauth_page.url, (
            f"Unexpected URL after navigating to /register: {unauth_page.url}"
        )
        # If register is accessible, check the form
        if "/register" in unauth_page.url:
            expect(unauth_page.locator("form, [id*='register'], [id*='signup']")).to_be_visible()

    def test_forgot_password_page_loads(self, unauth_page: Page):
        """
        WHAT: /forgot-password renders without a 500 error.
        DIAGNOSE: Template rendering error in forgot_password.html or
        the route in pages.py threw an exception.
        """
        unauth_page.goto(f"{BASE_URL}/forgot-password")
        # Should not be a 500 page
        assert "500" not in unauth_page.title(), (
            "Got a 500 error on /forgot-password. Check the route in pages.py "
            "and ensure forgot_password.html renders without context errors."
        )


# ─── Logout ──────────────────────────────────────────────────────────────────

class TestLogout:

    def test_logout_button_redirects_to_login(self, auth_page: Page):
        """
        WHAT: Clicking the logout button (#logout-btn) calls /api/v1/auth/logout
        and redirects to /login.
        DIAGNOSE: If the page doesn't redirect — the click delegation in app.js
        is not reaching doLogout(), or the fetch to /api/v1/auth/logout failed.
        Check browser console for JS errors.  The #logout-btn must be inside
        the .sidebar which is rendered by base.html.
        """
        auth_page.goto(f"{BASE_URL}/")
        auth_page.wait_for_selector("#logout-btn", state="visible", timeout=8_000)
        auth_page.click("#logout-btn")
        expect(auth_page).to_have_url(lambda u: "/login" in u, timeout=10_000)

    def test_after_logout_cannot_access_dashboard(self, unauth_page: Page):
        """
        WHAT: After logging out the session cookie is cleared and / redirects to /login.
        DIAGNOSE: The /api/v1/auth/logout endpoint is not clearing the session cookie.
        Check app/routers/auth.py logout handler.
        """
        # Log in first
        unauth_page.goto(f"{BASE_URL}/login")
        unauth_page.fill("#login-input", TEST_USERNAME)
        unauth_page.fill("#login-pass", TEST_PASSWORD)
        unauth_page.click("#login-btn")
        unauth_page.wait_for_url(f"{BASE_URL}/", timeout=15_000)

        # Log out
        unauth_page.click("#logout-btn")
        unauth_page.wait_for_url(lambda u: "/login" in u, timeout=10_000)

        # Try dashboard again — must redirect back to login
        unauth_page.goto(f"{BASE_URL}/")
        expect(unauth_page).to_have_url(lambda u: "/login" in u, timeout=8_000)
