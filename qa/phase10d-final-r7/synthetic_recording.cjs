const fs = require('node:fs');
const { chromium } = require('/Users/wangshiqi/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const base64 = await page.evaluate(async () => {
      const audio = new AudioContext();
      const source = audio.createOscillator();
      const destination = audio.createMediaStreamDestination();
      source.frequency.value = 440;
      source.connect(destination);
      const chunks = [];
      const recorder = new MediaRecorder(destination.stream, { mimeType: 'audio/webm;codecs=opus' });
      recorder.ondataavailable = event => chunks.push(event.data);
      const complete = new Promise(resolve => recorder.onstop = resolve);
      recorder.start();
      source.start();
      await new Promise(resolve => setTimeout(resolve, 900));
      source.stop();
      recorder.stop();
      await complete;
      await audio.close();
      const bytes = new Uint8Array(await new Blob(chunks).arrayBuffer());
      let binary = '';
      for (const value of bytes) binary += String.fromCharCode(value);
      return btoa(binary);
    });
    fs.writeFileSync(process.argv[2], Buffer.from(base64, 'base64'), { flag: 'wx', mode: 0o600 });
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
