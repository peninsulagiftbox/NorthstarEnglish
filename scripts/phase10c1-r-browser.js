// Native-background setup only. Do not synthesize visibilitychange.
async page => {
  const health = await page.request.get(new URL(page.url()).origin + '/api/v1/health');
  if (health.headers()['x-northstar-test-database'] !== 'true') throw Error('isolated target required');
  await page.getByRole('slider').waitFor();
  if (!await page.getByRole('region', { name: '播放设置面板' }).count()) await page.getByRole('button', { name: '播放设置', exact: true }).click();
  await page.getByLabel('播放模式', { exact: true }).selectOption('sentence');
  await page.getByRole('button', { name: '选择并播放句子 1', exact: true }).click();
  await page.waitForFunction(() => { const a = document.querySelector('audio'); return a && !a.paused && a.currentTime > .8; });
  await page.evaluate(() => {
    window.c1RVisibility = [];
    const sample = event => {
      const a = document.querySelector('audio');
      window.c1RVisibility.push({ event, at: performance.now(), visibility: document.visibilityState,
        paused: a.paused, time: a.currentTime, trusted: event === 'visibilitychange' ? true : null });
    };
    document.addEventListener('visibilitychange', e => {
      const a = document.querySelector('audio');
      window.c1RVisibility.push({ event: e.type, at: performance.now(), visibility: document.visibilityState,
        paused: a.paused, time: a.currentTime, trusted: e.isTrusted });
    });
    for (const name of ['pause', 'play', 'playing', 'seeked']) document.querySelector('audio').addEventListener(name, () => sample(name));
    sample('setup');
    window.c1RSampleTimer = setInterval(() => sample('sample'), 100);
  });
  return { ready: true, browser: await page.evaluate(() => navigator.userAgent),
    initial: await page.evaluate(() => window.c1RVisibility[0]) };
}
