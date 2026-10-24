// Rendering and target-safety regression; every write is mocked, never sent to the main DB.
async page=>{
 const errors=[],posts=[],draftWrites=[],results=[];let failNext=false,failedEvent='',resumeRevision=0;
 page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push(e.message));
 const sid=n=>`demo-01-v2-s${String(n).padStart(2,'0')}`;
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),url=new URL(req.url());
  if(req.method()==='GET'&&url.pathname.startsWith('/api/v1/drafts/')){await new Promise(r=>setTimeout(r,600));const id=url.pathname.split('/').at(-1);return route.fulfill({json:{text:`Draft for ${id}`,rowVersion:1}});}
  if(req.method()==='GET'&&url.pathname==='/api/v1/study/stages'){await new Promise(r=>setTimeout(r,600));return route.fulfill({json:Array.from({length:10},(_,i)=>({sentenceId:sid(i+1),state:'not_started',practiceCount:0}))});}
  if(req.method()==='GET'&&url.pathname==='/api/v1/recordings'){await new Promise(r=>setTimeout(r,600));return route.fulfill({json:{state:'not_started',recordings:[]}});}
  if(req.method()==='POST'&&url.pathname==='/api/v1/study/events'){
   const body=req.postDataJSON();posts.push(body);await new Promise(r=>setTimeout(r,650));
   if(failNext){failNext=false;failedEvent=body.eventId;return route.fulfill({status:503,json:{detail:'模拟网络失败'}});}
   return route.fulfill({json:{eventId:body.eventId,state:({start:'in_progress',pause:'paused',skip:'skipped'})[body.action]}});
  }
  if(req.method()!=='GET'){
   if(url.pathname.startsWith('/api/v1/drafts/')){draftWrites.push(req.postDataJSON());return route.fulfill({json:{rowVersion:2}});}
   return route.fulfill({json:{rowVersion:++resumeRevision}});
  }
  return route.continue();
 });
 const assert=(v,m)=>{if(!v)throw Error(m);};
 async function ready(n){await page.waitForFunction(id=>{const e=document.querySelector('#dictation-text');return e&&!e.readOnly&&e.value===`Draft for ${id}`;},sid(n));}
 async function begin(){await page.evaluate(()=>{window.__samples=[];window.__tracing=true;const measure=()=>{const root=document.querySelector('.draft-editor'),input=document.querySelector('#dictation-text'),action=[...root.querySelectorAll('button')].find(b=>b.textContent==='开始 / 恢复'),p=document.querySelector('.player-bar').getBoundingClientRect(),g=document.querySelector('.workspace-grid').getBoundingClientRect();return{opacity:getComputedStyle(action).opacity,disabled:action.disabled,inputDisabled:input.disabled,inputBackground:getComputedStyle(input).backgroundColor,toolbar:!!document.querySelector('.dictation-actions'),pendingText:root.textContent.includes('有一次待确认提交'),scroll:document.querySelector('.main-shell').scrollTop,gridX:g.x,playerY:p.y};};window.__baseline=measure();const tick=()=>{window.__samples.push(measure());if(window.__tracing)requestAnimationFrame(tick);};tick();});}
 async function finish(label){const data=await page.evaluate(()=>{window.__tracing=false;return{before:window.__baseline,samples:window.__samples};});assert(data.samples.length>10,label+' enough frames');assert(data.samples.every(s=>s.opacity==='1'&&!s.disabled&&!s.inputDisabled&&s.inputBackground==='rgb(255, 255, 255)'&&s.toolbar&&!s.pendingText),label+' no dim or missing controls');assert(data.samples.every(s=>s.gridX===data.before.gridX&&s.playerY===data.before.playerY),label+' shell stable');return{label,frames:data.samples.length,noDim:true,toolbarRetained:true};}
 for(const width of [1440,375]){
  await page.setViewportSize({width,height:900});await page.goto(`http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=dictation&sentence=${sid(1)}&english=1`);await ready(1);
  for(const n of [2,3,4,5,6,7,8,9,10,1]){
   const count=posts.length;await begin();await page.getByRole('button',{name:`选择句子 ${n}`,exact:true}).click();
   await page.waitForFunction(()=>document.querySelector('#dictation-text')?.readOnly);
   const b=page.getByRole('button',{name:'开始 / 恢复',exact:true});assert(await b.getAttribute('aria-disabled')==='true','Load aria guard');await b.evaluate(e=>e.click());await b.press('Enter');assert(posts.length===count,'Load mouse/keyboard cannot submit');
   await ready(n);await page.waitForTimeout(60);results.push({width,...await finish(`sentence ${n}`)});
  }
  await begin();const count=posts.length;await page.getByRole('button',{name:'暂停本轮',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.dictation-actions').getAttribute('aria-busy')==='true');
  await page.getByRole('button',{name:'跳过本句',exact:true}).evaluate(e=>e.click());await page.getByRole('button',{name:'开始 / 恢复',exact:true}).press('Enter');await page.waitForFunction(()=>document.querySelector('.dictation-actions').getAttribute('aria-busy')==='false');
  assert(posts.length===count+1,'Busy mouse/keyboard no duplicate');results.push({width,...await finish('pause request')});
  await page.screenshot({path:`docs/evidence/switch-flicker/stable-${width}.png`});
 }
 // Failure stays recoverable and reuses the original UUID; success does not flash a retry block.
 failNext=true;await page.getByRole('button',{name:'暂停本轮',exact:true}).click();await page.getByRole('button',{name:'重试同一次提交',exact:true}).waitFor();const failed=posts.at(-1).eventId;assert(failed===failedEvent,'Original failed event');
 await page.reload();await page.getByRole('button',{name:'重试同一次提交',exact:true}).waitFor();await page.getByRole('button',{name:'重试同一次提交',exact:true}).click();await page.getByRole('button',{name:'重试同一次提交',exact:true}).waitFor({state:'hidden'});await page.waitForFunction(()=>document.querySelector('.dictation-actions')?.getAttribute('aria-busy')==='false');assert(posts.at(-1).eventId===failed,'Retry preserves UUID');
 // Rapid requests must never install an earlier sentence's draft into the final target.
 for(const n of [2,3,4,1])await page.getByRole('button',{name:`选择句子 ${n}`,exact:true}).click();await ready(1);await page.waitForTimeout(700);assert(await page.locator('#dictation-text').inputValue()===`Draft for ${sid(1)}`,'Late responses stay isolated');
 for(const width of [1440,375]){
  await page.setViewportSize({width,height:900});await page.goto(`http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=speaking&sentence=${sid(1)}&english=1`);await page.getByText('本句尚无已保存录音。拒绝权限或跳过不会计为完成。',{exact:true}).waitFor();
  for(const n of [2,3]){
   await page.evaluate(()=>{window.__recordSamples=[];window.__recordTrace=true;const tick=()=>{const b=[...document.querySelectorAll('.recorder-panel button')].find(e=>e.textContent==='开始新录音');window.__recordSamples.push({opacity:getComputedStyle(b).opacity,disabled:b.disabled,waiting:b.getAttribute('aria-disabled')});if(window.__recordTrace)requestAnimationFrame(tick);};tick();});
   await page.getByRole('button',{name:`选择句子 ${n}`,exact:true}).click();const button=page.getByRole('button',{name:'开始新录音',exact:true});await page.waitForFunction(()=>document.querySelector('.recorder-panel')?.textContent.includes('正在读取记录'));
   await button.evaluate(e=>e.click());await page.waitForFunction(()=>document.querySelector('.recorder-panel')?.textContent.includes('本句尚无已保存录音。'));const samples=await page.evaluate(()=>{window.__recordTrace=false;return window.__recordSamples;});
   assert(samples.length>10&&samples.every(s=>s.opacity==='1'&&!s.disabled),'Recorder target switch no dim');assert(samples.some(s=>s.waiting==='true'),'Recorder loading guard');assert(await page.getByRole('button',{name:'停止并保存',exact:true}).isDisabled(),'Loading click must not start capture');results.push({width,label:`recording sentence ${n}`,frames:samples.length,noDim:true});
  }
 }
 assert(draftWrites.length===0,'Switching never writes a fixture draft to another target');assert(!errors.length,errors.join(';'));
 return{passed:true,results,failedRetrySameEvent:true,rapidTargetIsolation:true,draftWrites:draftWrites.length,mockedStudyCommands:posts.length,pageErrors:errors};
}
