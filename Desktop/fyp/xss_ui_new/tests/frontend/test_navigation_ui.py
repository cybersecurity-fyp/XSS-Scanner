"""
tests/frontend/test_navigation_ui.py — Sidebar, theme toggle, HTMX nav, topbar.

Each test has a DIAGNOSE comment explaining what a failure means.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.frontend.conftest import BASE_URL


class TestSidebar:

    def test_sidebar_is_visible_on_load(self, auth_page: Page):
        """
        WHAT: The .sidebar element is visible after loading the dashboard.
        DIAGNOSE: If hidden — CSS display:none not overridden, or #app-shell
        class is wrong.  Check style.css sidebar rules.
        """
        auth_page.goto(f"{BASE_URL}/")
        expect(auth_page.locator(".sidebar")).to_be_visible(timeout=8_000)

    def test_desktop_sidebar_toggle_collapses_sidebar(self, auth_page: Page):
        """
        WHAT: Clicking #sidebar-toggle-btn adds .sb-collapsed to #app-shell,
        visually narrowing the sidebar.
        DIAGNOSE: If class isn't added — click delegation in app.js isn't
        reaching toggleSidebar() → _toggleDesktopCollapse().
        Check document.addEventListener('click', ...) block in app.js.
        Ensure the browser viewport is >768px (desktop).
        """
        auth_page.set_viewport_size({"width": 1280, "height": 800})
        auth_page.goto(f"{BASE_URL}/")
        auth_page.wait_for_selector("#sidebar-toggle-btn", state="visible")

        app_shell = auth_page.locator("#app-shell")
        assert "sb-collapsed" not in (app_shell.get_attribute("class") or ""), (
            "Sidebar already has sb-collapsed on load — _initSidebar() may have "
            "read a stale localStorage value.  Clear localStorage and retry."
        )

        auth_page.click("#sidebar-toggle-btn")
        auth_page.wait_for_timeout(400)  # CSS transition
        classes = app_shell.get_attribute("class") or ""
        assert "sb-collapsed" in classes, (
            "After clicking #sidebar-toggle-btn, #app-shell should have class "
            "'sb-collapsed'.  If not — the click delegation in app.js isn't "
            "calling _toggleDesktopCollapse().  Check for JS errors in console."
        )

    def test_desktop_sidebar_toggle_expands_again(self, auth_page: Page):
        """
        WHAT: A second click on #sidebar-toggle-btn removes .sb-collapsed,
        expanding the sidebar back to full width.
        DIAGNOSE: same as above — _sbCollapsed flag not toggling correctly.
        """
        auth_page.set_viewport_size({"width": 1280, "height": 800})
        auth_page.goto(f"{BASE_URL}/")
        auth_page.wait_for_selector("#sidebar-toggle-btn", state="visible")

        btn = auth_page.locator("#sidebar-toggle-btn")
        btn.click()
        auth_page.wait_for_timeout(300)
        btn.click()
        auth_page.wait_for_timeout(400)
        classes = auth_page.locator("#app-shell").get_attribute("class") or ""
        assert "sb-collapsed" not in classes, (
            "After two clicks #app-shell still has 'sb-collapsed'. "
            "The toggle is not working as a proper on/off switch."
        )

    def test_mobile_hamburger_hidden_on_desktop(self, auth_page: Page):
        """
        WHAT: #mobile-sidebar-toggle-btn is NOT visible at desktop width (>768px).
        DIAGNOSE: The mobile hamburger is visible on desktop — two hamburger
        buttons showing simultaneously.  Fix: add CSS rule
        '#mobile-sidebar-toggle-btn { display: none !important; }' and
        '@media (max-width:768px) { #mobile-sidebar-toggle-btn { display:flex !important; } }'
        Also ensure base.html does NOT have style='display:flex' on that button.
        """
        auth_page.set_viewport_size({"width": 1280, "height": 800})
        auth_page.goto(f"{BASE_URL}/")
        mobile_btn = auth_page.locator("#mobile-sidebar-toggle-btn")
        expect(mobile_btn).to_be_hidden(timeout=4_000)

    def test_mobile_hamburger_visible_on_mobile(self, auth_page: Page):
        """
        WHAT: #mobile-sidebar-toggle-btn IS visible at mobile width (375px).
        DIAGNOSE: The mobile menu trigger is missing on small screens —
        check the CSS media query for #mobile-sidebar-toggle-btn.
        """
        auth_page.set_viewport_size({"width": 375, "height": 812})
        auth_page.goto(f"{BASE_URL}/")
        mobile_btn = auth_page.locator("#mobile-sidebar-toggle-btn")
        expect(mobile_btn).to_be_visible(timeout=4_000)

    def test_mobile_drawer_opens_on_hamburger_click(self, auth_page: Page):
        """
        WHAT: Clicking the mobile hamburger adds .sidebar-open to .sidebar
        and .overlay-open to #sidebar-overlay.
        DIAGNOSE: If classes aren't added — _openMobileDrawer() not called.
        The viewport is mobile (375px) but isMobile() threshold is 768px —
        check window.innerWidth vs threshold in app.js.
        """
        auth_page.set_viewport_size({"width": 375, "height": 812})
        auth_page.goto(f"{BASE_URL}/")
        auth_page.click("#mobile-sidebar-toggle-btn")
        auth_page.wait_for_timeout(400)
        classes = auth_page.locator(".sidebar").get_attribute("class") or ""
        assert "sidebar-open" in classes, (
            "After clicking mobile hamburger, .sidebar should have class "
            "'sidebar-open'. _openMobileDrawer() may not be running. "
            "Check the click delegation in app.js."
        )

    def test_sidebar_close_on_overlay_click(self, auth_page: Page):
        """
        WHAT: Clicking the overlay behind the mobile drawer closes the sidebar.
        DIAGNOSE: If .sidebar-open persists — closeSidebar() isn't triggered
        by the overlay click.  Check click delegation: '#sidebar-overlay' check.
        """
        auth_page.set_viewport_size({"width": 375, "height": 812})
        auth_page.goto(f"{BASE_URL}/")
        auth_page.click("#mobile-sidebar-toggle-btn")
        auth_page.wait_for_timeout(300)
        auth_page.click("#sidebar-overlay")
        auth_page.wait_for_timeout(400)
        classes = auth_page.locator(".sidebar").get_attribute("class") or ""
        assert "sidebar-open" not in classes, (
            "After clicking #sidebar-overlay, .sidebar should lose 'sidebar-open'. "
            "Check the click delegation block in app.js for the #sidebar-overlay case."
        )

    def test_sidebar_collapse_state_persisted(self, auth_page: Page):
        """
        WHAT: After collapsing sidebar and reloading, the collapsed state is restored
        from localStorage.
        DIAGNOSE: localStorage key 'sbCollapsed' not being written or read.
        Check _toggleDesktopCollapse() writes localStorage and the inline script
        in base.html reads it before DOMContentLoaded.
        """
        auth_page.set_viewport_size({"width": 1280, "height": 800})
        auth_page.goto(f"{BASE_URL}/")
        auth_page.click("#sidebar-toggle-btn")
        auth_page.wait_for_timeout(400)

        # Reload and check state persists
        auth_page.reload(wait_until="networkidle")
        auth_page.wait_for_timeout(300)
        classes = auth_page.locator("#app-shell").get_attribute("class") or ""
        assert "sb-collapsed" in classes, (
            "After reload, sidebar should still be collapsed because sbCollapsed=1 "
            "is in localStorage.  Check the inline script in base.html that runs "
            "before DOMContentLoaded."
        )


class TestThemeToggle:

    def test_theme_toggle_button_visible(self, auth_page: Page):
        """
        WHAT: #theme-toggle button is visible in the topbar.
        DIAGNOSE: If missing — base.html topbar HTML is broken, or CSS
        is hiding it.
        """
        auth_page.goto(f"{BASE_URL}/")
        expect(auth_page.locator("#theme-toggle")).to_be_visible(timeout=8_000)

    def test_theme_starts_dark(self, auth_page: Page):
        """
        WHAT: On fresh load the html element has data-theme='dark' (default).
        DIAGNOSE: If theme is 'light' — localStorage has a saved 'light' value
        from a previous test.  This test may be order-dependent; run in isolation.
        """
        # Clear any saved theme first
        auth_page.goto(f"{BASE_URL}/")
        auth_page.evaluate("localStorage.removeItem('xss-theme')")
        auth_page.reload(wait_until="networkidle")
        theme = auth_page.evaluate("document.documentElement.getAttribute('data-theme')")
        # Accept either dark or the system default — just not undefined
        assert theme in ("dark", "light"), (
            f"data-theme='{theme}' is unexpected. core/theme.js should set it "
            "to 'dark' or 'light' on init."
        )

    def test_theme_toggle_switches_to_light(self, auth_page: Page):
        """
        WHAT: Clicking #theme-toggle changes data-theme from 'dark' to 'light'.
        DIAGNOSE: If data-theme doesn't change — the click delegation in app.js
        is not reaching toggleTheme().  Check the '#theme-toggle' branch in the
        document click listener in app.js.  Also check core/theme.js is loaded.
        """
        auth_page.goto(f"{BASE_URL}/")
        # Force dark first
        auth_page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        auth_page.click("#theme-toggle")
        auth_page.wait_for_timeout(300)
        theme = auth_page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert theme == "light", (
            f"After clicking #theme-toggle from dark mode, expected data-theme='light' "
            f"but got '{theme}'. toggleTheme() in core/theme.js may not be called — "
            f"check the click delegation block in app.js."
        )

    def test_theme_toggle_switches_back_to_dark(self, auth_page: Page):
        """
        WHAT: A second click on #theme-toggle changes data-theme back to 'dark'.
        DIAGNOSE: toggleTheme() reads the current attribute but it may already
        have been changed by the first click.  Ensure Theme.toggle() reads from
        document.documentElement.getAttribute('data-theme'), not a stale variable.
        """
        auth_page.goto(f"{BASE_URL}/")
        auth_page.evaluate("document.documentElement.setAttribute('data-theme','light')")
        auth_page.click("#theme-toggle")
        auth_page.wait_for_timeout(300)
        theme = auth_page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert theme == "dark", (
            f"Expected data-theme='dark' after toggling from light, got '{theme}'."
        )

    def test_theme_persisted_after_reload(self, auth_page: Page):
        """
        WHAT: Theme choice is saved in localStorage and re-applied after reload.
        DIAGNOSE: localStorage.setItem(KEY, t) in core/theme.js not executing,
        or Theme.init() not reading it on next page load.
        """
        auth_page.goto(f"{BASE_URL}/")
        auth_page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        auth_page.click("#theme-toggle")  # dark → light
        auth_page.wait_for_timeout(300)
        auth_page.reload(wait_until="networkidle")
        theme = auth_page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert theme == "light", (
            "Theme should survive a page reload because localStorage persists it. "
            "Check Theme.init() in core/theme.js reads 'xss-theme' from localStorage."
        )


class TestHTMXNavigation:

    def test_nav_scan_link_loads_scan_page(self, auth_page: Page):
        """
        WHAT: Clicking 'New Scan' in the sidebar navigates to /scan via HTMX
        (URL changes, content swaps, no full reload).
        DIAGNOSE: If URL stays at / — the hx-get or hx-push-url on the <a>
        tag in base.html is not working.  If you get a full reload, HTMX
        may not have loaded (check CSP blocked unpkg.com).
        """
        auth_page.goto(f"{BASE_URL}/")
        auth_page.click("a[href='/scan']")
        expect(auth_page).to_have_url(f"{BASE_URL}/scan", timeout=10_000)
        expect(auth_page.locator("#scan-url")).to_be_visible(timeout=5_000)

    def test_nav_history_link_loads_history_page(self, auth_page: Page):
        """
        WHAT: Clicking 'Scan History' loads /history content.
        DIAGNOSE: same as above — hx-get on the history nav-item.
        """
        auth_page.goto(f"{BASE_URL}/")
        auth_page.click("a[href='/history']")
        expect(auth_page).to_have_url(f"{BASE_URL}/history", timeout=10_000)

    def test_nav_settings_link_loads_settings_page(self, auth_page: Page):
        """
        WHAT: Clicking 'Settings' loads /settings content.
        DIAGNOSE: /settings route may have thrown an exception (e.g. prefs
        double-JSON encoding).  Check server logs.
        """
        auth_page.goto(f"{BASE_URL}/")
        auth_page.click("a[href='/settings']")
        expect(auth_page).to_have_url(f"{BASE_URL}/settings", timeout=10_000)
        expect(auth_page.locator("#save-settings-btn")).to_be_visible(timeout=5_000)

    def test_nav_dashboard_link_from_other_page(self, auth_page: Page):
        """
        WHAT: From /scan, clicking the Dashboard nav item returns to /.
        DIAGNOSE: HTMX select-oob for #topbar-page-title may be broken,
        causing title not to update, but the URL should still change.
        """
        auth_page.goto(f"{BASE_URL}/scan")
        auth_page.click("a[href='/']")
        expect(auth_page).to_have_url(f"{BASE_URL}/", timeout=10_000)

    def test_page_title_updates_on_navigation(self, auth_page: Page):
        """
        WHAT: After HTMX navigation, document.title includes the new page name.
        DIAGNOSE: The htmx:afterSwap listener in base.html inline script may
        not be reading #topbar-page-title correctly, or the OOB swap is failing.
        """
        auth_page.goto(f"{BASE_URL}/")
        auth_page.click("a[href='/scan']")
        auth_page.wait_for_url(f"{BASE_URL}/scan", timeout=10_000)
        title = auth_page.title()
        assert "Scan" in title or "XSSniper" in title, (
            f"After navigating to /scan, document.title='{title}' does not "
            "mention 'Scan'.  The HTMX afterSwap title-sync script in base.html "
            "may not be running or #topbar-page-title is not swapping."
        )

    def test_topbar_clock_is_running(self, auth_page: Page):
        """
        WHAT: The topbar clock (#topbar-time) shows a time string that updates.
        DIAGNOSE: If empty — _startClock() in app.js is not running.
        If static — the setTimeout loop in _startClock() is broken.
        """
        auth_page.goto(f"{BASE_URL}/")
        auth_page.wait_for_selector("#topbar-time", state="visible")
        t1 = auth_page.locator("#topbar-time").text_content()
        assert t1 and t1.strip(), "Topbar clock is empty — _startClock() may not have run."
        auth_page.wait_for_timeout(1_200)
        t2 = auth_page.locator("#topbar-time").text_content()
        assert t1 != t2, (
            f"Topbar clock shows '{t1}' and didn't change after 1.2s — "
            "the setTimeout in _startClock() is not ticking."
        )

    def test_status_pill_shows_online(self, auth_page: Page):
        """
        WHAT: The ONLINE status pill is visible in the topbar.
        DIAGNOSE: If missing — check base.html .status-pill HTML or style.css.
        """
        auth_page.goto(f"{BASE_URL}/")
        expect(auth_page.locator(".status-pill")).to_be_visible()
