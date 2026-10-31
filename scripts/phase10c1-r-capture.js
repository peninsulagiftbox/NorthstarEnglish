// Diagnostic output only: calibration gate must pass before any 240-run acceptance.
async page => {
  const origin = new URL(page.url()).origin;
  if ((await page.request.get(origin + '/api/v1/health')).headers()['x-northstar-test-database'] !== 'true') throw Error('isolated target required');
  await page.goto(origin + '/lesson/c1-shared?version=c1-shared-v1&tab=text');
  await page.getByRole('slider').waitFor();
  await page.getByRole('button', { name: '播放设置', exact: true }).click();
  await page.getByLabel('播放模式', { exact: true }).selectOption('sentence');
  const captures = [];
  for (const rate of [0.75, 1, 1.25, 1.5]) {
    for (let step = 0; await page.getByRole('button', { name: '播放速度', exact: true }).getAttribute('data-speed') !== String(rate); step++) {
      if (step > 4) throw Error('rate selection failed');
      await page.getByRole('button', { name: '播放速度', exact: true }).click();
    }
    await page.getByRole('button', { name: '选择并播放句子 1', exact: true }).click();
    await page.waitForFunction(() => { const a = document.querySelector('audio'); return a && !a.paused && a.currentTime > .8; });
    captures.push(await page.evaluate(async rate => {
      const a = document.querySelector('audio');
      if (!a.captureStream) return { rate, supported: false };
      const stream = a.captureStream(), chunks = [];
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      const stopped = new Promise(resolve => recorder.onstop = resolve);
      recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
      const events = [];
      const sample = e => events.push({ event: e.type, at: performance.now(), mediaMs: a.currentTime * 1000 });
      for (const name of ['seeking', 'seeked', 'pause', 'play']) a.addEventListener(name, sample);
      const start = performance.now();
      recorder.start();
      await new Promise(resolve => setTimeout(resolve, 7000));
      recorder.stop(); await stopped;
      const stop = performance.now();
      const encoded = await new Blob(chunks).arrayBuffer();
      const ac = new AudioContext();
      const decoded = await ac.decodeAudioData(encoded.slice(0));
      const pcm = decoded.getChannelData(0);
      let sum = 0; for (const x of pcm) sum += x * x;
      const base64 = data => { let s = ''; for (const x of new Uint8Array(data)) s += String.fromCharCode(x); return btoa(s); };
      const result = { rate, actualRate: a.playbackRate, visibility: document.visibilityState,
        source: a.currentSrc, mime: recorder.mimeType, encodedBytes: encoded.byteLength,
        wallClockMs: stop - start, durationMs: decoded.duration * 1000, sampleRate: decoded.sampleRate,
        frames: pcm.length, rms: Math.sqrt(sum / pcm.length), events,
        encodedBase64: base64(encoded), pcmBase64: base64(pcm.buffer),
        baseLatency: ac.baseLatency, outputLatency: ac.outputLatency,
        sink: ac.sinkId ?? 'default (physical endpoint not verified)' };
      await ac.close(); for (const track of stream.getTracks()) track.stop();
      for (const name of ['seeking', 'seeked', 'pause', 'play']) a.removeEventListener(name, sample);
      return result;
    }, rate));
    if (!await page.locator('audio').evaluate(a => a.paused)) await page.getByRole('button', { name: '暂停播放', exact: true }).click();
  }
  return { status: 'NOT VERIFIED', captures, validAcceptanceMeasurements: 0,
    reason: 'Uncalibrated captureStream/Opus output; callback times are diagnostics, not sample-origin references. Physical output and independent fixed-delay/uncertainty calibration remain unverified.' };
}
