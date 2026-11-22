import { test, expect } from '@playwright/test';

test.describe('Landing page', () => {
  test('loads hero, stats, and primary CTAs', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /Operational clarity for every hospital decision/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Enter dashboard/i }).first()).toBeVisible();
    await expect(page.getByText(/Dashboard modules/i).first()).toBeVisible();
    expect(errors).toEqual([]);
  });

  test('CTA navigates to dashboard', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.getByRole('link', { name: /Enter dashboard/i }).first().click();
    await expect(page).toHaveURL(/\/overview/);
  });

  test('module category tabs filter cards', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    const modules = page.locator('#modules');
    const financeTab = modules.getByRole('tab', { name: 'Finance' });
    await financeTab.scrollIntoViewIfNeeded();
    await financeTab.click();
    await expect(financeTab).toHaveAttribute('aria-selected', 'true');
    await expect(modules.getByRole('link', { name: /Finance/i }).first()).toBeVisible();
    await expect(modules.getByRole('link', { name: /Emergency/i })).toHaveCount(0);
  });
});
