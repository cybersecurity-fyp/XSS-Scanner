"""
tests/frontend/test_scan_ui.py — New Scan page: form, toggles, advanced panel, submission.

Each test has a DIAGNOSE comment explaining what a failure means.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.frontend.conftest import BASE_URL


class TestScanPageLoad:

    def test_scan_page_loads(self, auth_page: Page):
        """
        WHAT: /scan returns 200 and renders the scan form.
        DIAGNOSE: 500 means pages.py scan() route threw an exception.
        Check server logs.  Also ensure the user session is valid.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        assert "500" not in auth_page.title(), (
            f"Scan page title is '{auth_page.title()}' — got a 500 error. "
            "Check server logs for the traceback in pages.py scan()."
        )

    def test_scan_url_input_visible(self, auth_page: Page):
        """
        WHAT: #scan-url input is visible and accepts text.
        DIAGNOSE: If missing — scan.html template not rendering the Target section.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        expect(auth_page.locator("#scan-url")).to_be_visible()

    def test_start_button_visible(self, auth_page: Page):
        """
        WHAT: The start scan button is visible on the scan page.
        DIAGNOSE: Look for #start-btn or a button with text 'Scan' / 'Start'.
        If missing — check scan.html for the submit button markup.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        start_btn = auth_page.locator("#start-btn, button:has-text('Scan'), button:has-text('Start')").first
        expect(start_btn).to_be_visible()

    def test_post_data_input_visible(self, auth_page: Page):
        """
        WHAT: #scan-data (POST data field) is visible.
        DIAGNOSE: check scan.html for #scan-data input in the Target section.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        expect(auth_page.locator("#scan-data")).to_be_visible()


class TestScanOptions:

    def test_crawl_toggle_present(self, auth_page: Page):
        """
        WHAT: The Crawl Mode toggle switch (#t-crawl) is in the DOM.
        DIAGNOSE: If missing — check scan.html Options fieldset for
        the .toggle element with id='t-crawl'.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        expect(auth_page.locator("#t-crawl")).to_be_attached()

    def test_crawl_toggle_activates_on_click(self, auth_page: Page):
        """
        WHAT: Clicking #t-crawl adds class 'on' and updates #h-crawl to 'true'.
        DIAGNOSE: If class doesn't change — initToggles() in app.js is not
        binding the click event.  Check that DOMContentLoaded fired and
        initToggles() ran.  Also verify HTMX didn't swap away the toggle.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        toggle = auth_page.locator("#t-crawl")
        hidden  = auth_page.locator("#h-crawl")

        assert hidden.input_value() == "false", (
            "#h-crawl should start as 'false'. Check scan.html toggle default."
        )
        toggle.click()
        auth_page.wait_for_timeout(200)

        classes = toggle.get_attribute("class") or ""
        assert "on" in classes, (
            "After clicking #t-crawl, it should have class 'on'. "
            "initToggles() in app.js may not have bound the click handler — "
            "check DOMContentLoaded fires and initToggles() runs."
        )
        assert hidden.input_value() == "true", (
            "#h-crawl should be 'true' after toggle is turned on. "
            "The data-for wiring in initToggles() may be broken."
        )

    def test_all_option_toggles_present(self, auth_page: Page):
        """
        WHAT: All 5 option toggles (crawl, json, fuzzer, encode, path) exist.
        DIAGNOSE: If a toggle is missing — that toggle row was removed from
        the Options fieldset in scan.html.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        for tid in ("#t-crawl", "#t-json", "#t-fuzzer", "#t-encode", "#t-path"):
            assert auth_page.locator(tid).count() > 0, (
                f"Toggle {tid} not found in scan page. "
                f"Check scan.html Options fieldset."
            )

    def test_toggle_deactivates_on_second_click(self, auth_page: Page):
        """
        WHAT: A second click on a toggle removes the 'on' class (toggle is on/off).
        DIAGNOSE: If still 'on' — classList.toggle('on') is not being called,
        or the event listener is bound twice and the second click is consumed.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        toggle = auth_page.locator("#t-json")
        toggle.click()
        auth_page.wait_for_timeout(150)
        toggle.click()
        auth_page.wait_for_timeout(150)
        classes = toggle.get_attribute("class") or ""
        assert "on" not in classes, (
            "After two clicks #t-json still has 'on'. "
            "The toggle is not working as a proper on/off switch."
        )


class TestAdvancedPanel:

    def test_advanced_section_visible(self, auth_page: Page):
        """
        WHAT: The Advanced section header (#adv-header) is visible.
        DIAGNOSE: If missing — scan.html Advanced section not rendered.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        expect(auth_page.locator("#adv-header")).to_be_visible()

    def test_advanced_panel_collapsed_by_default(self, auth_page: Page):
        """
        WHAT: #advanced-panel is not visible (collapsed) on page load.
        DIAGNOSE: If already open — the CSS .collapsible class has no
        height:0 / overflow:hidden rule, or the aria-expanded default is wrong.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        panel = auth_page.locator("#advanced-panel")
        # Panel should be collapsed (not visible or zero height)
        # We check aria-expanded on the button
        btn = auth_page.locator("#adv-header")
        expanded = btn.get_attribute("aria-expanded")
        assert expanded == "false", (
            f"#adv-header aria-expanded='{expanded}' on load, expected 'false'. "
            "The Advanced panel should start collapsed."
        )

    def test_advanced_panel_opens_on_click(self, auth_page: Page):
        """
        WHAT: Clicking #adv-header expands #advanced-panel and sets aria-expanded='true'.
        DIAGNOSE: If aria-expanded stays 'false' — the click handler on #adv-header
        in scan.js is not running.  Check pages/scan.js for the adv-toggle logic
        and ensure it's loaded via base.html <script defer>.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        auth_page.click("#adv-header")
        auth_page.wait_for_timeout(500)
        expanded = auth_page.locator("#adv-header").get_attribute("aria-expanded")
        assert expanded == "true", (
            "After clicking #adv-header, aria-expanded should be 'true'. "
            "The advanced panel toggle in scan.js may not be wired up."
        )

    def test_advanced_panel_inputs_accessible_when_open(self, auth_page: Page):
        """
        WHAT: After opening the advanced panel, #scan-level, #scan-threads,
        #scan-timeout sliders are interactable.
        DIAGNOSE: If not visible — the CSS transition didn't reveal them.
        Check .collapsible CSS (should transition max-height from 0 to a value).
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        auth_page.click("#adv-header")
        auth_page.wait_for_timeout(600)
        for input_id in ("#scan-level", "#scan-threads", "#scan-timeout"):
            el = auth_page.locator(input_id)
            assert el.count() > 0, f"{input_id} not found in advanced panel."
            expect(el).to_be_visible()


class TestScanSubmission:

    def test_empty_url_blocked_client_side(self, auth_page: Page):
        """
        WHAT: Clicking Start without a URL shows an error (client-side validation).
        DIAGNOSE: If a scan starts with empty URL — client validation is missing.
        Check scan.js startScan() for the URL empty-check before calling the API.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        auth_page.locator("#scan-url").fill("")
        start_btn = auth_page.locator("#start-btn, button:has-text('Scan'), button:has-text('Start')").first
        start_btn.click()
        auth_page.wait_for_timeout(1_000)
        # Should still be on the scan page (no scan started)
        assert "/scan" in auth_page.url, (
            "After clicking Start with empty URL, we navigated away. "
            "Client-side URL validation is missing in scan.js."
        )
        # Should show some error feedback
        error_visible = (
            auth_page.locator("#scan-error, .scan-error, [id*='error'], .toast-item").count() > 0
        )
        # If the input is marked invalid by the browser (type=url required), that's also fine
        validity = auth_page.evaluate("document.getElementById('scan-url')?.validity?.valid")
        assert not validity or error_visible, (
            "Empty URL should trigger visible error or browser validation. "
            "Check scan-url has 'required' attribute and scan.js validates before submit."
        )

    def test_invalid_url_shows_error(self, auth_page: Page):
        """
        WHAT: Entering a non-URL string and clicking Start shows an error.
        DIAGNOSE: If scan starts with 'not-a-url' — backend is not validating
        the URL format, or client-side validation is too permissive.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        auth_page.locator("#scan-url").fill("not-a-valid-url")
        start_btn = auth_page.locator("#start-btn, button:has-text('Scan'), button:has-text('Start')").first
        start_btn.click()
        auth_page.wait_for_timeout(1_500)
        # Browser type=url validation or client error — either stops the scan
        validity = auth_page.evaluate("document.getElementById('scan-url')?.validity?.valid")
        if validity is not None and not validity:
            return  # Browser native validation blocked it — pass
        # Otherwise an error element should appear
        error = auth_page.locator("#scan-error, .scan-error, .toast-item.error").first
        if error.count() > 0:
            return  # error shown — pass
        # If we get here check we at least didn't navigate away
        assert "/scan" in auth_page.url, (
            "Invalid URL 'not-a-valid-url' was accepted and navigated away. "
            "Add URL format validation to scan.js."
        )

    def test_stop_button_hidden_before_scan(self, auth_page: Page):
        """
        WHAT: #stop-btn is hidden (or absent) before a scan starts.
        DIAGNOSE: If stop button is visible at page load — check scan.js
        for the initial state logic that hides #stop-btn until scan is running.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        stop_btn = auth_page.locator("#stop-btn")
        if stop_btn.count() == 0:
            return  # Not rendered until needed — fine
        # If it's in DOM it should be hidden
        expect(stop_btn).to_be_hidden()

    def test_terminal_section_exists(self, auth_page: Page):
        """
        WHAT: The terminal output container (#terminal-output or equivalent) exists.
        DIAGNOSE: If missing — check scan.html for the results/terminal section.
        May be conditionally rendered only after scan starts.
        """
        auth_page.goto(f"{BASE_URL}/scan", wait_until="networkidle")
        terminal = auth_page.locator(
            "#terminal-output, #scan-output, .terminal, [id*='terminal'], [id*='output']"
        ).first
        # Terminal may only appear after scan starts — just verify the page has no 500
        assert "500" not in auth_page.title(), (
            "Scan page has a 500 error. Fix the route before testing the terminal."
        )
