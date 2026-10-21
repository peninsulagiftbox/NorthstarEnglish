async (page) => {
  page.setDefaultTimeout(12000);
  const draftKeys = ['northstar:draft:demo-01-v1:dictation:demo-01-v1-s05','northstar:draft:demo-01-v1:dictation:demo-01-v1-s06','northstar:draft:demo-01-v1:writing:lesson'];
  const originalDrafts = await page.evaluate(keys => keys.map(key => [key,localStorage.getItem(key)]), draftKeys);
  try {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const base = new URL(page.url()).origin;
  const checks = [];
  const assert = (value, message) => { if (!value) throw new Error(message); };
  const screenshot = name => page.screenshot({ path: `docs/evidence/phase-03/screenshots/${name}.png`, fullPage: false });
  const saved = () => page.getByText('浏览位置已保存 · 不计练习完成', { exact: true }).waitFor();
  const waitDraft = value => page.waitForFunction(v => document.querySelector('textarea')?.value === v, value);
  const noOverflow = async () => assert(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), 'Horizontal overflow: ' + page.url());
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(base + '/dashboard');
  await page.getByRole('heading', { name: /The Neighborhood Garden/ }).waitFor();
  await screenshot('dashboard-1440x900'); await noOverflow();
  for (const [label, path] of [['课程中心','/courses'],['智能复习','/review'],['学习报告','/reports'],['个人设置','/settings'],['学习首页','/dashboard']]) {
    await page.getByRole('navigation', { name: '主导航' }).getByRole('link', { name: label }).click();
    await page.waitForURL(base + path); await page.reload();
    await page.getByRole('main').waitFor(); await noOverflow();
    if (path === '/courses') {
      await page.getByText('仅目录 · 暂不可学习', { exact: true }).first().waitFor();
      assert(await page.getByText('仅目录 · 暂不可学习', { exact: true }).count() === 4, 'Four actual catalog-only books');
      await screenshot('courses-1440x900');
    }
    if (path === '/settings') await page.getByText('已连接', { exact: true }).first().waitFor();
  }
  checks.push('six routes, reload, actual catalog and health, explicit empty pages');
  await page.getByRole('link', { name: /开始浏览原创课|继续学习/ }).first().click();
  await page.getByRole('tab', { name: '课文', exact: true }).waitFor();
  await page.goto(base + '/lesson/demo-01?tab=text&sentence=demo-01-v1-s01&english=1&translation=1');
  await saved();
  await screenshot('lesson-1440x900');
  await page.getByRole('button', { name:'内容来源', exact:true }).click();
  await page.getByRole('dialog').getByText('当前范围为本地功能测试，尚不具备正式发布条件。', { exact:true }).waitFor();
  await page.keyboard.press('Escape');
  await page.getByRole('dialog').waitFor({ state:'detached' });
  assert(await page.locator('.sidebar').evaluate(el => el.getBoundingClientRect().width) === 224, '224px sidebar');
  assert(await page.locator('.player-bar').evaluate(el => el.getBoundingClientRect().height) === 76, '76px player');
  await page.getByRole('button', { name: /Leo · 006/ }).click();
  await page.locator('.tutor-explanation').getByText(/beside 表示/).waitFor();
  await saved();
  for (const label of ['精听听写','精读词汇','口语跟读','写作','课时测验','课文']) {
    await page.getByRole('tab', { name: label, exact: true }).click();
    assert(new URL(page.url()).searchParams.get('sentence') === 'demo-01-v1-s06', 'Selection retained across tabs');
    await page.reload();
    await page.getByRole('tab', { name: label, exact: true, selected: true }).waitFor();
    await saved();
  }
  checks.push('six tabs, sentence/tutor binding, URL refresh');
  await page.getByRole('tab', { name: '精听听写', exact: true }).click();
  await page.getByLabel('本句听写草稿', { exact: false }).fill('A local unsubmitted draft.');
  assert(!await page.locator('body').innerText().then(t => t.includes('Please put them beside the blue bench.') || t.includes('请把它们放在蓝色长椅旁边。') || t.includes('beside 表示')), 'Blind mode leaked answer');
  await screenshot('dictation-protected-1440x900');
  await page.getByRole('button', { name: '选择句子 5', exact: true }).click();
  await waitDraft('');
  assert(await page.locator('textarea').inputValue() === '', 'Drafts must be per sentence');
  await page.locator('textarea').fill('Another sentence draft.');
  await page.getByRole('button', { name: '选择句子 6', exact: true }).click();
  await waitDraft('A local unsubmitted draft.');
  assert(await page.locator('textarea').inputValue() === 'A local unsubmitted draft.', 'Sentence draft lost');
  await page.getByRole('tab', { name: '写作', exact: true }).click();
  await page.getByLabel('写作草稿', { exact: false }).fill('I can help in the garden.');
  await page.getByRole('button', { name: '选择句子 7', exact: true }).click();
  await waitDraft('I can help in the garden.');
  assert(await page.locator('textarea').inputValue() === 'I can help in the garden.', 'Writing draft must be lesson-wide');
  await page.reload();
  await page.getByLabel('写作草稿', { exact: false }).waitFor();
  await waitDraft('I can help in the garden.');
  assert(await page.locator('textarea').inputValue() === 'I can help in the garden.', 'Draft lost on reload');
  await saved();
  await page.getByRole('tab', { name: '课文', exact: true }).click();
  await page.getByRole('button', { name: '盲听模式', exact: true }).click();
  await page.getByRole('button', { name: '隐藏译文', exact: true }).click();
  await saved();
  await page.goto(base + '/lesson/demo-01');
  await page.getByRole('button', { name: '显示英文', exact: true }).waitFor();
  assert(new URL(page.url()).searchParams.get('sentence') === 'demo-01-v1-s07', 'Server did not restore selected sentence');
  await page.getByRole('button', { name: '显示译文', exact: true }).waitFor();
  await saved();
  await page.getByRole('button', { name: '显示英文', exact: true }).click();
  await page.goBack();
  await page.getByRole('button', { name: '显示英文', exact: true }).waitFor();
  await page.goForward();
  await page.getByRole('button', { name: '盲听模式', exact: true }).waitFor();
  await saved();
  checks.push('isolated local drafts, refresh, server checkpoint, preferences, browser back/forward');
  for (const width of [1512,1280,979,768,375]) {
    await page.setViewportSize({ width, height:900 }); await noOverflow();
    if (width < 980) {
      assert(!await page.locator('.tutor-desktop').isVisible(), 'Tutor must collapse');
      await page.getByRole('button', { name: '打开句子助教', exact: true }).click();
      await page.getByRole('dialog').waitFor();
      if (width === 979) await screenshot('tutor-drawer-979x900');
      await page.keyboard.press('Escape');
      await page.getByRole('dialog').waitFor({ state:'detached' });
      assert(await page.getByRole('button', { name: '打开句子助教', exact: true }).evaluate(el => el === document.activeElement), 'Drawer must restore focus');
    }
    await screenshot('lesson-' + width + 'x900');
  }
  await page.setViewportSize({ width:1440, height:900 });
  await page.getByRole('tab', { name:'课文', exact:true }).focus();
  await page.keyboard.press('ArrowRight');
  await page.getByRole('tab', { name:'精听听写', exact:true, selected:true }).waitFor();
  checks.push('1440/1512/1280/979/768/375 widths, no overflow, drawer and tab keyboard focus');
  await saved();
  const second = await page.context().newPage();
  second.setDefaultTimeout(12000);
  await second.goto(base + '/lesson/demo-01');
  await second.getByText('浏览位置已保存 · 不计练习完成', { exact:true }).waitFor();
  await page.getByRole('tab', { name:'写作', exact:true }).click();
  await page.locator('.sync-status').filter({ hasText:'另一页面更新了浏览位置。' }).waitFor();
  await waitDraft('I can help in the garden.');
  assert(await page.locator('textarea').inputValue() === 'I can help in the garden.', 'Conflict lost local draft');
  await second.close();
  await page.getByRole('button', { name:'重新载入同步' }).click(); await saved();
  checks.push('two-page revision conflict preserves local draft and offers reload');
  await page.goto(base + '/lesson/missing');
  await page.getByRole('heading', { name:'找不到这个课次' }).waitFor();
  await screenshot('lesson-not-found');
  await page.goto(base + '/lesson/demo-01?tab=unknown&sentence=foreign&english=1');
  await page.getByRole('tab', { name:'课文', exact:true, selected:true }).waitFor();
  assert(new URL(page.url()).searchParams.get('sentence') === 'demo-01-v1-s01', 'Invalid sentence not normalized');
  await saved();
  await page.route('**/api/v1/books', route => route.fulfill({ status:503, contentType:'application/problem+json', body:'{"status":503}' }));
  await page.goto(base + '/courses');
  await page.getByText('课程加载失败，请确认本地服务已启动。', { exact:true }).waitFor();
  await screenshot('courses-error');
  await page.unroute('**/api/v1/books');
  await page.getByRole('button', { name:'重新加载', exact:true }).click();
  await page.getByText('仅目录 · 暂不可学习', { exact:true }).first().waitFor();
  await page.route('**/api/v1/books', route => route.fulfill({ contentType:'application/json', body:'{"books":[],"standaloneLessons":[]}' }));
  await page.reload(); await page.getByRole('heading', { name:'暂无可用原创课' }).waitFor(); await screenshot('courses-empty');
  await page.unroute('**/api/v1/books');
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  await page.route('**/api/v1/books', async route => { await gate; await route.continue(); });
  await page.reload({ waitUntil:'domcontentloaded' });
  await page.getByText('正在从本地 API 读取课程…', { exact:true }).waitFor(); await screenshot('courses-loading');
  release(); await page.getByText('仅目录 · 暂不可学习', { exact:true }).first().waitFor();
  await page.unroute('**/api/v1/books');
  checks.push('unknown lesson, invalid tab/sentence, catalog loading/error/retry/empty');
  await page.goto(base + '/lesson/demo-01?tab=text&sentence=demo-01-v1-s06&english=1&translation=1'); await saved();
  assert(errors.length === 0, 'Browser errors: ' + errors.join('; '));
  return { passed:true, checks, pageErrors:errors };
  } finally { await page.evaluate(values => { for (const [key,value] of values) { if (value === null) localStorage.removeItem(key); else localStorage.setItem(key,value); } }, originalDrafts); }
}
