const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = require('/Users/wangshiqi/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

async function main() {
  const runtime = JSON.parse(fs.readFileSync(`${__dirname}/evidence/browser-runtime.json`));
  const output = `${runtime.root}/output/playwright/phase10d-final-r6`;
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const [a, b] = await Promise.all([context.newPage(), context.newPage()]);
  const result = { buildId: runtime.buildId, databaseUuid: runtime.database.uuid, checks: [] };
  const card = (page, name) => page.locator('.review-card').filter({ has: page.getByRole('heading', { name, exact: true }) });
  try {
    const response = await context.request.get(`${runtime.web}/api/v1/concept-reviews/due?limit=20`);
    assert.equal(response.status(), 200);
    const cards = (await response.json()).items;
    assert.ok(cards.length >= 2);
    const first = cards[0], second = cards[1];
    result.first = { id: first.id, name: first.displayName, initialVersion: first.rowVersion };
    result.second = { id: second.id, name: second.displayName, initialVersion: second.rowVersion };
    await Promise.all([a.goto(`${runtime.web}/review`), b.goto(`${runtime.web}/review`)]);
    await Promise.all([card(a, first.displayName).waitFor(), card(b, first.displayName).waitFor()]);
    await Promise.all([
      card(a, first.displayName).getByRole('button', { name: '翻开答案' }).click(),
      card(b, first.displayName).getByRole('button', { name: '翻开答案' }).click(),
    ]);
    const accepted = a.waitForResponse(r => r.url().includes(`/concept-reviews/${first.id}/results`));
    await card(a, first.displayName).getByRole('button', { name: '记住了 · 延后复习' }).click();
    assert.equal((await accepted).status(), 200);
    const stale = b.waitForResponse(r => r.url().includes(`/concept-reviews/${first.id}/results`));
    await card(b, first.displayName).getByRole('button', { name: '记住了 · 延后复习' }).click();
    assert.equal((await stale).status(), 409);
    await card(b, first.displayName).getByText('此操作已被拒绝且未计数。').waitFor();
    await b.screenshot({ path: `${output}/dual-tab-conflict.png` });
    result.checks.push('same-version A 200, B 409 and explicit conflict UI');
    await card(a, second.displayName).waitFor();
    await card(a, second.displayName).getByRole('button', { name: '翻开答案' }).click();
    await context.setOffline(true);
    await card(a, second.displayName).getByRole('button', { name: '记住了 · 延后复习' }).click();
    await card(a, second.displayName).getByRole('button', { name: '重试原自评' }).waitFor();
    await a.screenshot({ path: `${output}/offline-pending.png` });
    result.checks.push('offline command kept pending');
    await context.setOffline(false);
    const retry = a.waitForResponse(r => r.url().includes(`/concept-reviews/${second.id}/results`));
    await card(a, second.displayName).getByRole('button', { name: '重试原自评' }).click();
    assert.equal((await retry).status(), 200);
    await a.reload();
    const updated = await context.request.get(`${runtime.web}/api/v1/concept-reviews/due?limit=20`);
    assert.equal(updated.status(), 200);
    const after = (await updated.json()).items;
    assert.ok(!after.some(item => item.id === first.id || item.id === second.id));
    result.checks.push('online retry accepted and refreshed due queue omits two scheduled cards');
    result.status = 'PASS';
  } catch (error) {
    result.status = 'FAIL';
    result.error = error.stack;
  } finally {
    await context.close();
    await browser.close();
    fs.writeFileSync(`${__dirname}/evidence/dual-tab-result.json`, JSON.stringify(result, null, 2) + '\n');
  }
  assert.equal(result.status, 'PASS', result.error);
}

main().catch(error => { console.error(error); process.exitCode = 1; });
