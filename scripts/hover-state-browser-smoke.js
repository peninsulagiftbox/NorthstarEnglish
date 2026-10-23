// Check real hover/press rendering; intercept writes and use practice fixtures.
async page=>{
 const results=[],errors=[];let writes=0;page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/v1/**',route=>{
  const req=route.request(),url=new URL(req.url());
  if(req.method()!=='GET'){writes++;if(url.pathname.endsWith('/favorite'))return route.fulfill({json:{favorite:req.postDataJSON().favorite}});return route.fulfill({json:{}});}
  if(url.pathname==='/api/v1/writing')return route.fulfill({json:{taskId:'hover-fixture',prompt:'Write a short reply.',sourceSentenceIds:[],draft:{text:'A local fixture draft.',rowVersion:1},state:'in_progress',revisions:[]}});
  if(url.pathname==='/api/v1/recordings')return route.fulfill({json:{state:'in_progress',recordings:[{id:'hover-fixture',mimeType:'audio/webm',durationMs:5000,status:'missing',createdAt:'2026-10-23T10:00:00Z',playbackCount:0}]}});
  return route.continue();
 });
 const assert=(v,m)=>{if(!v)throw Error(m);};
 const read=el=>el.evaluate(e=>{const s=getComputedStyle(e);return{bg:s.backgroundColor,color:s.color,opacity:s.opacity,pressed:e.getAttribute('aria-pressed'),selected:e.getAttribute('aria-selected')};});
 const contrast=s=>{const rgb=c=>(c.match(/[\d.]+/g)||[]).map(Number),bg=rgb(s.bg),fg=rgb(s.color);if(bg.length===4&&bg[3]<1)return null;const l=v=>{const x=v.slice(0,3).map(n=>{n/=255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;});return x[0]*.2126+x[1]*.7152+x[2]*.0722;};return(Math.max(l(bg),l(fg))+.05)/(Math.min(l(bg),l(fg))+.05);};
 async function check(el,label,{stable=false,dark=false,activeMayChange=false}={}){
  await el.scrollIntoViewIfNeeded();await page.mouse.move(3,3);const before=await read(el);await el.hover();const hover=await read(el);
  await el.evaluate(e=>e.addEventListener('click',event=>{event.preventDefault();event.stopImmediatePropagation();},{once:true,capture:true}));
  await page.mouse.down();const active=await read(el);await page.mouse.up();await page.mouse.move(3,3);
  for(const [state,s] of Object.entries({before,hover,active})){const ratio=contrast(s);assert(ratio===null||ratio>=4.5,`${label} ${state} contrast ${ratio}: ${JSON.stringify(s)}`);if(stable&&!(activeMayChange&&state==='active'))assert(s.bg===before.bg&&s.color===before.color,`${label} loses selection in ${state}`);if(dark)assert(s.bg.startsWith('rgba('),`${label} loses dark banner background`);}
  return{label,before,hover,active};
 }
 for(const width of [1440,375]){
  await page.setViewportSize({width,height:900});
  for(const path of ['/dashboard','/courses','/review','/reports','/settings']){
   await page.goto('http://127.0.0.1:3100'+path);await page.waitForTimeout(250);
   if(path==='/dashboard'||path==='/courses'){await page.locator('.hero-secondary').waitFor();await check(page.locator('.hero-secondary'),`${path} hero`,{dark:true});await check(page.locator('.hero-actions .primary'),`${path} primary`);}
   const controls=page.locator('main button,main a.button');let checked=0;
   for(let i=0;i<await controls.count();i++){const el=controls.nth(i);if(await el.isVisible()&&await el.isEnabled()){await check(el,`${path} control ${i}`);checked++;}}
   results.push({width,page:path,checked});
  }
  for(const tab of ['text','dictation','vocabulary','speaking','writing','quiz']){
   await page.goto(`http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=${tab}&sentence=demo-01-v2-s03&english=1`);await page.getByRole('tab',{selected:true}).waitFor();
   await check(page.getByRole('tab',{selected:true}),`${tab} selected tab`,{stable:true});
   if(tab==='text')await check(page.locator('.sentence.selected'),`${tab} selected sentence`,{stable:true});
   else await check(page.locator('.sentence-picker [aria-pressed=true]'),`${tab} selected picker`,{stable:true});
   const controls=page.locator('.lesson-card .button:not(:disabled)');let checked=0;
   for(let i=0;i<await controls.count();i++){const el=controls.nth(i);if(await el.isVisible()){await check(el,`${tab} button ${i}`);checked++;}}
   await check(page.locator('.play-button'),'player play');
   await page.getByRole('button',{name:'播放设置',exact:true}).click();await check(page.locator('.player-bar [aria-expanded=true]'),'expanded player settings',{stable:true,activeMayChange:true});await page.getByRole('button',{name:'关闭',exact:true}).click();
   if(tab==='vocabulary'){
    const favorite=page.locator('.vocabulary-favorite').first();if(await favorite.getAttribute('aria-pressed')!=='true')await favorite.click();await page.waitForFunction(()=>document.querySelector('.vocabulary-favorite').getAttribute('aria-pressed')==='true');await check(favorite,'selected favorite',{stable:true});
   }
   if(tab==='speaking'){
    await page.getByRole('button',{name:'删除这段录音',exact:true}).click();await check(page.getByRole('dialog').locator('.button.danger'),'modal danger');await check(page.getByRole('dialog').getByRole('button',{name:'取消',exact:true}),'modal cancel');await page.keyboard.press('Escape');
   }
   if(tab==='writing'){await page.locator('.sentence-picker [aria-pressed=true]').hover();await page.screenshot({path:`docs/evidence/hover-states/writing-${width}.png`});}
   results.push({width,page:tab,checked,selectedPreserved:true});
  }
 }
 assert(!errors.length,errors.join(';'));return{passed:true,results,interceptedWrites:writes,pageErrors:errors};
}
