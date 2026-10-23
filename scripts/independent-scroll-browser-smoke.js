async page=>{
 const errors=[],results=[];let writes=0;page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/v1/**',route=>{if(route.request().method()==='GET')return route.continue();writes++;return route.fulfill({json:{}});});
 const url='http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=text&sentence=demo-01-v2-s01&english=1';
 const assert=(v,m)=>{if(!v)throw Error(m);};
 const measure=()=>page.evaluate(()=>{const side=document.querySelector('.sidebar'),main=document.querySelector('.main-shell'),player=document.querySelector('.player-bar'),r=side.getBoundingClientRect(),p=player.getBoundingClientRect();return{window:scrollY,side:side.scrollTop,main:main.scrollTop,sideY:r.y,sideHeight:r.height,viewport:innerHeight,playerY:p.y,playerBottom:p.bottom,overflow:document.documentElement.scrollWidth>innerWidth};});
 for(const [width,height] of [[1440,900],[1280,600],[979,400],[375,900],[375,500]]){
  await page.setViewportSize({width,height});await page.goto(url);await page.locator('.sentence-list').waitFor();await page.waitForTimeout(100);
  await page.locator('.main-shell').evaluate(el=>el.scrollTop=0);const before=await measure();
  await page.mouse.move(width-120,height/2);await page.mouse.wheel(0,600);await page.waitForTimeout(250);const after=await measure();
  assert(after.main>0,'Right pane scrolls');assert(after.window===0&&after.side===before.side&&after.sideY===before.sideY,'Right scroll leaves left and window fixed');assert(!after.overflow,'No horizontal overflow');assert(after.playerY===before.playerY&&after.playerBottom===height,'Player fixed');
  if(width>640)assert(after.sideHeight===height,'Left pane fills viewport');
  await page.locator('.main-shell').evaluate(el=>el.scrollTop=el.scrollHeight);const end=await measure();await page.mouse.wheel(0,1800);await page.waitForTimeout(150);const bottom=await measure();assert(bottom.window===0&&bottom.sideY===before.sideY&&bottom.side===before.side,'No scroll chaining at bottom');
  if(width>640){
   const mainTop=bottom.main;await page.mouse.move(110,Math.min(height-30,350));await page.mouse.wheel(0,600);await page.waitForTimeout(200);const left=await measure();assert(left.main===mainTop&&left.window===0&&left.sideY===0,'Left scroll cannot move right pane');
   const scrollable=await page.locator('.sidebar').evaluate(el=>el.scrollHeight>el.clientHeight);if(scrollable)assert(left.side>0,'Short sidebar scrolls internally');
  }
  await page.screenshot({path:`docs/evidence/independent-scroll/scroll-${width}-${height}.png`});results.push({width,height,mainScroll:after.main,sidebarFixed:true,windowScroll:bottom.window,playerFixed:true});
 }
 await page.setViewportSize({width:1440,height:900});await page.goto(url);await page.locator('.sentence-list').waitFor();await page.locator('.main-shell').evaluate(el=>el.scrollTop=170);
 const beforeTab=await measure();await page.getByRole('tab',{name:'课时测验',exact:true}).click();await page.waitForTimeout(200);assert((await measure()).main===beforeTab.main,'Tab retains content scroll');
 await page.getByRole('link',{name:'课程中心',exact:false}).click();await page.waitForURL('**/courses');await page.waitForTimeout(150);assert((await page.locator('.main-shell').evaluate(el=>el.scrollTop))===0,'Route navigation resets pane');
 assert(!errors.length,errors.join(';'));return{passed:true,results,tabScrollPreserved:true,navigationReset:true,interceptedWrites:writes,pageErrors:errors};
}
