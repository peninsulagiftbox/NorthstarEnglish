// Open about:blank#<isolated-api-port>; all application API traffic stays on the verified test schema.
async page=>{
 const port=Number(new URL(page.url()).hash.slice(1)),base='http://127.0.0.1:3100',api=`http://127.0.0.1:${port}`;
 if(!Number.isInteger(port)||port<1024||port>65535)throw Error('Provide isolated API port in initial URL fragment');
 if((await page.request.get(api+'/api/v1/health')).headers()['x-northstar-test-database']!=='true')throw Error('Require isolated test database');
 const errors=[],results=[];page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push(e.message));let lose=false,lastEvent='',playbackPosts=0;
 await page.route('**/api/v1/**',async route=>{
  const url=new URL(route.request().url());const response=await route.fetch({url:api+url.pathname+url.search});
  if(route.request().method()==='POST'&&url.pathname.endsWith('/playbacks')){playbackPosts++;lastEvent=route.request().postDataJSON().eventId;await new Promise(r=>setTimeout(r,800));if(lose){lose=false;return route.abort('failed');}}
  await route.fulfill({response});
 });
 const ctx='lessonId=demo-01&versionId=demo-01-v2&sentenceId=demo-01-v2-s05',url=base+'/lesson/demo-01?version=demo-01-v2&tab=speaking&sentence=demo-01-v2-s05&english=1';
 const recordings=async()=> (await(await page.request.get(api+'/api/v1/recordings?'+ctx)).json()).recordings;
 const id=(await recordings()).find(r=>r.status==='ready')?.id;if(!id)throw Error('Existing fake-microphone test recording required');
 const selector=`audio[src="/api/v1/recordings/${id}/audio"]`,audio=page.locator(selector);
 for(const width of [1440,375]){
  await page.setViewportSize({width,height:900});await page.goto(url);await audio.waitFor();await audio.scrollIntoViewIfNeeded();await page.waitForTimeout(100);
  const before=(await recordings()).find(r=>r.id===id).playbackCount;
  await page.evaluate(selector=>{
   const measure=()=>{const rect=document.querySelector(selector).closest('li').getBoundingClientRect(),grid=document.querySelector('.workspace-grid').getBoundingClientRect();return{scroll:scrollY,y:rect.y,x:rect.x,documentY:rect.y+scrollY,height:rect.height,gridY:grid.y,retry:!!Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='重试待确认操作')};};
   window.__playSamples=[];window.__playTrace=true;window.__playBefore=measure();const tick=()=>{window.__playSamples.push(measure());if(window.__playTrace)requestAnimationFrame(tick);};tick();
  },selector);
  await audio.click({position:{x:30,y:27}});await page.waitForFunction(selector=>!document.querySelector(selector).paused,selector);await page.waitForTimeout(2100);await audio.evaluate(a=>a.pause());
  const measured=await page.evaluate(()=>{window.__playTrace=false;return{before:window.__playBefore,samples:window.__playSamples};});
  const drift=Math.max(...measured.samples.map(s=>Math.abs(s.documentY-measured.before.documentY))),scrollDrift=Math.max(...measured.samples.map(s=>Math.abs(s.scroll-measured.before.scroll)));
  if(drift>1||scrollDrift>1||measured.samples.some(s=>s.retry||Math.abs(s.height-measured.before.height)>1))throw Error(JSON.stringify({width,drift,scrollDrift,retry:measured.samples.some(s=>s.retry)}));
  if((await recordings()).find(r=>r.id===id).playbackCount!==before+1)throw Error('Actual playback not saved exactly once');
  results.push({width,cardDrift:drift,scrollDrift,retryFlashed:false,countIncreased:1});
  await page.screenshot({path:`docs/evidence/play-jump/playing-stable-${width}.png`});
 }
 // A real failure must still expose the original event for safe retry after refresh.
 const before=(await recordings()).find(r=>r.id===id).playbackCount;lose=true;
 await audio.evaluate(a=>{a.currentTime=0;});await audio.click({position:{x:30,y:27}});await page.getByRole('alert').filter({hasText:'暂时无法连接'}).waitFor();await audio.evaluate(a=>a.pause());await page.getByRole('button',{name:'重试待确认操作',exact:true}).waitFor();const failedEvent=lastEvent;
 if((await recordings()).find(r=>r.id===id).playbackCount!==before+1)throw Error('Accepted response-loss count');
 await page.reload();await page.getByRole('button',{name:'重试待确认操作',exact:true}).waitFor();await page.getByRole('button',{name:'重试待确认操作',exact:true}).click();await page.getByRole('button',{name:'重试待确认操作',exact:true}).waitFor({state:'hidden'});
 await page.waitForTimeout(1000);if(lastEvent!==failedEvent||(await recordings()).find(r=>r.id===id).playbackCount!==before+1)throw Error('Original event retry duplicated or lost');
 if(errors.length)throw Error(errors.join(';'));return{passed:true,results,responseLossRetrySameEvent:true,playbackPosts,pageErrors:errors};
}
