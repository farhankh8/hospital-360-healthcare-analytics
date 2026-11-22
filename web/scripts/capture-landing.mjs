import { chromium } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

const base = process.env.BASE_URL || 'http://localhost:3000';
const outDir = path.resolve('public/landing');
const shots = [
  ['overview', '/overview'],
  ['hospitals', '/hospitals'],
  ['finance', '/finance'],
  ['claims', '/claims'],
  ['inpatient', '/inpatient'],
  ['data-quality', '/data-quality'],
  ['pipeline', '/pipeline'],
  ['patient-journey', '/patient-journey'],
];

async function capture(page, name, route, theme) {
  await page.emulateMedia({ colorScheme: theme });
  await page.goto(`${base}${route}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  const file = path.join(outDir, `${name}-1440-${theme}.png`);
  await page.screenshot({ path: file, fullPage: false });
  console.log(file);
}

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
await fs.mkdir(outDir, { recursive: true });
for (const [name, route] of shots) {
  for (const theme of ['light', 'dark']) {
    try { await capture(page, name, route, theme); } catch (e) { console.error(name, theme, e.message); }
  }
}
await browser.close();
