const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = require('/Users/wangshiqi/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

async function main() {
  const runtime = JSON.parse(fs.readFileSync(`${__dirname}/evidence/browser-runtime.json`));
  const expected = Number(process.env.CARD_COUNT);
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
  const page = await context.newPage(), result = { expected, checks: [], errors: [] };
  page.on('pageerror', error => result.errors.push(error.message));
  const output = `${runtime.root}/output/playwright/phase10d2-r5-independent`;
  fs.mkdirSync(output, { recursive: true });
  const section = page.locator('section').filter({ has: page.getByRole('button', { name: '全部概念卡', exact: true }) });
  const all = section.getByRole('button', { name: '全部概念卡', exact: true });
  const due = section.getByRole('button', { name: /概念卡到期复习/ });
  const refresh = section.getByRole('button', { name: '刷新概念卡', exact: true });
  const more = section.getByRole('button', { name: '加载更多概念卡', exact: true });
  const idle = () => section.getByText('正在读取概念复习计划…', { exact: true }).waitFor({ state: 'hidden' });
  const names = () => section.locator('.review-card h2').allTextContents();
  async function drain() {
    await idle(); let pages = 0;
    while (await more.count()) { await more.click(); await section.getByText('正在加载更多…', { exact: true }).waitFor({ state: 'hidden' }); assert.ok(++pages < 10); }
  }
  async function api() {
    const items = []; let cursor;
    do {
      const response = await context.request.get(`${runtime.web}/api/v1/concept-reviews/due?all=true${cursor ? '&cursor=' + encodeURIComponent(cursor) : ''}`);
      assert.equal(response.status(), 200); const body = await response.json(); items.push(...body.items); cursor = body.nextCursor;
    } while (cursor);
    assert.equal(new Set(items.map(item => item.id)).size, expected); return items;
  }
  async function compare(mode, label) {
    await drain(); const cards = await api(), wanted = cards.filter(item => mode || item.due).map(item => item.displayName);
    assert.deepEqual(await names(), wanted, label);
    result.checks.push({ label, count: wanted.length });
  }
  try {
    await page.goto(`${runtime.web}/review`); await section.waitFor(); await idle();
    if (process.env.BASELINE === '1') {
      await all.click(); await page.waitForLoadState('networkidle');
      assert.equal((await api()).length, expected); assert.equal((await names()).length, 20); assert.equal(await more.count(), 0);
      result.checks.push({ label: 'R5 original reproduced', api: expected, ui: 20, noPagination: true });
    } else {
      await compare(false, 'initial-due');
      await all.click(); await compare(true, 'all');
      await refresh.click(); await compare(true, 'refresh');
      await due.click(); await compare(false, 'switch-due');
      await page.reload(); await section.waitFor(); await compare(false, 'reopen');
      if (expected === 100) {
        await all.click(); await drain();
        const cards = await api(), item = cards[99];
        const far = section.locator('.review-card').filter({ has: page.getByRole('heading', { name: item.displayName, exact: true }) });
        await far.locator('summary').click(); await far.getByRole('link', { name: /查看这次练习/ }).waitFor();
        assert.ok(cards.indexOf(item) >= 20, 'rating target must be outside first page');
        let delivered;
        await context.route('**/concept-reviews/*/results', async route => { delivered = await (await route.fetch()).json(); await route.abort('failed'); });
        await far.getByRole('button', { name: '翻开答案', exact: true }).click();
        await far.getByRole('button', { name: '记住了 · 延后复习', exact: true }).click();
        await far.getByRole('button', { name: '重试原自评', exact: true }).waitFor();
        await context.unroute('**/concept-reviews/*/results');
        await page.reload(); await section.waitFor(); await drain();
        const pending = section.locator('.review-card').filter({ has: page.getByRole('heading', { name: item.displayName, exact: true }) });
        await pending.getByRole('button', { name: '重试原自评', exact: true }).click(); await idle();
        await compare(false, 'outbox replay after reopen');
        result.rating = { cardId: item.id, eventId: delivered.eventId, rowVersion: delivered.rowVersion };
        await all.click(); await idle();
        let release, started;
        const seen = new Promise(resolve => { started = resolve; });
        await context.route('**/concept-reviews/due*cursor=*', async route => { started(); await new Promise(resolve => { release = resolve; }); await route.continue(); });
        await more.click(); await seen; await refresh.click(); await idle(); release();
        await page.waitForLoadState('networkidle'); assert.equal((await names()).length, 20, 'late page after refresh');
        await context.unrouteAll({ behavior: 'wait' });
        let requests = 0;
        await context.route('**/concept-reviews/due*cursor=*', async route => { requests++; await new Promise(resolve => setTimeout(resolve, 300)); await route.continue(); });
        await more.evaluate(button => { button.click(); button.click(); button.click(); });
        await section.getByText('正在加载更多…', { exact: true }).waitFor({ state: 'hidden' });
        assert.equal(requests, 1); assert.equal((await names()).length, 40);
        await context.unrouteAll({ behavior: 'wait' });
        await context.route('**/concept-reviews/due*cursor=*', async route => { await new Promise(resolve => setTimeout(resolve, 500)); await route.continue(); });
        await more.click(); await due.click(); await idle(); await page.waitForLoadState('networkidle');
        await context.unrouteAll({ behavior: 'wait' }); await page.waitForLoadState('networkidle');
        assert.ok((await names()).length <= 20);
        await compare(false, 'late page after mode switch');
        await all.click(); await idle();
        await context.route('**/concept-reviews/due*cursor=*', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'fixture unavailable' }) }));
        await more.click(); await section.getByRole('button', { name: '重新加载', exact: true }).waitFor();
        assert.equal((await names()).length, 20);
        await context.unroute('**/concept-reviews/due*cursor=*');
        await section.getByRole('button', { name: '重新加载', exact: true }).click(); await compare(true, 'page-error-retry');
      }
      if (expected === 101) {
        await all.click(); await drain();
        const bank = section.locator('.review-card').filter({ has: page.getByRole('heading', { name: 'bank — financial institution', exact: true }) });
        await bank.locator('summary').click();
        const raw = []; let cursor;
        do { const response = await context.request.get(`${runtime.web}/api/v1/concept-reviews/${runtime.bankCardId}/sources${cursor ? '?cursor=' + encodeURIComponent(cursor) : ''}`); const body = await response.json(); raw.push(...body.items); cursor = body.nextCursor; } while (cursor);
        assert.equal(raw.length, 83); assert.equal(new Set(raw.map(item => item.attemptId + ':' + item.occurrenceId)).size, 83);
        for (const source of raw.filter(item => item.restricted)) assert.deepEqual(Object.keys(source).sort(), ['attemptId','lessonId','occurrenceId','recordedAt','restricted','versionId','visible'].sort());
        while (await bank.getByRole('button', { name: '加载更多来源', exact: true }).count()) { await bank.getByRole('button', { name: '加载更多来源', exact: true }).click(); await bank.getByText('正在读取来源…', { exact: true }).waitFor({ state: 'hidden' }); }
        assert.equal(await bank.getByText(/内容不可用（课程已撤回或无访问权限）/).count(), 82);
        assert.equal(await bank.getByRole('link', { name: /查看这次练习/ }).count(), 1);
        result.sources = { api: raw.length, restricted: 82, visible: 1, fieldsChecked: true };
      }
    }
    assert.deepEqual(result.errors, []); result.result = 'PASS';
    await section.screenshot({ path: `${output}/${process.env.BASELINE ? 'baseline' : 'matrix'}-${expected}.png` });
  } catch (error) { result.result = 'FAIL'; result.error = error.stack; }
  finally {
    const label = `${process.env.BASELINE ? 'baseline' : 'matrix'}-${expected}`;
    await context.tracing.stop({ path: `${output}/${label}.zip` }); await browser.close();
    fs.writeFileSync(`${__dirname}/evidence/${label}.json`, JSON.stringify(result, null, 2));
  }
  console.log(JSON.stringify(result)); process.exitCode = result.result === 'PASS' ? 0 : 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
