async (page) => {
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const response = await page.request.get(new URL("/api/v1/lessons/demo-01", page.url()).toString());
  if (response.status() !== 200) throw new Error("Expected real course API");
  const lesson = await response.json();
  if (lesson.sentences.length !== 10 || lesson.releaseReady !== false) throw new Error("Wrong content or rights boundary");
  // Temporary browser audit panel, never shipped as production UI.
  await page.evaluate((lesson) => {
    const panel = document.createElement("section");
    panel.style.cssText = "position:relative;background:white;padding:24px;margin:20px;border:2px solid #0d806d;z-index:10";
    const heading = document.createElement("h2");
    heading.textContent = "Phase 02 音频 API 验证（临时测试面板，非学习工作台）";
    panel.append(heading);
    const note = document.createElement("p");
    note.textContent = "10 段原型合成音频；来源授权 pending_review，正式发布受阻。";
    panel.append(note);
    const button = document.createElement("button");
    button.textContent = "验证播放全部十段音频";
    panel.append(button);
    const rows = [];
    window.northstarMediaAudit = { done: false, results: [] };
    for (const sentence of lesson.sentences) {
      const row = document.createElement("div");
      const text = document.createElement("span");
      text.textContent = sentence.id + " · ";
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.preload = "metadata";
      audio.src = sentence.audio.uri;
      row.append(text, audio);
      panel.append(row);
      rows.push({ sentence, audio, text });
    }
    document.body.prepend(panel);
    button.onclick = async () => {
      button.disabled = true;
      try {
        for (const { sentence, audio, text } of rows) {
          const samples = [];
          audio.ontimeupdate = () => samples.push(audio.currentTime);
          await new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error("Playback timeout: " + sentence.id)), 15000);
            audio.onended = () => { clearTimeout(timer); resolve(); };
            audio.onerror = () => { clearTimeout(timer); reject(new Error("Decode/play error: " + sentence.id)); };
            audio.play().catch(error => { clearTimeout(timer); reject(error); });
          });
          const durationMs = Math.round(audio.duration * 1000);
          if (!samples.some(time => time > 0) || Math.abs(durationMs - sentence.audio.durationMs) > 150) {
            throw new Error("Duration/time progression mismatch: " + sentence.id);
          }
          const result = { id: sentence.id, uri: sentence.audio.uri, durationMs, expectedMs: sentence.audio.durationMs, ended: audio.ended, timeAdvanced: true };
          window.northstarMediaAudit.results.push(result);
          text.textContent = sentence.id + " · PASS（已播放至 ended） ";
        }
      } catch (error) { window.northstarMediaAudit.error = String(error); }
      window.northstarMediaAudit.done = true;
    };
  }, lesson);
  await page.getByRole("button", { name: "验证播放全部十段音频" }).click();
  await page.waitForFunction(() => window.northstarMediaAudit.done, null, { timeout: 90000 });
  const result = await page.evaluate(() => window.northstarMediaAudit);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.screenshot({ path: "docs/evidence/phase-02/screenshots/audio-api-browser-audit.png", fullPage: true });
  if (result.error || result.results.length !== 10 || errors.length) throw new Error(JSON.stringify({ result, errors }));
  return { passed: true, browser: page.context().browser().version(), ...result, errors };
}
