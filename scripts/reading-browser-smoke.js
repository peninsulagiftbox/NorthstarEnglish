async (page) => {
  page.setDefaultTimeout(12000);
  const base = new URL(page.url()).origin, checks = [], pageErrors = [];
  const assert = (ok, message) => { if (!ok) throw new Error(message); };
  page.on('pageerror', e => pageErrors.push(e.message));
  const shot = async name => { await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))); return page.screenshot({path:`docs/evidence/phase-05/screenshots/${name}.png`,fullPage:false}); };
  const health = await page.request.get(base+'/api/v1/health');
  assert(health.headers()['x-northstar-test-database']==='true','Write E2E requires isolated test database');
  const context = 'lessonId=demo-01&versionId=demo-01-v2';
  const reading = async () => (await page.request.get(base+'/api/v1/reading?'+context)).json();
  const url=base+'/lesson/demo-01?version=demo-01-v2&tab=vocabulary&sentence=demo-01-v2-s01&english=1&translation=1';
  await page.setViewportSize({width:1440,height:900});await page.goto(url);
  await page.locator('.vocabulary-card').first().waitFor();
  const initial=await reading(), count=initial.questions[0].history.length;
  assert(await page.locator('.vocabulary-card').count()===5,'Five API vocabulary entries');
  for(const word of initial.vocabulary) {
    await page.locator('.vocabulary-select').filter({has:page.getByText(word.term,{exact:true})}).click();
    await page.waitForFunction(id=>new URL(location.href).searchParams.get('sentence')===id,word.sentenceId);
    await page.waitForFunction(text=>document.querySelector('.vocabulary-source')?.textContent.includes(text),word.sourceText);
    assert((await page.locator('.vocabulary-source').textContent()).includes(word.sourceText),'Actual source text');
    assert((await page.locator('.tutor-desktop .tutor-current').innerText()).includes(word.sourceText),'Tutor follows source');
    assert(await page.locator('.vocabulary-source mark').innerText()===word.term,'Term highlighted');
  }
  assert((await reading()).questions[0].history.length===count,'Browse is not a practice');
  const fav=page.getByRole('button',{name:'收藏 beside',exact:true});
  const original=await fav.getAttribute('aria-pressed');
  await fav.click();await page.waitForFunction(expected=>document.querySelector('[aria-label="收藏 beside"]')?.getAttribute('aria-pressed')===expected,original==='true'?'false':'true');
  await page.reload();await page.locator('.vocabulary-card').first().waitFor();
  assert(await fav.getAttribute('aria-pressed')!==(original),'Favorite persisted on refresh');
  assert((await reading()).questions[0].history.length===count,'Favorite is not mastery or practice');
  checks.push('Five source-linked words, highlighted originals, tutor context, favorite refresh, no practice from browsing');
  await shot('vocabulary-1440');
  await page.locator('.vocabulary-select').filter({has:page.getByText('beside',{exact:true})}).click();
  await page.locator('.vocabulary-source').scrollIntoViewIfNeeded();await shot('beside-source-1440');
  await page.getByRole('radio',{name:'Inside the classroom.',exact:true}).check();
  await page.getByRole('button',{name:'提交阅读答案',exact:true}).waitFor();
  await page.waitForFunction(()=>!!document.querySelector('.reading-question .primary') && !document.querySelector('.reading-question .primary').disabled && document.querySelector('.reading-question .primary').getAttribute('aria-disabled')!=='true');
  assert((await reading()).questions[0].state==='in_progress','Selection starts a round');
  await page.getByRole('button',{name:'提交阅读答案',exact:true}).click();
  await page.getByRole('heading',{name:'本次答错 · 已加入复习来源',exact:true}).waitFor();
  assert((await page.locator('.reading-feedback').innerText()).includes('Please put them beside the blue bench.'),'Wrong feedback source');
  assert(new URL(page.url()).searchParams.get('sentence')==='demo-01-v2-s06','Wrong answer auto focuses evidence sentence');
  await shot('wrong-evidence-1440');
  const wrong=(await reading()).questions[0].history[0];
  assert((await (await page.request.get(base+'/api/v1/reviews/items')).json()).some(s=>s.attemptId===wrong.attemptId && s.reason==='reading_evidence_mismatch' && s.knowledgePointId==='demo-01-v2-kp-beside'),'Wrong source in review');
  await page.locator('.reading-feedback').getByRole('button',{name:'在全文中查看上下文 →'}).click();
  await page.getByRole('button',{name:'选择并播放句子 6',pressed:true,exact:true}).waitFor();
  assert((await page.locator('.sentence.selected').innerText()).includes('Please put them beside'),'Evidence link selects original');
  await page.getByRole('tab',{name:'精读词汇',exact:true}).click();
  await page.getByText(`累计真实作答 ${count+1} 次`,{exact:false}).waitFor();
  await page.locator('.reading-history summary').click();
  assert((await page.locator('.reading-history').innerText()).includes('Inside the classroom.'),'History survives tab navigation');
  checks.push('Wrong answer, automatic evidence context, original sentence link, persisted choice and review knowledge source');
  // The server accepts the next answer, then its response is lost. Reload must reuse the same UUID.
  await page.getByRole('radio',{name:'Next to the blue bench.',exact:true}).check();
  await page.waitForFunction(()=>!!document.querySelector('.reading-question .primary') && !document.querySelector('.reading-question .primary').disabled && document.querySelector('.reading-question .primary').getAttribute('aria-disabled')!=='true');
  let lost=true, acceptedEvent='';
  await page.route('**/api/v1/reading/*/attempts',async route=>{
    if(!lost) return route.continue();
    lost=false;acceptedEvent=route.request().postDataJSON().eventId;
    const response=await route.fetch();assert(response.status()===200,'Accepted answer before loss');await route.abort('failed');
  });
  await page.getByRole('button',{name:'提交阅读答案',exact:true}).click();
  await page.getByRole('button',{name:'重试原提交',exact:true}).waitFor();
  await page.reload();await page.getByRole('button',{name:'重试原提交',exact:true}).waitFor();
  assert(await page.getByRole('radio',{name:'Next to the blue bench.',exact:true}).isChecked(),'Pending choice retained');
  await page.unroute('**/api/v1/reading/*/attempts');
  await page.getByRole('button',{name:'重试原提交',exact:true}).click();
  await page.getByRole('heading',{name:'回答正确',exact:true}).waitFor();
  await page.waitForFunction(n=>document.querySelector('.reading-question')?.textContent.includes(`累计真实作答 ${n} 次`),count+2);
  const after=(await reading()).questions[0];
  assert(after.history.length===count+2 && after.history.filter(h=>h.eventId===acceptedEvent).length===1,'Replay creates no duplicate');
  for(const name of ['暂停本轮','跳过本轮']) {
    await page.getByRole('button',{name,exact:true}).click();
    await page.waitForFunction(()=>!!document.querySelector('.reading-question .primary') && !document.querySelector('.reading-question .primary').disabled && document.querySelector('.reading-question .primary').getAttribute('aria-disabled')!=='true');
    assert((await reading()).questions[0].history.length===count+2,'Pause/skip preserve count');
  }
  await page.reload();await page.locator('.vocabulary-card').first().waitFor();
  assert((await reading()).questions[0].state==='skipped','Skipped round persists separately');
  await page.locator('.reading-history summary').click();
  assert(await page.locator('.reading-history li').count()===count+2,'All immutable history retained');
  await shot('history-1440');checks.push('Accepted response loss, IndexedDB pending restore, same-event retry, correct history, pause/skip never count');
  await page.getByRole('radio',{name:'Next to the blue bench.',exact:true}).check();
  await page.waitForFunction(()=>!!document.querySelector('.reading-question .primary') && !document.querySelector('.reading-question .primary').disabled && document.querySelector('.reading-question .primary').getAttribute('aria-disabled')!=='true');
  let releaseResponse, acceptedResolve;
  const held=new Promise(resolve=>releaseResponse=resolve), accepted=new Promise(resolve=>acceptedResolve=resolve);
  await page.route('**/api/v1/reading/*/attempts',async route=>{const response=await route.fetch();acceptedResolve();await held;await route.fulfill({response});});
  await page.getByRole('button',{name:'提交阅读答案',exact:true}).click();await accepted;
  await page.getByRole('tab',{name:'课文',exact:true}).click();
  await page.locator('.sentence-list').waitFor();
  const delivered=page.waitForResponse(r=>r.url().includes('/reading/') && r.url().endsWith('/attempts'));releaseResponse();await delivered;
  await page.waitForLoadState('networkidle');
  await page.unroute('**/api/v1/reading/*/attempts');
  await page.waitForFunction(()=>new URL(location.href).searchParams.get('tab')==='text');
  assert(new URL(page.url()).searchParams.get('tab')==='text','Late response must not change current tab');
  assert((await reading()).questions[0].history.length===count+3,'Late accepted answer remains in history');
  checks.push('Accepted late answer after leaving tab does not steal context');
  await page.goto(base+'/review');await page.locator('.review-card').first().waitFor();
  assert((await page.locator('main').innerText()).includes('阅读证据'),'Review distinguishes reading');await shot('review-source-1440');
  await page.goto(url);await page.locator('.vocabulary-card').first().waitFor();
  for(const width of [1280,979,375]) {
    await page.setViewportSize({width,height:900});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow at '+width);
    await shot('vocabulary-'+width);
    const bounds=await page.locator('.player-bar').boundingBox();assert(bounds && Math.abs(bounds.y+bounds.height-900)<1,'Fixed player bottom at '+width);
    if(width===375) {await page.locator('.reading-question').scrollIntoViewIfNeeded();await shot('reading-375');}
  }
  await page.getByRole('button',{name:'盲听模式',exact:true}).click();
  await page.getByRole('button',{name:'显示英文并开始精读',exact:true}).waitFor();
  assert(await page.locator('.vocabulary-card').count()===0,'Hidden English does not expose cards');
  await page.getByRole('button',{name:'显示英文并开始精读',exact:true}).click();
  await page.locator('.vocabulary-card').first().waitFor();
  checks.push('Review reading labels, 1440/1280/979/375 layout, blind protection');
  // Verify visible error/retry and empty states with explicit API fault injection.
  await page.route('**/api/v1/reading?*',route=>route.fulfill({status:503,contentType:'application/problem+json',body:JSON.stringify({detail:'精读测试故障'})}));
  await page.reload();await page.getByRole('button',{name:'重新读取精读',exact:true}).waitFor();
  await shot('reading-error-375');await page.unroute('**/api/v1/reading?*');
  await page.getByRole('button',{name:'重新读取精读',exact:true}).click();await page.locator('.vocabulary-card').first().waitFor();
  await page.route('**/api/v1/reading?*',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({vocabulary:[],questions:[]})}));
  await page.reload();await page.getByRole('heading',{name:'本版本暂无词条',exact:true}).waitFor();
  await page.unroute('**/api/v1/reading?*');await page.goto(url);await page.locator('.vocabulary-card').first().waitFor();
  checks.push('Injected API503/retry and empty state');
  assert(pageErrors.length===0,'Page errors: '+pageErrors.join(';'));
  return {passed:true,checks,pageErrors,initialCount:count,finalCount:count+3};
}
