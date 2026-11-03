const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = require('/Users/wangshiqi/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

async function main() {
  const expected = Number(process.env.DUE_COUNT);
  const identity = JSON.parse(fs.readFileSync(`${__dirname}/evidence/browser-runtime.json`, 'utf8'));
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.tracing.start({ screenshots: true, snapshots: true });
  const page = await context.newPage();
  const result = { expected, pageErrors: [], networkErrors: [] };
  page.on('pageerror', error => result.pageErrors.push(error.message));
  page.on('requestfailed', request => result.networkErrors.push({ url: request.url(), failure: request.failure() }));
  const output = `${identity.root}/output/playwright/phase10d2-r5-fix`;
  const section = page.locator('section').filter({ has: page.getByRole('button', { name: /全部概念卡/ }) });
  const dueButton = section.getByRole('button', { name: /概念卡到期复习/ });
  const allButton = section.getByRole('button', { name: /全部概念卡/ });
  const loadMore = section.getByRole('button', { name: '加载更多概念卡', exact: true });
  const cardNames = () => section.locator('.review-card h2').allTextContents();
  try {
    await page.goto(`${identity.web}/review`);
    await dueButton.click();
    await section.getByText('正在读取概念复习计划…', { exact: true }).waitFor({ state: 'hidden' });
    while (await loadMore.count()) {
      await loadMore.click();
      await section.getByText('正在加载更多…', { exact: true }).waitFor({ state: 'hidden' });
    }
    if (expected === 0) {
      await section.getByText('当前没有到期的概念卡').waitFor();
      assert.match(await dueButton.textContent(), /已加载 0/);
      while (await loadMore.count()) {
        await loadMore.click();
        for (;;) {
          if (!(await loadMore.count()) || !(await loadMore.isDisabled())) break;
          await page.waitForTimeout(120);
        }
      }
      assert.equal((await cardNames()).length, 0);
      result.loadedLabel = await dueButton.textContent();
    } else {
      await section.locator('.review-card').first().waitFor();
      while (await loadMore.count()) {
        await loadMore.click();
        for (;;) {
          if (!(await loadMore.count()) || !(await loadMore.isDisabled())) break;
          await page.waitForTimeout(120);
        }
      }
      const names = await cardNames();
      assert.equal(names.length, expected, `expected ${expected} due cards, saw ${names.length}`);
      assert.equal(new Set(names).size, expected, 'duplicate due cards');
      await section.getByText(`已读取全部分页，显示 ${expected} 张概念卡，其中到期 ${expected} 张。`).waitFor();
      result.loadedLabel = await dueButton.textContent();
    }
    result.result = 'PASS';
    await page.screenshot({ path: `${output}/due-${expected}.png`, fullPage: true });
  } catch (error) {
    result.result = 'ERROR';
    result.error = error.stack;
    await page.screenshot({ path: `${output}/failure-due-${expected}.png`, fullPage: true }).catch(() => {});
  } finally {
    await context.tracing.stop({ path: `${output}/trace-due-${expected}.zip` });
    await context.close();
    await browser.close();
    fs.writeFileSync(`${__dirname}/evidence/due-check-${expected}.json`, JSON.stringify(result, null, 2) + '\n');
  }
  console.log(JSON.stringify({ expected, result: result.result, error: result.error }));
  process.exitCode = result.result === 'PASS' ? 0 : 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
