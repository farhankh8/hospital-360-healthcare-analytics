import { expect, test } from '@playwright/test';

test.describe('KPI Glossary', () => {
  test('search, category filter, table view and detail drawer', async ({ page }) => {
    await page.goto('/kpi-glossary');
    await expect(page.getByTestId('kpi-glossary-page')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('glossary-table')).toBeVisible({ timeout: 15000 });

    // search
    await page.getByTestId('glossary-search').fill('occupancy');
    await expect(page.getByTestId('glossary-row').first()).toBeVisible();

    // category filter
    await page.getByTestId('glossary-search').fill('');
    await page.getByTestId('glossary-category').selectOption({ label: 'Finance' });
    await expect(page.getByTestId('glossary-row').first()).toBeVisible();

    // open detail drawer
    await page.getByTestId('glossary-row').first().click();
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Business definition|Formula/i).first()).toBeVisible();
  });
});
