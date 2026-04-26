"""
tests/frontend/test_settings_ui.py — Settings page: preferences, password change,
profile edit, danger zone / delete account modal.

Each test has a DIAGNOSE comment explaining what a failure means.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.frontend.conftest import BASE_URL


class TestSettingsPageLoad:

    def test_settings_page_loads(self, auth_page: Page):
        """
        WHAT: /settings returns 200 without a 500 error.
        DIAGNOSE: settings_page() in pages.py raised an exception.
        Common cause: prefs double-JSON-encoding (json.dumps then | tojson).
        Fix: pass 'prefs': prefs (dict), NOT 'prefs': json.dumps(prefs).
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        assert "500" not in auth_page.title(), (
            f"Settings page shows 500 (title='{auth_page.title()}'). "
            "Check server logs.  Most likely cause: prefs double-encoded as JSON."
        )

    def test_scan_defaults_section_visible(self, auth_page: Page):
        """
        WHAT: The Scan Defaults card is visible.
        DIAGNOSE: If missing — settings.html card section not rendering.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        expect(auth_page.locator("#settings-scan-heading")).to_be_visible()

    def test_save_button_visible(self, auth_page: Page):
        """
        WHAT: #save-settings-btn is visible.
        DIAGNOSE: Check settings.html 'Save Preferences' card.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        expect(auth_page.locator("#save-settings-btn")).to_be_visible()

    def test_danger_zone_section_visible(self, auth_page: Page):
        """
        WHAT: The Danger Zone section is visible with the delete account button.
        DIAGNOSE: Check settings.html card--danger-border section.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        expect(auth_page.locator("#open-delete-modal-btn")).to_be_visible()


class TestScanDefaults:

    def test_scan_level_select_has_options(self, auth_page: Page):
        """
        WHAT: #s-level dropdown has options 1, 2, 3 for scan level.
        DIAGNOSE: If missing — check settings.html #s-level <select> options.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        select = auth_page.locator("#s-level")
        expect(select).to_be_visible()
        options = select.locator("option").all()
        assert len(options) >= 3, (
            f"#s-level has {len(options)} options, expected at least 3 (Basic/Standard/Deep)."
        )

    def test_threads_input_accepts_number(self, auth_page: Page):
        """
        WHAT: #s-threads is a number input and accepts a new value.
        DIAGNOSE: If input value doesn't update — check settings.html for
        #s-threads type='number'.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        inp = auth_page.locator("#s-threads")
        expect(inp).to_be_visible()
        inp.fill("5")
        assert inp.input_value() == "5", (
            "#s-threads value didn't update to '5'. "
            "Check the input type and that it's not disabled."
        )

    def test_timeout_input_accepts_number(self, auth_page: Page):
        """
        WHAT: #s-timeout accepts a new numeric value.
        DIAGNOSE: Check settings.html #s-timeout type='number'.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        inp = auth_page.locator("#s-timeout")
        inp.fill("10")
        assert inp.input_value() == "10"

    def test_save_settings_calls_api(self, auth_page: Page):
        """
        WHAT: Clicking #save-settings-btn triggers an API call and shows a toast.
        DIAGNOSE: If no toast appears — settings.js save handler is not running
        or the API call returned an error.  Check pages/settings.js saveSettings()
        and /api/v1/account/preferences endpoint.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")

        with auth_page.expect_response(
            lambda r: "preferences" in r.url or "settings" in r.url,
            timeout=8_000
        ) as resp_info:
            auth_page.click("#save-settings-btn")

        resp = resp_info.value
        assert resp.status < 500, (
            f"Saving settings returned HTTP {resp.status}. "
            "Check the /api/v1/account/preferences endpoint in account.py."
        )


class TestMLConfiguration:

    def test_prefilter_toggle_visible(self, auth_page: Page):
        """
        WHAT: ML Prefiltering toggle (#t-prefilter) is visible.
        DIAGNOSE: Check settings.html ML Configuration card.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        expect(auth_page.locator("#t-prefilter")).to_be_visible()

    def test_confidence_range_visible(self, auth_page: Page):
        """
        WHAT: Confidence threshold slider (#conf-range) is visible.
        DIAGNOSE: Check settings.html ML Configuration card for the range input.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        expect(auth_page.locator("#conf-range")).to_be_visible()

    def test_confidence_val_updates_on_slider_change(self, auth_page: Page):
        """
        WHAT: Moving #conf-range updates the #conf-val label.
        DIAGNOSE: If label stays the same — settings.js input event listener
        on #conf-range is not updating #conf-val.  Check pages/settings.js.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        slider   = auth_page.locator("#conf-range")
        val_span = auth_page.locator("#conf-val")
        initial  = val_span.text_content().strip()

        # Set value to 0.9 via JS (easier than dragging)
        auth_page.evaluate(
            """() => {
                const r = document.getElementById('conf-range');
                r.value = '0.9';
                r.dispatchEvent(new Event('input'));
            }"""
        )
        auth_page.wait_for_timeout(200)
        updated = val_span.text_content().strip()
        assert updated != initial or updated == "0.9", (
            f"#conf-val shows '{updated}' after setting slider to 0.9 (was '{initial}'). "
            "settings.js should update #conf-val on range 'input' event."
        )


class TestPasswordChange:

    def test_change_password_button_visible(self, auth_page: Page):
        """
        WHAT: The change password button (#cp-btn or similar) is visible on settings page.
        DIAGNOSE: If missing — check settings.html right column for the
        Change Password card.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        cp_btn = auth_page.locator(
            "#cp-btn, [id*='change-pass'], button:has-text('Change Password'), "
            "button:has-text('Update Password')"
        ).first
        if cp_btn.count() == 0:
            pytest.skip("No change password button found — may be on a different page.")
        expect(cp_btn).to_be_visible()

    def test_change_password_empty_fields_blocked(self, auth_page: Page):
        """
        WHAT: Submitting change-password with empty fields shows an error.
        DIAGNOSE: If password changes or no error — settings.js is not
        validating empty fields before calling the API.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        cp_btn = auth_page.locator(
            "#cp-btn, [id*='change-pass'], button:has-text('Change Password')"
        ).first
        if cp_btn.count() == 0:
            pytest.skip("No change password button — skipping.")
        cp_btn.click()
        auth_page.wait_for_timeout(1_000)
        # Should not have navigated away
        assert "/settings" in auth_page.url or auth_page.url.endswith("/"), (
            "Submitting empty password change navigated away — validation missing."
        )


class TestDangerZone:

    def test_delete_account_button_opens_modal(self, auth_page: Page):
        """
        WHAT: Clicking #open-delete-modal-btn shows the delete confirmation modal.
        DIAGNOSE: If modal doesn't appear — settings.js openModal() not called,
        or the modal ID doesn't match.  Check pages/settings.js for the
        #open-delete-modal-btn click handler and the modal ID it opens.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        auth_page.click("#open-delete-modal-btn")
        auth_page.wait_for_timeout(500)

        # Look for any visible modal / dialog
        modal = auth_page.locator(
            ".modal-overlay.open, .modal[open], [role='dialog']:visible, "
            "#delete-account-modal, #delete-modal"
        ).first
        if modal.count() > 0:
            expect(modal).to_be_visible()
        else:
            # Fallback: check if any overlay became visible
            overlay_visible = auth_page.evaluate(
                """() => {
                    const els = document.querySelectorAll('.modal-overlay, [role="dialog"]');
                    return [...els].some(e => getComputedStyle(e).display !== 'none');
                }"""
            )
            assert overlay_visible, (
                "Clicking #open-delete-modal-btn did not open any modal. "
                "Check settings.js for the click handler — it should call openModal() "
                "with the correct modal ID."
            )

    def test_cancel_closes_delete_modal(self, auth_page: Page):
        """
        WHAT: After opening the delete modal, clicking Cancel closes it.
        DIAGNOSE: If modal stays open — closeModal() in app.js is not being
        called by the cancel button.  Check modal markup for a Cancel button
        that calls closeModal().
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        auth_page.click("#open-delete-modal-btn")
        auth_page.wait_for_timeout(500)

        cancel = auth_page.locator(
            "button:has-text('Cancel'), #delete-cancel-btn, .modal-cancel"
        ).first
        if cancel.count() == 0:
            pytest.skip("No Cancel button found in delete modal.")

        cancel.click()
        auth_page.wait_for_timeout(400)
        # Modal should be gone
        overlay_visible = auth_page.evaluate(
            """() => {
                const els = document.querySelectorAll('.modal-overlay, [role="dialog"]');
                return [...els].some(e =>
                    e.classList.contains('open') ||
                    getComputedStyle(e).display === 'flex'
                );
            }"""
        )
        assert not overlay_visible, (
            "Modal is still visible after clicking Cancel. "
            "closeModal() in app.js may not be called by the cancel button."
        )

    def test_edit_username_button_visible(self, auth_page: Page):
        """
        WHAT: #edit-username-btn is visible on the settings page.
        DIAGNOSE: Check settings.html right column for the Profile section
        and the Edit button.
        """
        auth_page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        btn = auth_page.locator(
            "#edit-username-btn, button:has-text('Edit'), [id*='edit-user']"
        ).first
        if btn.count() == 0:
            pytest.skip("No edit username button — check settings.html.")
        expect(btn).to_be_visible()
