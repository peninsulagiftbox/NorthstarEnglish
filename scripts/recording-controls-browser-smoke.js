// Start on about:blank#<isolated-api-port>. No traffic is sent to the main learning API.
async page=>{
 const port=Number(new URL(page.url()).hash.slice(1)),base='http://127.0.0.1:3100',api=`http://127.0.0.1:${port}`;
 if(!Number.isInteger(port)||port<1024)throw Error('Provide isolated API port');
 if((await page.request.get(api+'/api/v1/health')).headers()['x-northstar-test-database']!=='true')throw Error('Require isolated schema');
 const errors=[],results=[];let commandPosts=0;page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/v1/**',async route=>{const u=new URL(route.request().url()),response=await route.fetch({url:api+u.pathname+u.search});if(route.request().method()==='POST'&&(u.pathname.endsWith('/events')||u.pathname.endsWith('/playbacks')||u.pathname.endsWith('/ratings'))){commandPosts++;await new Promise(r=>setTimeout(r,800));}await route.fulfill({response});});
 const get=async()=> (await(await page.request.get(api+'/api/v1/recordings?lessonId=demo-01&versionId=demo-01-v2&sentenceId=demo-01-v2-s05')).json());
 const id=(await get()).recordings.find(r=>r.status==='ready')?.id;if(!id)throw Error('Need fake-microphone test recording');
 const audio=page.locator(`audio[src="/api/v1/recordings/${id}/audio"]`),card=page.locator('.recording-list li').filter({has:audio});
 const begin=async()=>page.evaluate(()=>{
  const buttons=Array.from(document.querySelectorAll('.recorder-panel button')),audio=document.querySelector('.recording-list audio'),list=document.querySelector('.recording-list');
  const read=()=>({scroll:scrollY,listY:list.getBoundingClientRect().y+scrollY,buttons:buttons.map(b=>({opacity:getComputedStyle(b).opacity,y:b.getBoundingClientRect().y+scrollY,disabled:b.disabled}))});
  window.__controlBefore=read();window.__controlSamples=[];window.__controlsTrace=true;window.__audioBefore=audio;window.__disabledChanges=0;window.__loads=0;audio.addEventListener('loadstart',window.__loadListener=()=>window.__loads++);
  window.__controlObserver=new MutationObserver(ms=>window.__disabledChanges+=ms.length);window.__controlObserver.observe(document.querySelector('.recorder-panel'),{subtree:true,attributes:true,attributeFilter:['disabled']});
  const tick=()=>{window.__controlSamples.push(read());if(window.__controlsTrace)requestAnimationFrame(tick);};tick();
 });
 const end=async(name,width)=>{
  const result=await page.evaluate(()=>{window.__controlsTrace=false;window.__controlObserver.disconnect();window.__audioBefore.removeEventListener('loadstart',window.__loadListener);const b=window.__controlBefore,s=window.__controlSamples;return{buttonOpacityChanged:s.some(v=>v.buttons.some((x,i)=>x.opacity!==b.buttons[i].opacity)),cardDrift:Math.max(...s.map(v=>Math.abs(v.listY-b.listY))),scrollDrift:Math.max(...s.map(v=>Math.abs(v.scroll-b.scroll))),buttonDrift:Math.max(...s.flatMap(v=>v.buttons.map((x,i)=>Math.abs(x.y-b.buttons[i].y)))),disabledMutations:window.__disabledChanges,audioSameNode:window.__audioBefore===document.querySelector('.recording-list audio'),extraLoads:window.__loads};});
  if(result.buttonOpacityChanged||result.cardDrift>1||result.scrollDrift>1||result.buttonDrift>1||result.disabledMutations||!result.audioSameNode||result.extraLoads)throw Error(JSON.stringify({name,width,...result}));results.push({name,width,...result});
 };
 for(const width of [1440,375]){
  await page.setViewportSize({width,height:900});await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=speaking&sentence=demo-01-v2-s05&english=1');await audio.waitFor();await page.waitForFunction(()=>document.querySelector('.recording-list audio')?.readyState>=1);
  await page.getByRole('button',{name:'暂停跟读',exact:true}).evaluate(e=>e.scrollIntoView({block:'center'}));await page.waitForTimeout(80);await begin();const posts=commandPosts;
  await page.getByRole('button',{name:'暂停跟读',exact:true}).click();await page.waitForFunction(()=>Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='暂停跟读')?.getAttribute('aria-disabled')==='true');
  await page.evaluate(()=>{Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='删除这段录音').click();const b=Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='暂时跳过跟读');b.focus();});await page.keyboard.press('Enter');
  if(await page.getByRole('dialog').count())throw Error('Transient lock allowed deletion dialog');
  await page.waitForFunction(()=>Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='暂停跟读')?.getAttribute('aria-disabled')!=='true');if(commandPosts!==posts+1)throw Error('Transient lock did not guard repeat/keyboard operations');await end('pause / blocked conflicting clicks',width);
  await begin();await page.getByRole('button',{name:'暂时跳过跟读',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.recorder-panel')?.textContent.includes('本轮已跳过'));await end('skip',width);
  await audio.evaluate(e=>e.scrollIntoView({block:'center'}));await page.waitForTimeout(80);await begin();const count=(await get()).recordings.find(r=>r.id===id).playbackCount;
  await audio.click({position:{x:30,y:27}});await page.waitForTimeout(2100);await audio.evaluate(a=>a.pause());if((await get()).recordings.find(r=>r.id===id).playbackCount!==count+1)throw Error('Actual playback count');await end('native playback / automatic save',width);
  await card.getByRole('button',{name:'人工自评：本次满意',exact:true}).evaluate(e=>e.scrollIntoView({block:'center'}));await page.waitForTimeout(80);await begin();await card.getByRole('button',{name:'人工自评：本次满意',exact:true}).click();await page.locator('.recorder-panel>.toast').waitFor();if(await page.locator('.recorder-panel>.toast').evaluate(e=>getComputedStyle(e).position)!=='fixed')throw Error('Rating feedback participates in page layout');await page.screenshot({path:`docs/evidence/recording-click/feedback-${width}.png`});await page.locator('.recorder-panel>.toast').waitFor({state:'hidden'});await end('rating toast enter/exit',width);
  if((await get()).recordings.find(r=>r.id===id).playbackCount!==count+1)throw Error('Rating added a playback');
 }
 if(errors.length)throw Error(errors.join(';'));return{passed:true,results,requestDelayMs:800,duplicateAndKeyboardGuardPassed:true,pageErrors:errors};
}
