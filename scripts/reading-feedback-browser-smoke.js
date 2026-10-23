// Delay/mock study-event responses and block all other writes; never mutate main DB.
async page => {
 page.setDefaultTimeout(10000);
 const errors=[],requests=[],checks=[];let reading=null,release,arrived,delay=false,fail=false;
 const assert=(ok,message)=>{if(!ok)throw new Error(message);};
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),url=new URL(req.url());
  if(req.method()==='GET'&&url.pathname==='/api/v1/reading'){
   if(!reading)reading=await(await route.fetch()).json();
   return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reading)});
  }
  if(req.method()==='POST'&&/\/reading\/[^/]+\/events$/.test(url.pathname)){
   const body=req.postDataJSON();requests.push(body);
   if(fail){fail=false;return route.fulfill({status:503,contentType:'application/problem+json',body:JSON.stringify({detail:'测试阅读操作保存失败'})});}
   if(delay){delay=false;const hold=new Promise(resolve=>release=resolve);arrived();await hold;}
   reading.questions[0].state=({skip:'skipped',pause:'paused',start:'in_progress'})[body.action];
   return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({eventId:body.eventId,state:reading.questions[0].state})});
  }
  return ['GET','HEAD'].includes(req.method())?route.continue():route.abort('blockedbyclient');
 });
 for(const width of [1440,375]) {
  reading=null;await page.setViewportSize({width,height:900});
  await page.goto('http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=vocabulary&english=1&sentence=demo-01-v2-s10');
  const region=page.locator('.reading-question'),skip=region.getByRole('button',{name:'跳过本轮',exact:true});
  await skip.waitFor();await page.waitForFunction(()=>document.querySelector('.reading-question fieldset')?.disabled===false);
  await region.evaluate(el=>el.scrollIntoView({block:'center',behavior:'instant'}));
  // Keep original nodes in the browser to detect remounts, and compare relative
  // geometry so automatic scroll anchoring cannot disguise a layout change.
  await region.evaluate(el=>{window.readingNodes=[el.querySelector('fieldset'),...el.querySelectorAll('.toolbar button'),el.querySelector('.reading-history')];});
  const layout=()=>region.evaluate(el=>({historyY:el.querySelector('.reading-history').getBoundingClientRect().top-el.getBoundingClientRect().top,height:el.getBoundingClientRect().height,opacities:[...el.querySelectorAll('input,.toolbar button')].map(b=>getComputedStyle(b).opacity),selected:[...el.querySelectorAll('input')].map(b=>b.checked),disabled:[...el.querySelectorAll('.toolbar button')].map(b=>b.disabled),fieldsetDisabled:el.querySelector('fieldset').disabled}));
  const before=await layout(),count=reading.questions[0].history.length,offset=requests.length;
  assert((await region.locator('.reading-save-status').innerText()).trim()==='','Idle status should be blank');
  const arrival=new Promise(resolve=>arrived=resolve);delay=true;await skip.click();await arrival;
  assert(await region.getAttribute('aria-busy')==='true','Busy signal');
  const during=await layout();
  assert(JSON.stringify(before)===JSON.stringify(during),'Pending changed geometry, opacity, disabled styling or choices: '+JSON.stringify({before,during}));
  await region.getByRole('button',{name:'开始 / 恢复',exact:true}).evaluate(b=>b.click());
  await skip.evaluate(b=>{b.click();b.click();});
  await region.locator('input').first().evaluate(b=>b.click());
  await region.locator('input').first().focus();await page.keyboard.press('ArrowDown');
  assert(JSON.stringify((await layout()).selected)===JSON.stringify(before.selected),'Locked choices changed');
  assert(requests.length===offset+1,'Duplicate action during pending');
  await page.screenshot({path:`docs/evidence/reading-feedback/pending-${width}.png`});
  release();await page.waitForFunction(()=>document.querySelector('.reading-question')?.getAttribute('aria-busy')==='false');
  assert(reading.questions[0].history.length===count,'Skip changed practice history');
  assert(await region.evaluate(el=>window.readingNodes.every((node,i)=>node===[el.querySelector('fieldset'),...el.querySelectorAll('.toolbar button'),el.querySelector('.reading-history')][i])),'Reading area remounted');
  // A failed command stays queued. Other controls must not implicitly retry it.
  fail=true;await region.getByRole('button',{name:'暂停本轮',exact:true}).click();
  await region.getByRole('button',{name:'重试原提交',exact:true}).waitFor();
  const failedEvent=requests.at(-1).eventId,failedCount=requests.length;
  await skip.evaluate(b=>b.click());assert(requests.length===failedCount,'Uncertain command retried via another action');
  await region.getByRole('button',{name:'重试原提交',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.reading-question')?.getAttribute('aria-busy')==='false');
  assert(requests.at(-1).eventId===failedEvent,'Explicit retry lost event ID');
  assert(!await region.getByRole('button',{name:'重试原提交',exact:true}).count(),'Pending not cleared');
  assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Overflow');
  checks.push({width,stableGeometry:true,stableOpacity:true,sameNodes:true,duplicateGuard:true,explicitRetrySameEvent:true});
 }
 assert(errors.length===0,errors.join(';'));
 return {passed:true,checks,pageErrors:errors};
}
