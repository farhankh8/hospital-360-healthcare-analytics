import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const PAGES = [
  { name: 'overview', path: '/overview' },
  { name: 'finance', path: '/finance' },
  { name: 'explorer', path: '/explorer' },
  { name: 'data-quality', path: '/data-quality' },
];

for (const pageInfo of PAGES) {
  test(`a11y: ${pageInfo.name} has no serious/critical axe violations`, async ({ page }) => {
    await page.goto(pageInfo.path, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const bad = results.violations.filter((v) => ['serious', 'critical'].includes(v.impact || ''));
    expect(bad, JSON.stringify(bad.map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length })), null, 2)).toEqual([]);
  });
}
