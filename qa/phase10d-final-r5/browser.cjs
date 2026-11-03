const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = require('/Users/wangshiqi/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

async function main() {
  const identity = JSON.parse(fs.readFileSync(`${__dirname}/evidence/browser-runtime.json`, 'utf8'));
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
  const page = await context.newPage();
  const pageErrors = [], networkErrors = [], responses = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('requestfailed', request => networkErrors.push({ url: request.url(), failure: request.failure() }));
  page.on('response', response => {
    if (response.url().includes('/api/v1/')) responses.push({ url: response.url(), status: response.status() });
  });
  const result = { runtime: identity, pageErrors, networkErrors, responses };
  const output = `${identity.root}/output/playwright/phase10d-final-r5`;
  fs.mkdirSync(output, { recursive: true });
  try {
    await page.goto(`${identity.web}/review`);
    await page.getByRole('button', { name: '全部概念卡', exact: true }).click();
    const bank = page.locator('.review-card').filter({ has: page.getByRole('heading', { name: 'bank — financial institution', exact: true }) });
    await bank.waitFor();
    await bank.locator('summary').click();
    await bank.getByText(/已显示 [01]\/1 条可见/).waitFor();
    let clicks = 0;
    while (await bank.getByRole('button', { name: '加载更多来源', exact: true }).count()) {
      const response = page.waitForResponse(response => response.url().includes(`/concept-reviews/${identity.cardId}/sources?cursor=`));
      await bank.getByRole('button', { name: '加载更多来源', exact: true }).click();
      assert.equal((await response).status(), 200);
      await bank.getByText('正在读取来源…', { exact: true }).waitFor({ state: 'hidden' });
      assert.ok(++clicks <= 5);
    }
    result.sources = {
      restricted: await bank.getByText(/内容不可用（课程已撤回或无访问权限）/).count(),
      visible: await bank.getByRole('link', { name: /查看这次练习/ }).count(),
      summary: await bank.locator('summary').innerText(), clicks,
    };
    assert.equal(result.sources.restricted, 82);
    assert.equal(result.sources.visible, 1);
    result.sources.result = 'PASS';
    await bank.locator('summary').scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${output}/sources-fixed.png` });
    await bank.locator('summary').click();
    const queuePages = [], queueItems = [];
    let cursor = null;
    do {
      const response = await context.request.get(`${identity.web}/api/v1/concept-reviews/due?all=true${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`);
      assert.equal(response.status(), 200);
      const body = await response.json();
      queuePages.push(body);
      queueItems.push(...body.items);
      cursor = body.nextCursor;
      assert.ok(queuePages.length < 10);
    } while (cursor);
    const readUI = async () => page.locator('.review-card h2').allTextContents();
    const initialUI = await readUI();
    await Promise.all([
      page.waitForResponse(response => response.url().includes('/concept-reviews/due?all=true')),
      page.getByRole('button', { name: '刷新概念卡', exact: true }).click(),
    ]);
    await page.reload();
    await page.getByRole('button', { name: '全部概念卡', exact: true }).click();
    await page.locator('.review-card').first().waitFor();
    const afterReload = await readUI();
    result.queue = {
      pages: queuePages, apiCount: queueItems.length, initialUI, afterReload,
      missing: queueItems.filter(item => !afterReload.includes(item.displayName)),
      buttons: await page.locator('button').allTextContents(),
      result: afterReload.length === queueItems.length ? 'PASS' : 'FAIL',
    };
    await page.screenshot({ path: `${output}/queue-boundary.png`, fullPage: true });
    fs.writeFileSync(`${output}/queue-dom.txt`, await page.locator('body').innerText());
    result.result = result.queue.result;
  } catch (error) {
    result.result = 'ERROR';
    result.error = error.stack;
  } finally {
    await context.tracing.stop({ path: `${output}/browser-trace.zip` });
    await context.close();
    await browser.close();
    fs.writeFileSync(`${__dirname}/evidence/browser-result.json`, JSON.stringify(result, null, 2) + '\n');
  }
  console.log(JSON.stringify({ result: result.result, sources: result.sources, queue: result.queue && { api: result.queue.apiCount, ui: result.queue.afterReload.length, missing: result.queue.missing.map(item => item.id) }, error: result.error }));
  process.exitCode = result.result === 'PASS' ? 0 : 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
