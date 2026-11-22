import { expect, test } from '@playwright/test';

test.describe('Hospital Comparison and Profile', () => {
  test('comparison controls and navigate to profile tabs', async ({ page }) => {
    await page.goto('/hospitals');
    await expect(page.getByTestId('comparison-controls')).toBeVisible({ timeout: 15000 });
    await page.getByTestId('comparison-metric').selectOption('occupancy');
    await page.getByTestId('comparison-sort').selectOption('asc');

    // click first hospital row to open profile
    const firstRow = page.locator('table tbody tr').first();
    await expect(firstRow).toBeVisible({ timeout: 15000 });
    await firstRow.click();
    await expect(page).toHaveURL(/\/hospitals\/H/, { timeout: 15000 });
    await expect(page.getByTestId('hospital-profile-header')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('profile-tabs')).toBeVisible();
    await page.getByTestId('tab-departments').click();
    await expect(page.getByTestId('tab-departments')).toBeVisible();
  });
});
