/**
 * Playwright configuration for the HOSPITAL 360 browser journey.
 *
 * The Next.js app and FastAPI backend must already be running (see README.md):
 *   npm run dev            # in web/       -> http://localhost:3000
 *   uvicorn api.main:app   # in hospital360 -> http://localhost:8000/api/v1
 *
 * Run from the web/ directory:
 *   npx playwright test --config=e2e/playwright.config.ts
 *
 * The TypeScript test runner comes from the npm package @playwright/test
 * (`npm i -D @playwright/test` in web/, or let npx fetch it). The Python
 * `playwright` package in requirements-dev.txt is used to install browsers:
 *   python -m playwright install chromium
 */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  retries: 0,
  // Two workers keep the single API process stable on Windows while still
  // covering both chromium and mobile projects in parallel.
  workers: 2,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report' }]],
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 5'] } },
  ],
});
