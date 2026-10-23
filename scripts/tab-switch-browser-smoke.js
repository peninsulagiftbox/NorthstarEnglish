async page=>{
 const errors=[],results=[];page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));let blockedWrites=0;
 await page.route('**/api/v1/**',route=>{if(!['GET','HEAD'].includes(route.request().method())){blockedWrites++;return route.abort();}return route.continue();});
 // Deliberately slow only data reads, exposing the loading frame without changing returned data.
 for(const path of ['reading','writing','recordings'])await page.route(`**/api/v1/${path}?*`,async route=>{await new Promise(r=>setTimeout(r,400));await route.continue();});
 const url='http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=vocabulary&sentence=demo-01-v2-s10&english=1';
 for(const width of [1440,1280,979,375]){
  await page.setViewportSize({width,height:900});await page.goto(url);await page.locator('.vocabulary-card').first().waitFor();
  const positions=width===375?[0,180]:[0,120,180];
  for(const position of positions){
   await page.evaluate(y=>scrollTo(0,y),position);await page.waitForTimeout(80);
   await page.evaluate(()=>{
    const measure=()=>{const r=document.querySelector('.workspace-grid').getBoundingClientRect(),t=document.querySelector('.tutor-desktop').getBoundingClientRect();return{scroll:scrollY,gridX:r.x,gridY:r.y,gridWidth:r.width,tutorX:t.x,tutorY:t.y,viewport:document.documentElement.clientWidth,overflow:document.documentElement.scrollWidth>innerWidth,cardHeight:document.querySelector('.lesson-card').getBoundingClientRect().height};};
    window.__tabSamples=[];window.__tabTrace=true;window.__tabBaseline=measure();const tick=()=>{window.__tabSamples.push(measure());if(window.__tabTrace)requestAnimationFrame(tick);};tick();
   });
   for(const name of ['口语跟读','写作','课时测验','精读词汇']){await page.getByRole('tab',{name,exact:true}).click();await page.waitForTimeout(700);}
   const data=await page.evaluate(()=>{window.__tabTrace=false;return{before:window.__tabBaseline,samples:window.__tabSamples};});
   const drift=Math.max(...data.samples.map(s=>Math.abs(s.scroll-data.before.scroll))),gridDrift=Math.max(...data.samples.map(s=>Math.abs(s.gridY-data.before.gridY))),xDrift=Math.max(...data.samples.map(s=>Math.abs(s.gridX-data.before.gridX)));
   if(drift>1||gridDrift>1||xDrift>1||data.samples.some(s=>s.overflow||Math.abs(s.gridWidth-data.before.gridWidth)>1))throw Error(JSON.stringify({width,position,drift,gridDrift,xDrift}));
   results.push({width,position,samples:data.samples.length,scrollDrift:drift,gridDrift,xDrift});
  }
 }
 await page.setViewportSize({width:1440,height:900});await page.evaluate(()=>scrollTo(0,180));await page.getByRole('tab',{name:'课时测验',exact:true}).click();await page.waitForFunction(()=>document.querySelector('[role=tab][aria-selected=true]')?.id==='tab-quiz');await page.screenshot({path:'docs/evidence/tab-jump/quiz-stable-1440.png'});
 await page.getByRole('tab',{name:'精读词汇',exact:true}).click();await page.locator('.vocabulary-card').first().waitFor();await page.screenshot({path:'docs/evidence/tab-jump/vocabulary-stable-1440.png'});
 if(errors.length)throw Error(errors.join(';'));return{passed:true,results,readDelayMs:400,blockedWrites,pageErrors:errors};
}
