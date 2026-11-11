async page => {
  const base = new URL(page.url()).origin;
  const checks = [], errors = [];
  const assert = (value, message) => { if (!value) throw Error(message); };
  const get = async path => {
    const response = await page.request.get(base + '/api/v1' + path);
    assert(response.ok(), path + ': ' + response.status());
    return response.json();
  };
  const health = await page.request.get(base + '/api/v1/health');
  assert(health.headers()['x-northstar-test-database'] === 'true', 'isolated schema required');
  assert((await health.json()).migrationVersion === '013.04', 'V013.04 required');
  page.setDefaultTimeout(20000);
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({width: 1440, height: 900});
  const catalog = await get('/lessons');
  assert(JSON.stringify(catalog).includes('sample-a') && JSON.stringify(catalog).includes('sample-b'), 'imported courses in catalog');
  for (const [name, count, total] of [['a', 12, 5], ['b', 24, 12]]) {
    const id = 'sample-' + name, version = id + '-v1';
    const lesson = await get('/lessons/' + id + '?versionId=' + version);
    assert(lesson.sentences.length === count && lesson.paragraphs.length === (name === 'a' ? 2 : 3), 'paragraph and sentence counts');
    assert(lesson.contentReadiness === 'basic_content', 'basic readiness only');
    assert(!JSON.stringify(lesson).includes('storageKey') && !JSON.stringify(lesson).includes('answerKey'), 'private values absent');
    await page.goto(base + '/lesson/' + id + '?version=' + version + '&tab=text&sentence=' + version + '-s1&english=1');
    await page.getByRole('button', {name: '播放', exact: true}).waitFor();
    await page.getByRole('button', {name: '播放', exact: true}).click();
    await page.waitForFunction(() => document.querySelector('.player-bar')?.getAttribute('data-status') === 'playing');
    await page.waitForFunction(() => Number(document.querySelector('input[aria-label="当前句播放进度"]')?.value) > 0.3);
    await page.getByRole('button', {name: '暂停播放', exact: true}).click();
    await page.screenshot({path: 'output/playwright/phase10e/' + name + '-reading.png'});
    await page.reload();
    await page.getByRole('button', {name: '播放', exact: true}).waitFor();
    assert(await page.locator('.player-bar').getAttribute('data-sentence') === version + '-s1', 'sentence resume');
    const quiz = await get('/quiz?lessonId=' + id + '&versionId=' + version);
    assert(quiz.questions.length === total, 'imported quiz question count');
    assert(!JSON.stringify(quiz.questions).includes('answerKey'), 'quiz does not reveal answer keys');
    await page.goto(base + '/lesson/' + id + '?version=' + version + '&tab=quiz');
    await page.getByRole('button', {name: '提交本轮 ' + total + ' 题', exact: true}).waitFor();
    for (const group of await page.locator('fieldset').all()) {
      const radios = group.getByRole('radio');
      if (await radios.count()) await group.getByRole('radio', {name: 'Next to', exact: true}).check();
    }
    await page.getByRole('button', {name: '提交本轮 ' + total + ' 题', exact: true}).click();
    await page.getByRole('heading', {name: '本轮结果：' + total + ' / ' + total + ' 题正确', exact: true}).waitFor();
    await page.screenshot({path: 'output/playwright/phase10e/' + name + '-quiz.png'});
    const after = await get('/quiz?lessonId=' + id + '&versionId=' + version);
    assert(after.history.length === quiz.history.length + 1 && after.history[0].correctCount === total, 'actual quiz score and denominator');
    checks.push(id + ': real media, resume, ' + total + '-question quiz, answer privacy');
  }
  await page.goto(base + '/lesson/recover-1?version=recover-1-v1&tab=quiz');
  await page.getByText('本版本暂无课时测验，不生成完成记录。', {exact: true}).waitFor();
  await page.screenshot({path: 'output/playwright/phase10e/no-exercises.png'});
  const old = await get('/lessons/change?versionId=change-v1');
  const current = await get('/lessons/change');
  assert(old.versionId === 'change-v1' && current.versionId === 'change-v2', 'old URLs and current pointer');
  checks.push('empty exercises and historical version access');
  assert(errors.length === 0, JSON.stringify(errors));
  return {passed: true, checks, errors, humanListening: 'NOT VERIFIED; playback is browser runtime evidence only'};
}
