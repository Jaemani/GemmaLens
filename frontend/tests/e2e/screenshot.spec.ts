import { test } from '@playwright/test';
const BASE = 'http://localhost:3003';
const DOC_ID = '532f7cd3-04df-496e-8f08-de2f2942c427';

test('screenshots', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });

  await page.goto(`${BASE}/dictionary`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await page.screenshot({ path: '/tmp/ss_lib3.png' });

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.screenshot({ path: '/tmp/ss_dash2.png' });

  await page.goto(`${BASE}/analysis/${DOC_ID}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/ss_reader2.png' });

  // right panel clip
  await page.screenshot({ path: '/tmp/ss_reader_right2.png', clip: { x: 680, y: 0, width: 600, height: 900 } });
});
