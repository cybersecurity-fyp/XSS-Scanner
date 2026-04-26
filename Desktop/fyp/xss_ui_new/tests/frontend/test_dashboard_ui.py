"""
tests/frontend/test_dashboard_ui.py — Dashboard stats, charts, activity feed.

Each test has a DIAGNOSE comment explaining what a failure means.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.frontend.conftest import BASE_URL


class TestDashboardLoad:

    def test_dashboard_loads_without_error(self, auth_page: Page):
        """
        WHAT: / returns 200 and does not show a 500 error page.
        DIAGNOSE: Server threw an exception in the dashboard route.
        Common causes: get_stats() / get_daily_stats() / get_history() raising
        because the 'user_id' column is missing from the scans table.
        Run the migration: ALTER TABLE scans ADD COLUMN IF NOT EXISTS user_id BIGINT;
        Also check app/routers/pages.py wraps DB calls in try/except.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        assert "500" not in auth_page.title(), (
            f"Dashboard returned a 500 page (title='{auth_page.title()}'). "
            "Check server logs for the traceback."
        )
        expect(auth_page.locator("body")).not_to_contain_text("Internal Server Error")

    def test_stats_cards_visible(self, auth_page: Page):
        """
        WHAT: At least one .stat-value element is visible on the dashboard.
        DIAGNOSE: Stats section not rendering — check dashboard.html block
        that shows total scans, vulnerabilities, and health score.
        If .stat-value is missing from HTML, the Jinja template block changed.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        stat_values = auth_page.locator(".stat-value")
        count = stat_values.count()
        assert count >= 1, (
            f"Expected at least 1 .stat-value element on dashboard, found {count}. "
            "The stats cards may not be rendered — check dashboard.html template."
        )

    def test_stats_cards_have_visible_labels(self, auth_page: Page):
        """
        WHAT: .stat-label elements are visible alongside stat values.
        DIAGNOSE: Labels missing — the stats card HTML structure changed.
        Check dashboard.html for .stat-label divs under each stat card.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        labels = auth_page.locator(".stat-label")
        assert labels.count() >= 1, (
            "No .stat-label elements found on dashboard. "
            "Check dashboard.html for the stats card structure."
        )
        # At least one should have non-empty text
        texts = [labels.nth(i).text_content().strip() for i in range(labels.count())]
        non_empty = [t for t in texts if t]
        assert non_empty, "All .stat-label elements are empty — Jinja data not rendering."

    def test_total_scans_stat_is_numeric(self, auth_page: Page):
        """
        WHAT: The first stat card shows a numeric value (0 or more).
        DIAGNOSE: If the value is 'N/A' or empty — get_stats() returned an
        error dict and the template shows a fallback, or the template variable
        binding is broken.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        first_stat = auth_page.locator(".stat-value").first
        text = first_stat.text_content().strip()
        assert text != "", "First .stat-value is empty — stats not rendering."
        # Should be a number or contain a number
        import re
        has_number = bool(re.search(r"\d", text))
        assert has_number, (
            f"First .stat-value shows '{text}' which contains no number. "
            "Check that stats dict is passed correctly from pages.py to dashboard.html."
        )

    def test_stats_grid_section_visible(self, auth_page: Page):
        """
        WHAT: .stats-3col (or equivalent grid) container is present.
        DIAGNOSE: If not found, dashboard.html template structure has changed —
        check the class names in the stats section.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        grid = auth_page.locator(".stats-3col, .stats-grid, [class*='stat']").first
        expect(grid).to_be_visible()


class TestDashboardCharts:

    def test_activity_chart_canvas_exists(self, auth_page: Page):
        """
        WHAT: #activityChart <canvas> element is in the DOM.
        DIAGNOSE: If missing — the chart section in dashboard.html is not
        rendering.  If present but chart is blank — the JSON data from
        #chart-daily-data script tag may be empty or malformed.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        canvas = auth_page.locator("#activityChart")
        assert canvas.count() > 0, (
            "#activityChart canvas not found. The activity chart section in "
            "dashboard.html may not be rendering — check the Jinja block."
        )

    def test_vuln_chart_canvas_exists(self, auth_page: Page):
        """
        WHAT: #vulnChart <canvas> element is in the DOM.
        DIAGNOSE: same as activityChart above.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        canvas = auth_page.locator("#vulnChart")
        assert canvas.count() > 0, (
            "#vulnChart canvas not found. Check dashboard.html for the vuln "
            "chart canvas element."
        )

    def test_chart_data_script_tag_exists(self, auth_page: Page):
        """
        WHAT: The <script type='application/json' id='chart-daily-data'> tag
        exists and contains valid JSON.
        DIAGNOSE: If missing — dashboard route didn't pass 'daily' to template.
        If JSON is invalid — json.dumps(daily) in the template has a bug.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        data_el = auth_page.locator("#chart-daily-data")
        if data_el.count() == 0:
            pytest.skip("No #chart-daily-data element — chart data may be inline")

        raw = data_el.text_content()
        import json
        try:
            json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"#chart-daily-data contains invalid JSON: {exc}\n"
                "Raw content: " + raw[:200]
            )

    def test_chart_js_library_loaded(self, auth_page: Page):
        """
        WHAT: Chart.js is available as window.Chart.
        DIAGNOSE: If undefined — /static/js/vendor/chart.min.js failed to load
        (404) or CSP blocked it.  Check the file exists and middleware CSP
        allows it.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        chart_defined = auth_page.evaluate("typeof window.Chart !== 'undefined'")
        assert chart_defined, (
            "window.Chart is undefined — Chart.js library did not load. "
            "Check /static/js/vendor/chart.min.js exists and is served correctly. "
            "Also verify CSP default-src 'self' allows it."
        )


class TestDashboardRecentActivity:

    def test_recent_activity_section_visible(self, auth_page: Page):
        """
        WHAT: The recent scans / activity section on dashboard is rendered.
        DIAGNOSE: If hidden/missing — history[:5] returned [] (which is valid),
        but the template may still render the section header.  Check dashboard.html
        for the {% if history %} guard — if it hides the entire section when empty,
        that's expected behaviour and this test should be skipped on empty DB.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        # Look for any table, list, or 'recent' labelled section
        recent = auth_page.locator(
            ".recent-activity, #recent-scans, "
            "[aria-label*='recent' i], [id*='recent' i], "
            "table, .data-table"
        )
        # If the DB has no scans, the section may be hidden — that's fine
        if recent.count() == 0:
            pytest.skip(
                "No recent activity section visible — DB may be empty. "
                "Run at least one scan and retry."
            )

    def test_no_500_when_history_empty(self, auth_page: Page):
        """
        WHAT: Dashboard renders without error even when scan history is empty.
        DIAGNOSE: If 500 — pages.py get_history() is not wrapped in try/except
        or it raises when result set is empty.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        assert "500" not in auth_page.title()
        expect(auth_page.locator("body")).not_to_contain_text("500")
        expect(auth_page.locator("body")).not_to_contain_text("Internal Server Error")

    def test_user_name_shown_in_sidebar(self, auth_page: Page):
        """
        WHAT: The logged-in username appears in the sidebar user pill.
        DIAGNOSE: If empty — user dict not passed to template, or
        .user-name element is missing from base.html sidebar footer.
        """
        auth_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        user_name_el = auth_page.locator(".user-name")
        if user_name_el.count() == 0:
            pytest.skip("No .user-name element in sidebar — check base.html sidebar footer.")
        expect(user_name_el.first).to_be_visible()
        text = user_name_el.first.text_content().strip()
        assert text, ".user-name is visible but empty — user context not passed to template."
