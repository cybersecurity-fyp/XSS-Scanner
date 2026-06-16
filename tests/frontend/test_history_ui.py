"""
tests/frontend/test_history_ui.py — Scan History page: filters, search, bulk ops, actions.

Each test has a DIAGNOSE comment explaining what a failure means.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.frontend.conftest import BASE_URL


class TestHistoryPageLoad:

    def test_history_page_loads(self, auth_page: Page):
        """
        WHAT: /history returns 200 without a 500 error.
        DIAGNOSE: get_history() in pages.py raised an exception.
        Common cause: 'user_id' column missing from scans table.
        Run the migration and ensure pages.py wraps DB call in try/except.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        assert "500" not in auth_page.title(), (
            f"History page shows 500 (title='{auth_page.title()}'). "
            "Check server logs — likely get_history() raised an exception."
        )

    def test_history_heading_visible(self, auth_page: Page):
        """
        WHAT: The 'All Scans' heading (#history-heading) is visible.
        DIAGNOSE: If missing — the card section in history.html is not rendering.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        expect(auth_page.locator("#history-heading")).to_be_visible()

    def test_filter_selects_visible(self, auth_page: Page):
        """
        WHAT: Status and vulnerability filter dropdowns (#status-filter, #vuln-filter)
        are present and visible.
        DIAGNOSE: Check history.html .filter-bar section.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        expect(auth_page.locator("#status-filter")).to_be_visible()
        expect(auth_page.locator("#vuln-filter")).to_be_visible()

    def test_search_input_visible(self, auth_page: Page):
        """
        WHAT: The URL search input (#search-input) is visible.
        DIAGNOSE: Check history.html .search-wrap section.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        expect(auth_page.locator("#search-input")).to_be_visible()


class TestHistoryFilters:

    def test_status_filter_has_options(self, auth_page: Page):
        """
        WHAT: #status-filter has options for 'All Status', 'Completed', 'Failed'.
        DIAGNOSE: If options are missing — check history.html <select> markup.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        select = auth_page.locator("#status-filter")
        options = select.locator("option").all_text_contents()
        assert "Completed" in options, (
            f"#status-filter options: {options}. 'Completed' option missing — "
            "check history.html for the <option value='Completed'>."
        )
        assert "Failed" in options, (
            f"#status-filter options: {options}. 'Failed' option missing."
        )

    def test_vuln_filter_has_options(self, auth_page: Page):
        """
        WHAT: #vuln-filter has 'All Results', 'Vulnerable', 'Clean' options.
        DIAGNOSE: Check history.html vuln-filter <select> options.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        select = auth_page.locator("#vuln-filter")
        options = select.locator("option").all_inner_texts()
        assert any("Vulnerable" in o or "vuln" in o.lower() for o in options), (
            f"#vuln-filter has no Vulnerable option. Options: {options}"
        )

    def test_search_filters_table_rows(self, auth_page: Page):
        """
        WHAT: Typing in #search-input hides rows whose URL doesn't match.
        DIAGNOSE: If all rows remain visible — the search event listener in
        history.js is not running, or it's filtering on a different attribute.
        This test requires at least one scan row in history.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        table = auth_page.locator("#history-table")
        if table.count() == 0:
            pytest.skip("No history table — run at least one scan first.")

        rows = auth_page.locator("#history-table tbody tr")
        initial_count = rows.count()
        if initial_count == 0:
            pytest.skip("History table is empty — run at least one scan first.")

        # Type a search term that won't match any URL
        auth_page.fill("#search-input", "xyzABCnonexistent_term_12345")
        auth_page.wait_for_timeout(600)

        visible_rows = [
            r for r in range(rows.count())
            if rows.nth(r).is_visible()
        ]
        assert len(visible_rows) == 0 or len(visible_rows) < initial_count, (
            f"After searching for a non-existent term, all {initial_count} rows are still "
            "visible. The search filter in history.js may not be running — check that "
            "#search-input has an 'input' event listener in pages/history.js."
        )

    def test_clear_search_restores_rows(self, auth_page: Page):
        """
        WHAT: Clearing #search-input makes all rows visible again.
        DIAGNOSE: If rows stay hidden after clearing — the filter logic is not
        checking for empty string as 'show all'.  Check history.js filter function.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        table = auth_page.locator("#history-table")
        if table.count() == 0:
            pytest.skip("No history table.")

        rows = auth_page.locator("#history-table tbody tr")
        if rows.count() == 0:
            pytest.skip("History table is empty.")

        initial_visible = rows.count()
        auth_page.fill("#search-input", "xyznonexistent")
        auth_page.wait_for_timeout(400)
        auth_page.fill("#search-input", "")
        auth_page.wait_for_timeout(400)

        after_clear = sum(1 for i in range(rows.count()) if rows.nth(i).is_visible())
        assert after_clear == initial_visible, (
            f"After clearing search, {after_clear} rows visible (expected {initial_visible}). "
            "History filter in history.js should show all rows when search is empty."
        )


class TestHistoryBulkActions:

    def test_check_all_checkbox_exists(self, auth_page: Page):
        """
        WHAT: #check-all checkbox is in the table header.
        DIAGNOSE: If missing — check history.html table <thead> for #check-all.
        This only renders when history has entries ({% if history %} block).
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        if auth_page.locator("#history-table").count() == 0:
            pytest.skip("No history table — DB has no scans.")
        expect(auth_page.locator("#check-all")).to_be_visible()

    def test_check_all_selects_all_rows(self, auth_page: Page):
        """
        WHAT: Clicking #check-all checks all .scan-check checkboxes.
        DIAGNOSE: If not all checked — history.js #check-all click handler is
        not running or it's not targeting .scan-check checkboxes.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        if auth_page.locator("#history-table").count() == 0:
            pytest.skip("No history table.")
        rows = auth_page.locator(".scan-check")
        if rows.count() == 0:
            pytest.skip("No scan rows in history.")

        auth_page.click("#check-all")
        auth_page.wait_for_timeout(300)
        checked = sum(
            1 for i in range(rows.count())
            if rows.nth(i).is_checked()
        )
        assert checked == rows.count(), (
            f"After clicking #check-all, only {checked}/{rows.count()} rows are checked. "
            "The #check-all handler in history.js is not checking all .scan-check inputs."
        )

    def test_bulk_bar_appears_after_selection(self, auth_page: Page):
        """
        WHAT: #bulk-bar becomes visible after checking a row.
        DIAGNOSE: If bulk-bar stays hidden — history.js isn't watching checkbox
        changes to show the bulk action bar.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        if auth_page.locator("#history-table").count() == 0:
            pytest.skip("No history table.")
        first_check = auth_page.locator(".scan-check").first
        if first_check.count() == 0:
            pytest.skip("No scan rows.")
        first_check.check()
        auth_page.wait_for_timeout(400)
        bulk_bar = auth_page.locator("#bulk-bar")
        # Check if it became visible (some implementations use CSS class, some use display)
        is_visible = bulk_bar.is_visible()
        if not is_visible:
            # Also check via computed style
            display = auth_page.evaluate(
                "getComputedStyle(document.getElementById('bulk-bar')).display"
            )
            assert display != "none", (
                "#bulk-bar should appear when rows are selected. "
                "Check history.js checkbox event listener that shows #bulk-bar."
            )

    def test_bulk_count_shows_selected_count(self, auth_page: Page):
        """
        WHAT: #bulk-count shows '1 selected' after one row is checked.
        DIAGNOSE: If it shows '0 selected' — history.js is not updating the
        count when checkboxes change.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        if auth_page.locator(".scan-check").count() == 0:
            pytest.skip("No scan rows.")
        auth_page.locator(".scan-check").first.check()
        auth_page.wait_for_timeout(300)
        count_text = auth_page.locator("#bulk-count").text_content()
        assert "1" in count_text, (
            f"#bulk-count shows '{count_text}' after selecting 1 row. "
            "Expected '1' in text.  Check history.js selection counter logic."
        )

    def test_bulk_cancel_deselects_all(self, auth_page: Page):
        """
        WHAT: Clicking #bulk-cancel-btn unchecks all rows.
        DIAGNOSE: If rows stay checked — history.js #bulk-cancel-btn handler
        is not iterating .scan-check and unchecking them.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        if auth_page.locator(".scan-check").count() == 0:
            pytest.skip("No scan rows.")
        auth_page.click("#check-all")
        auth_page.wait_for_timeout(300)
        auth_page.click("#bulk-cancel-btn")
        auth_page.wait_for_timeout(300)
        checked = sum(
            1 for i in range(auth_page.locator(".scan-check").count())
            if auth_page.locator(".scan-check").nth(i).is_checked()
        )
        assert checked == 0, (
            f"After clicking #bulk-cancel-btn, {checked} rows are still checked. "
            "history.js cancel handler should uncheck all .scan-check inputs."
        )


class TestHistoryRowActions:

    def test_view_button_exists_in_rows(self, auth_page: Page):
        """
        WHAT: Each scan row has a 'View' button ([data-action='view']).
        DIAGNOSE: If missing — check history.html action-group buttons in the
        table row template.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        if auth_page.locator("#history-table tbody tr").count() == 0:
            pytest.skip("No scan rows in history.")
        expect(auth_page.locator("[data-action='view']").first).to_be_visible()

    def test_csv_export_link_exists(self, auth_page: Page):
        """
        WHAT: Each scan row has a CSV export link pointing to /api/v1/csv/{id}.
        DIAGNOSE: If missing — check history.html action-group for the
        <a href='/api/v1/csv/{{ scan.id }}'> element.
        """
        auth_page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        if auth_page.locator("#history-table tbody tr").count() == 0:
            pytest.skip("No scan rows in history.")
        csv_link = auth_page.locator("a[href*='/api/v1/csv/']").first
        expect(csv_link).to_be_visible()
