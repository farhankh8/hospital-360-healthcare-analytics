import { expect, test } from '@playwright/test';

test.describe('Patient Journey', () => {
  test('search sample patient, open timeline, filter by event type, export CSV', async ({ page }) => {
    await page.goto('/patient-journey');
    await expect(page.getByTestId('patient-journey-page')).toBeVisible({ timeout: 15000 });

    await page.getByTestId('journey-sample').click();
    await expect(page.getByTestId('journey-timeline')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('journey-card-patient')).toBeVisible();

    // open a timeline event (drilldown)
    const firstEvent = page.locator('[data-testid="journey-timeline"] button').first();
    await expect(firstEvent).toBeVisible();
    await firstEvent.click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible({ timeout: 10000 });
    await dialog.getByRole('button', { name: 'Close', exact: true }).click();
    await expect(dialog).toBeHidden({ timeout: 5000 });

    // filter by event type if a filter chip exists
    const filterBtn = page.locator('[data-testid^="journey-filter-"]').first();
    if (await filterBtn.count()) {
      await filterBtn.click();
      await expect(page.getByTestId('journey-timeline')).toBeVisible({ timeout: 10000 });
    }

    // export CSV
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('journey-export').click(),
    ]);
    expect(download.suggestedFilename()).toContain('patient-journey');
  });
});
