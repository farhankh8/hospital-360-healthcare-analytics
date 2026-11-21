import { expect, test } from '@playwright/test';

test.describe('Pipeline page', () => {
  test('select run, compare two runs, open lineage drawer', async ({ page }) => {
    await page.goto('/pipeline');

    // Run history table should load and rows should be selectable.
    const runTable = page.locator('table').filter({ hasText: 'Run ID' }).first();
    await expect(runTable).toBeVisible({ timeout: 15000 });
    const rows = runTable.locator('tbody tr');
    await expect(rows.first()).toBeVisible();

    // Select first run -> run detail panel appears.
    await rows.nth(0).click();
    await expect(page.getByText(/Run detail:/i)).toBeVisible();
    await page.getByRole('button', { name: /Add to compare/i }).click();

    // Select second run and add to compare.
    if (await rows.nth(1).count()) {
      await rows.nth(1).click();
      await expect(page.getByText(/Run detail:/i)).toBeVisible();
      await page.getByRole('button', { name: /Add to compare/i }).click();
    }

    // Compare section should show deltas/table once two runs selected.
    await expect(page.getByText(/Compare runs/i).first()).toBeVisible();
    await expect(page.getByText(/Delta \(B-A\)/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/Duration seconds|Quarantined records/i).first()).toBeVisible();

    // Lineage drawer: click a lineage row.
    const lineageButton = page.locator('[data-testid="pipeline-lineage-search"]').locator('..').locator('button', { hasText: /./ }).first();
    // fallback: any lineage button in lineage card
    const lineageCardButton = page.getByRole('button', { name: /silver_|gold_|bronze_|dim_|fact_/i }).first();
    if (await lineageCardButton.count()) {
      await lineageCardButton.click();
    } else {
      await lineageButton.click();
    }
    await expect(page.getByRole('dialog', { name: /Lineage:/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Record details/i).first()).toBeVisible();
  });
});
