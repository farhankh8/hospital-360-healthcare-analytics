import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = 'http://127.0.0.1:3000';
const PAGES = [
  ['overview', '/overview'],
  ['hospital-comparison', '/hospitals'],
  ['hospital-profile', '/hospitals/H01'],
  ['appointments', '/appointments'],
  ['inpatient', '/inpatient'],
  ['finance', '/finance'],
  ['claims', '/claims'],
  ['data-quality', '/data-quality'],
  ['explorer', '/explorer'],
  ['pipeline', '/pipeline'],
  ['kpi-glossary', '/kpi-glossary'],
];
const VIEWPORTS = [[1440,900,'1440'], [390,844,'390']];

const out = path.resolve('docs/ui/before');
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
for (const [w,h,label] of VIEWPORTS) {
  const context = await browser.newContext({ viewport: { width: w, height: h } });
  const page = await context.newPage();
  for (const [name, route] of PAGES) {
    try {
      await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 60000 });
      await page.waitForTimeout(1500);
      const file = path.join(out, `${name}-${label}.png`);
      await page.screenshot({ path: file, fullPage: true });
      console.log('ok', file);
    } catch (e) {
      console.log('fail', name, label, e.message);
    }
  }
  await context.close();
}
await browser.close();
