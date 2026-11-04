const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = require('/Users/wangshiqi/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

(async () => {
  const runtime = JSON.parse(fs.readFileSync('qa/phase10d-final-r7/evidence/r7-browser-runtime.json'));
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const media = [];
  page.on('response', response => {
    if (/audio|media/.test(response.url())) media.push({ url: response.url(), status: response.status() });
  });
  try {
    await page.goto(runtime.web + '/lesson/demo-01');
    const player = page.getByRole('region', { name: '音频播放器' });
    await player.waitFor();
    assert.match(page.url(), /version=demo-01-v2/);
    assert.equal(await page.getByText('The Neighborhood Garden').count() > 0, true);
    await player.getByRole('button', { name: '播放', exact: true }).click();
    await page.waitForTimeout(450);
    const first = await player.getAttribute('data-status');
    assert.ok(['playing', 'ended', 'paused'].includes(first), first);
    const firstAudio = await page.locator('audio').evaluate(audio => ({ source: audio.currentSrc, readyState: audio.readyState, error: audio.error?.code ?? null }));
    assert.ok(firstAudio.source && firstAudio.readyState >= 2 && firstAudio.error === null, firstAudio);
    await page.getByRole('button', { name: '选择并播放句子 2' }).click();
    await page.waitForTimeout(300);
    const second = await player.getAttribute('data-sentence');
    assert.equal(second, 'demo-01-v2-s02');
    const pause = player.getByRole('button', { name: '暂停播放' });
    if (await pause.count()) await pause.click();
    await page.reload();
    await player.waitFor();
    assert.match(page.url(), /sentence=demo-01-v2-s02/);
    const path = 'output/playwright/phase10d-final-r7';
    fs.mkdirSync(path, { recursive: true });
    await page.screenshot({ path: path + '/demo-playback.png', fullPage: true });
    const result = { status: 'PASS', databaseUuid: runtime.databaseUuid, buildId: runtime.buildId,
                     firstPlaybackStatus: first, firstAudio, selectedSentence: second, refreshRestoredSentence: true,
                     mediaResponses: media };
    fs.writeFileSync('qa/phase10d-final-r7/evidence/r7-browser-demo-result.json', JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
