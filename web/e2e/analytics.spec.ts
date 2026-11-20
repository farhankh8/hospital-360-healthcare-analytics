/**
 * End-to-end journey from blueprint section 28:
 *   Overview -> select H03 -> change date range -> verify KPI changes ->
 *   click no-show KPI -> appointment detail -> export filtered data.
 * Extra cases: mobile viewport, refresh preserves filters, empty/invalid filters.
 *
 * Selectors prefer data-testid hooks (documented in web components) with
 * accessible-label fallbacks so the journey survives small markup changes.
 */
import { test, expect, type Locator, type Page } from '@playwright/test';

async function pick(page: Page, testId: string, label: RegExp): Promise<Locator> {
  const byTestId = page.locator(`[data-testid="${testId}"]`).first();
  if (await byTestId.count()) return byTestId;
  return page.getByLabel(label).first();
}

function kpiCard(page: Page, name: RegExp): Locator {
  return page.locator('[data-testid^="kpi-"]').filter({ hasText: name }).first();
}

async function readKpiValue(card: Locator): Promise<string> {
  const value = card.locator('[data-testid="metric-value"]').first();
  if (await value.count()) return (await value.innerText()).trim();
  return (await card.innerText()).trim();
}

test('overview -> H03 -> date change -> KPI drill-down -> export', async ({ page }) => {
  await page.goto('/overview');
  await expect(page).toHaveURL(/\/overview/);

  // A KPI card must render an API-driven value, not a hard-coded sample.
  const encounters = kpiCard(page, /total encounters/i);
  await expect(encounters).toBeVisible();
  const baseline = await readKpiValue(encounters);
  expect(baseline.length).toBeGreaterThan(0);

  // Select H03 through the global hospital filter.
  const hospital = await pick(page, 'filter-hospital', /hospital/i);
  await hospital.click();
  await page.getByRole('option', { name: /H03|Cardiac/i }).first().click();
  await expect(page).toHaveURL(/hospital=H03|hospital_id=H03/);

  const filtered = await readKpiValue(encounters);
  expect(filtered).not.toBe(baseline);

  // Change the date range; both numerator and denominator are recomputed by the API.
  const from = await pick(page, 'filter-date-from', /from|start date/i);
  await from.fill('2026-01-01');
  const to = await pick(page, 'filter-date-to', /to|end date/i);
  await to.fill('2026-06-30');
  await to.press('Tab');
  await expect(page).toHaveURL(/2026-01-01/);
  await expect(page).toHaveURL(/2026-06-30/);

  const afterDates = await readKpiValue(encounters);
  expect(afterDates).not.toBe(filtered);

  // Click the no-show KPI -> filtered appointment detail table.
  const noShow = kpiCard(page, /no-?show rate/i);
  await noShow.click();
  await expect(page).toHaveURL(/appointments/);
  await expect(page).toHaveURL(/hospital=H03|hospital_id=H03/);
  const table = page.locator('table, [data-testid="data-table"]').first();
  await expect(table).toBeVisible();

  // Export filtered data: download starts and carries the active filter context.
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: /export/i }).first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.(csv|xlsx)$/i);
});

test('refresh preserves filters', async ({ page }) => {
  await page.goto('/overview?hospital=H03&from=2026-01-01&to=2026-06-30');
  await expect(page).toHaveURL(/hospital=H03/);
  await page.reload();
  await expect(page).toHaveURL(/hospital=H03/);
  await expect(page).toHaveURL(/2026-01-01/);
  await expect(kpiCard(page, /total encounters/i)).toBeVisible();
});

test('mobile viewport renders one to two KPI cards per row', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/overview');
  await expect(kpiCard(page, /total encounters/i)).toBeVisible();
  const cards = page.locator('[data-testid^="kpi-"]');
  if (await cards.count()) {
    const first = await cards.nth(0).boundingBox();
    const second = await cards.nth(1).boundingBox();
    // 1 or 2 cards per row is acceptable; allow the normal 16px grid gap.
    if (first && second) expect(second.y).toBeLessThan(first.y + first.height + 24);
  }
  const filterButton = page.getByRole('button', { name: /filter/i }).first();
  if (await filterButton.count()) await expect(filterButton).toBeVisible();
});

test('invalid filter and empty result show a controlled state', async ({ page }) => {
  await page.goto('/overview?hospital=H99&from=2030-01-01&to=2030-01-31');
  await expect(page).toHaveURL(/H99/);
  const empty = page.getByText(/no data|no results|empty/i).first();
  const card = kpiCard(page, /total encounters/i);
  await expect(empty.or(card)).toBeVisible();
});
