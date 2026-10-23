async page=>{
 page.setDefaultTimeout(15000);const base=new URL(page.url()).origin,errors=[],checks=[];page.on('pageerror',e=>errors.push(e.message));
 const assert=(v,m)=>{if(!v)throw Error(m);};assert((await page.request.get(base+'/api/v1/health')).headers()['x-northstar-test-database']==='true','Require isolated database before any writes');
 const ctx='lessonId=demo-01&versionId=demo-01-v2&sentenceId=demo-01-v2-s05';
 const get=async()=> (await(await page.request.get(base+'/api/v1/recordings?'+ctx)).json()).recordings;
 const initial=await get(),recording=initial.find(r=>r.status==='ready');assert(!!recording,'Use prior fake-microphone test recording, never private main audio');const id=recording.id,before=recording.playbackCount;
 let posts=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith(`/recordings/${id}/playbacks`))posts++;});
 await page.setViewportSize({width:1440,height:900});await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=speaking&sentence=demo-01-v2-s05&english=1');
 const audio=page.locator(`audio[src="/api/v1/recordings/${id}/audio"]`),card=page.locator('.recording-list li').filter({has:audio});await audio.waitFor();
 await audio.evaluate(a=>{a.currentTime=.3;});await page.waitForTimeout(350);assert((await get()).find(r=>r.id===id).playbackCount===before,'Seek alone creates no observation');
 await audio.evaluate(async a=>{a.currentTime=0;await a.play();});
 await page.waitForFunction(({id,n})=>Array.from(document.querySelectorAll('.recording-list li')).find(li=>li.querySelector(`audio[src="/api/v1/recordings/${id}/audio"]`))?.textContent.includes(`已回放 ${n} 次`),{id,n:before+1});
 await page.waitForTimeout(1000);await audio.evaluate(a=>a.pause());assert((await get()).find(r=>r.id===id).playbackCount===before+1 && posts===1,'Repeated timeupdates/ended count only once');
 await card.getByRole('button',{name:'人工自评：本次满意',exact:true}).click();await page.getByText('人工自评已保存，不增加回放次数。',{exact:true}).waitFor();assert((await get()).find(r=>r.id===id).playbackCount===before+1,'Rating does not add playback');
 await audio.evaluate(async a=>{a.currentTime=0;await a.play();});await page.waitForFunction(({id,n})=>Array.from(document.querySelectorAll('.recording-list li')).find(li=>li.querySelector(`audio[src="/api/v1/recordings/${id}/audio"]`))?.textContent.includes(`已回放 ${n} 次`),{id,n:before+2});await audio.evaluate(a=>a.pause());assert(posts===2,'A second real playback adds exactly one');
 await page.reload();await audio.waitFor();assert((await card.textContent()).includes(`已回放 ${before+2} 次`),'Count persists after refresh');checks.push('Automatic actual playback, seek exclusion, one per playback, replay increments, ratings separate, refresh persistence');
 for(const width of [1440,375]){
  await page.setViewportSize({width,height:900});await card.scrollIntoViewIfNeeded();
  const spacing=await card.evaluate(li=>{const r=li.querySelector('.recording-ratings').getBoundingClientRect(),d=li.querySelector('.recording-delete').getBoundingClientRect();return{gap:d.top-r.bottom,overflow:document.documentElement.scrollWidth>innerWidth};});assert(spacing.gap>=15.5&&!spacing.overflow,'Delete row spacing and no horizontal overflow');await page.screenshot({path:`docs/evidence/recording-playback/screenshots/buttons-${width}.png`});
 }
 await page.setViewportSize({width:1440,height:900});let lost=true,event='';await page.route(`**/api/v1/recordings/${id}/playbacks`,async route=>{if(!lost)return route.continue();lost=false;event=route.request().postDataJSON().eventId;const accepted=await route.fetch();assert(accepted.status()===200,'Playback accepted before lost receipt');await route.abort('failed');});
 await audio.evaluate(async a=>{a.currentTime=0;await a.play();});await page.getByRole('alert').filter({hasText:'暂时无法连接'}).waitFor();await audio.evaluate(a=>a.pause());assert((await get()).find(r=>r.id===id).playbackCount===before+3,'Lost response accepted once');
 await page.reload();await page.getByRole('button',{name:'重试待确认操作',exact:true}).waitFor();await page.getByRole('button',{name:'重试待确认操作',exact:true}).click();await page.getByRole('button',{name:'重试待确认操作',exact:true}).waitFor({state:'hidden'});assert((await get()).find(r=>r.id===id).playbackCount===before+3,'Original UUID retry cannot duplicate');
 checks.push('16px separation at 1440/375, lost automatic receipt retained across reload and idempotent retry');assert(!errors.length,'No page errors '+errors.join(';'));return{passed:true,checks,initialCount:before,finalCount:before+3,playbackEvent:event,pageErrors:errors};
}
