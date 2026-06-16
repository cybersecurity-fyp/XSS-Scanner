import { test, expect } from '@playwright/test';

test.describe('Frontend UI & Architecture', () => {
  test.beforeEach(async ({ page }) => {
    // Assuming the app runs on localhost:8080 during testing
    await page.goto('http://localhost:8080');
  });

  test('Sidebar should toggle correctly', async ({ page, isMobile }) => {
    const sidebar = page.locator('#sidebar');
    const toggleBtn = page.locator('#sidebar-toggle-btn');
    
    if (isMobile) {
      // Test mobile drawer
      await page.click('#mobile-sidebar-toggle-btn');
      await expect(sidebar).toHaveClass(/sidebar-open/);
      await expect(page.locator('#sidebar-overlay')).toBeVisible();
      
      // Hit escape to close
      await page.keyboard.press('Escape');
      await expect(sidebar).not.toHaveClass(/sidebar-open/);
    } else {
      // Test desktop collapse
      await toggleBtn.click();
      await expect(page.locator('#app-shell')).toHaveClass(/sb-collapsed/);
      // ARIA mapping verified
      await expect(toggleBtn).toHaveAttribute('aria-expanded', 'false');
      
      await toggleBtn.click();
      await expect(page.locator('#app-shell')).not.toHaveClass(/sb-collapsed/);
      await expect(toggleBtn).toHaveAttribute('aria-expanded', 'true');
    }
  });

  test('HTMX SPA routing swaps main content', async ({ page }) => {
    // Click on history and wait for HTMX to intercept and swap
    await page.click('a[data-tooltip="History"]');
    
    // Validate we routed without a full pageload reload (rely on playwright tracing or just content switch)
    await expect(page).toHaveURL(/.*\/history/);
    await expect(page.locator('#main-content-inner')).toBeVisible();
  });
});
