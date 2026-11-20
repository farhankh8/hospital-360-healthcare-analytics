/**
 * Blueprint §31: every one of the 21 specified pages must be implemented.
 * This smoke checks that every route renders a heading and produces no
 * uncaught browser error.
 */
import { test, expect } from '@playwright/test';

const ROUTES = [
  '/overview',
  '/hospitals',
  '/hospitals/H01',
  '/appointments',
  '/emergency',
  '/inpatient',
  '/procedures',
  '/diagnostics',
  '/pharmacy',
  '/finance',
  '/claims',
  '/workforce',
  '/inventory',
  '/experience',
  '/quality',
  '/explorer',
  '/patient-journey',
  '/data-quality',
  '/pipeline',
  '/kpi-glossary',
  '/methodology',
];

test('all 21 blueprint routes render without browser errors', async ({ page }) => {
  test.setTimeout(180_000);
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));

  for (const route of ROUTES) {
    errors.length = 0;
    const response = await page.goto(route, { waitUntil: 'domcontentloaded' });
    expect(response?.status(), `${route} status`).toBe(200);
    await expect(page.locator('h1, h2').first(), `${route} heading`).toBeVisible();
    expect(errors, `${route} browser errors`).toEqual([]);
  }
});
