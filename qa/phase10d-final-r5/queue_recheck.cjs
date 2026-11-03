const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = require('/Users/wangshiqi/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

async function main() {
  const identity = JSON.parse(fs.readFileSync(`${__dirname}/evidence/browser-runtime.json`));
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const result = { pageErrors: [], networkErrors: [], responses: [], attempts: [] };
  page.on('pageerror', error => result.pageErrors.push(error.message));
  page.on('requestfailed', request => result.networkErrors.push({ url: request.url(), failure: request.failure() }));
  page.on('response', response => {
    if (response.url().includes('/api/v1/')) result.responses.push({ url: response.url(), status: response.status() });
  });
  const output = `${identity.root}/output/playwright/phase10d-final-r5`;
  await context.tracing.start({ screenshots: true, snapshots: true });
  try {
    const pages = [], items = [];
    let cursor;
    do {
      const response = await context.request.get(`${identity.web}/api/v1/concept-reviews/due?all=true${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`);
      assert.equal(response.status(), 200);
      const body = await response.json();
      pages.push(body);
      items.push(...body.items);
      cursor = body.nextCursor;
      assert.ok(pages.length < 10);
    } while (cursor);
    assert.equal(items.length, 22);
    assert.equal(new Set(items.map(item => item.id)).size, 22);
    result.pages = pages;
    for (const action of ['initial-all', 'refresh-all', 'reload-all', 'due-only']) {
      if (action === 'initial-all' || action === 'reload-all') {
        await page.goto(`${identity.web}/review`);
        await page.getByRole('button', { name: '全部概念卡', exact: true }).click();
      } else if (action === 'refresh-all') {
        await page.getByRole('button', { name: '刷新概念卡', exact: true }).click();
      } else {
        await page.getByRole('button', { name: /概念卡到期复习/ }).click();
      }
      const section = page.locator('section').filter({ has: page.getByRole('button', { name: '全部概念卡', exact: true }) });
      assert.equal(await section.count(), 1);
      await section.locator('.review-card').first().waitFor();
      await page.waitForLoadState('networkidle');
      const names = await section.locator('.review-card h2').allTextContents();
      result.attempts.push({
        action, conceptCardCount: names.length, names,
        missing: items.filter(item => !names.includes(item.displayName)).map(item => ({ id: item.id, conceptId: item.conceptId, name: item.displayName, rowVersion: item.rowVersion, due: item.due })),
        buttons: await section.locator('button').allTextContents(),
      });
    }
    for (const item of result.attempts[0].missing) {
      const card = await context.request.get(`${identity.web}/api/v1/concept-reviews/${item.id}`);
      const sources = await context.request.get(`${identity.web}/api/v1/concept-reviews/${item.id}/sources`);
      assert.equal(card.status(), 200);
      assert.equal(sources.status(), 200);
      result[`direct-${item.conceptId}`] = { card: await card.json(), sources: await sources.json() };
    }
    result.result = result.attempts.every(attempt => attempt.conceptCardCount === items.length) ? 'PASS' : 'FAIL';
    const section = page.locator('section').filter({ has: page.getByRole('button', { name: '全部概念卡', exact: true }) });
    await section.getByRole('button', { name: '全部概念卡', exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${output}/queue-header.png` });
    await section.screenshot({ path: `${output}/concept-queue-only.png` });
    fs.writeFileSync(`${output}/concept-queue-only.txt`, await section.innerText());
  } finally {
    await context.tracing.stop({ path: `${output}/queue-recheck-trace.zip` });
    await context.close();
    await browser.close();
    fs.writeFileSync(`${__dirname}/evidence/queue-recheck-result.json`, JSON.stringify(result, null, 2) + '\n');
  }
  console.log(JSON.stringify({ result: result.result, apiCount: result.pages.reduce((sum, item) => sum + item.items.length, 0), attempts: result.attempts.map(item => ({ action: item.action, ui: item.conceptCardCount, missing: item.missing })) }));
  process.exitCode = result.result === 'PASS' ? 0 : 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
