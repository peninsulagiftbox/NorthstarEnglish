async (page) => {
  page.setDefaultTimeout(12000);
  const base=new URL(page.url()).origin,checks=[],errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const assert=(v,m)=>{if(!v)throw new Error(m);};
  const pick=async n=>{await page.getByRole('button',{name:`选择句子 ${n}`,exact:true}).click();await page.getByRole('button',{name:`选择句子 ${n}`,exact:true,pressed:true}).waitFor();await page.waitForFunction(()=>{const input=document.querySelector('textarea');return input&&!input.disabled&&!input.readOnly;});};
  const play=()=>page.getByRole('button',{name:'播放本句',exact:true}).click();
  const pause=async()=>{if(!await page.locator('audio').evaluate(a=>a.paused)){await page.getByRole('button',{name:'暂停播放',exact:true}).click();await page.waitForFunction(()=>document.querySelector('audio')?.paused);}};
  const setSpeed=async value=>{const button=page.getByRole('button',{name:'播放速度',exact:true});for(let i=0;i<4&&await button.getAttribute('data-speed')!==value;i++)await button.click();assert(await button.getAttribute('data-speed')===value,'Speed cycle target missing');};
  const seek=async t=>{if(!await page.getByRole('slider',{name:'当前句播放进度'}).count()) await page.getByRole('button',{name:'播放设置',exact:true}).click();return page.getByRole('slider',{name:'当前句播放进度'}).evaluate((el,v)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,String(v));el.dispatchEvent(new Event('input',{bubbles:true}));},t);};
  const saved=()=>page.getByText('浏览位置已保存 · 不计练习完成',{exact:true}).waitFor();
  let other;
  try {
    const health = await page.request.get(base + '/api/v1/health');
    assert(health.headers()['x-northstar-test-database'] === 'true', 'Write E2E requires the verified isolated test database');
    await page.goto(base+'/lesson/demo-01?version=demo-01-v1&tab=dictation&sentence=demo-01-v1-s06&english=1');
    await page.getByRole('button',{name:'播放本句',exact:true}).waitFor();
    // A prior full-page navigation can leave a committed checkpoint request in
    // flight. Respect the conflict UI and explicitly reload its new revision;
    // never retry a stale If-Match by silently overwriting another writer.
    await page.waitForFunction(()=>{const s=document.querySelector('.sync-status');return s&&(s.textContent.includes('浏览位置已保存')||s.classList.contains('error'));});
    if (await page.getByRole('button',{name:'重新载入同步',exact:true}).count()) {
      await page.getByRole('button',{name:'重新载入同步',exact:true}).click();
    }
    await saved();
    await play();await page.waitForFunction(()=>document.querySelector('.player-bar')?.dataset.status==='playing');await pause();
    await seek(1.1);await saved();await page.reload();
    await page.waitForFunction(()=>{const a=document.querySelector('audio');return a?.duration>0&&a.paused&&Math.abs(a.currentTime-1.1)<.12;});
    checks.push('server playback sentence and local position restore paused');
    for(const n of [1,2,6]){await pick(n);await play();}
    await page.waitForFunction(()=>document.querySelector('audio')?.src.includes('a06')&&!document.querySelector('audio')?.paused);
    await pick(5);assert(await page.locator('audio').evaluate(a=>a.src.includes('a06')),'Selection switched playing sentence');
    assert(await page.locator('audio').count()===1,'Multiple audio elements');
    await page.getByRole('tab',{name:'课文',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('audio')?.paused);
    await page.getByRole('tab',{name:'精听听写',exact:true}).click();
    await page.getByRole('tab',{name:'精听听写',exact:true,selected:true}).waitFor();
    await page.waitForFunction(()=>!document.body.innerText.includes('Please put them beside'));
    await page.getByRole('heading',{name:'The Neighborhood Garden',exact:true}).click();
    await page.keyboard.press('Space');await page.waitForFunction(()=>document.querySelector('.player-bar')?.dataset.status==='playing');
    await page.keyboard.press('j');await page.waitForFunction(()=>document.querySelector('audio')?.src.includes('a05'));
    await page.keyboard.press('k');await page.waitForFunction(()=>document.querySelector('audio')?.src.includes('a06'));
    await page.keyboard.press('r');assert(await page.locator('.player-bar').getAttribute('data-mode')==='sentence','R loop shortcut');
    await page.keyboard.press('Space');await page.waitForFunction(()=>document.querySelector('audio')?.paused);
    checks.push('rapid source switches, selected/playing separation, tab pause and all four shortcuts');
    if(!await page.getByLabel('播放模式',{exact:true}).count()) await page.getByRole('button',{name:'播放设置',exact:true}).click();
    await setSpeed('1.5');
    await page.getByLabel('播放模式',{exact:true}).selectOption('sequence');await pick(1);await play();
    await page.waitForFunction(()=>document.querySelector('audio')?.duration>0);await seek(3.45);
    await page.waitForFunction(()=>document.querySelector('audio')?.src.includes('a02')&&!document.querySelector('audio')?.paused);await pause();
    await page.getByLabel('播放模式',{exact:true}).selectOption('list');await pick(10);await play();
    await page.waitForFunction(()=>document.querySelector('audio')?.src.includes('a10')&&document.querySelector('audio')?.duration>0);await seek(2.8);
    await page.waitForFunction(()=>document.querySelector('audio')?.src.includes('a01')&&!document.querySelector('audio')?.paused);await pause();
    await page.getByLabel('播放模式',{exact:true}).selectOption('sentence');await pick(6);await play();
    await page.waitForFunction(()=>document.querySelector('audio')?.src.includes('a06')&&document.querySelector('audio')?.duration>0);await seek(3);
    await page.waitForFunction(()=>{const a=document.querySelector('audio');return a?.src.includes('a06')&&!a.paused&&a.currentTime<.6;});await pause();
    checks.push('real ended: sequential next, list wrap, same-sentence loop');
    await page.getByLabel('播放模式',{exact:true}).selectOption('single');
    await pick(9);await page.waitForFunction(()=>{const t=document.querySelector('textarea');return t&&!t.readOnly;});
    const editor=page.getByLabel('本句听写草稿',{exact:true});
    const draftPath='**/api/v1/drafts/demo-01-v1-s09';
    await page.route(draftPath,route=>route.request().method()==='PUT'?route.abort():route.continue());
    await editor.fill('Offline preserved draft for nine.');
    await page.locator('.dictation-draft .message.error').waitFor();
    assert(await editor.inputValue()==='Offline preserved draft for nine.','Offline failure lost local input');
    await page.unroute(draftPath);await page.reload();
    await page.waitForFunction(()=>document.querySelector('textarea')?.value==='Offline preserved draft for nine.');
    await page.waitForFunction(async expected=>{const response=await fetch('/api/v1/drafts/demo-01-v1-s09?lessonId=demo-01&versionId=demo-01-v1');return response.ok&&(await response.json()).text===expected;},'Offline preserved draft for nine.');
    checks.push('offline draft write failure preserves IndexedDB text; reload resumes sync');
    other=await page.context().newPage();
    await other.goto(base+'/lesson/demo-01?version=demo-01-v1&tab=dictation&sentence=demo-01-v1-s09&english=1');
    await other.getByLabel('本句听写草稿',{exact:true}).waitFor();
    await other.waitForFunction(()=>{const t=document.querySelector('textarea');return t&&!t.readOnly;});
    // Persist the other page's start event first, then edit competing drafts from the same revision.
    await other.getByLabel('本句听写草稿',{exact:true}).fill('Other page draft nine.');
    await page.waitForFunction(async expected=>{const response=await fetch('/api/v1/drafts/demo-01-v1-s09?lessonId=demo-01&versionId=demo-01-v1');return response.ok&&(await response.json()).text===expected;},'Other page draft nine.');
    await editor.fill('My conflicting local draft nine.');
    await page.getByRole('heading',{name:'服务端草稿（保留本机输入）',exact:true}).waitFor();
    assert(await editor.inputValue()==='My conflicting local draft nine.','Conflict lost local text');
    assert(await page.locator('.draft-conflict').innerText().then(t=>t.includes('Other page draft nine.')),'Conflict lost server text');
    await page.reload();await page.getByRole('heading',{name:'服务端草稿（保留本机输入）',exact:true}).waitFor();
    assert(await editor.inputValue()==='My conflicting local draft nine.','Conflict local copy lost on refresh');
    await page.screenshot({path:'docs/evidence/phase-04/screenshots/draft-conflict-1440x900.png'});
    await page.getByRole('button',{name:'比较后保留本机稿并同步',exact:true}).click();
    await page.waitForFunction(async expected=>{const response=await fetch('/api/v1/drafts/demo-01-v1-s09?lessonId=demo-01&versionId=demo-01-v1');return response.ok&&(await response.json()).text===expected;},'My conflicting local draft nine.');
    await other.close();other=null;
    checks.push('two-page If-Match conflict retains both texts across reload; explicit resolution');
    // Simulate quota/disabled storage only in the test browser; real submission must stay blocked.
    const failed=await page.context().newPage();
    await failed.addInitScript(()=>{IDBFactory.prototype.open=function(){throw new DOMException('Storage disabled','QuotaExceededError');};});
    await failed.goto(base+'/lesson/demo-01?version=demo-01-v1&tab=dictation&sentence=demo-01-v1-s02');
    await failed.getByText(/草稿同步初始化失败/).waitFor();
    await failed.getByLabel('本句听写草稿',{exact:true}).fill('Preserve this text manually.');
    await failed.getByText(/本机存储失败|无法将提交保存到本机队列/).first().waitFor();
    assert(await failed.locator('textarea').inputValue()==='Preserve this text manually.','Storage error erased input');
    await failed.close();
    checks.push('disabled storage shows failure and retains editable original');
    assert(errors.length===0,'Page errors: '+errors.join(';'));
    return {passed:true,checks,pageErrors:errors};
  } catch(error){await page.screenshot({path:'docs/evidence/phase-04/screenshots/recovery-failure.png'});throw new Error('After '+checks.join(' | ')+': '+error.message);} finally {if(other)await other.close();await page.unrouteAll({behavior:'wait'});}
}
