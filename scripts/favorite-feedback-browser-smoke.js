// Favorite responses are deliberately delayed/mocked; all other writes are blocked.
// This checks UI request isolation without modifying the main learning database.
async page => {
 page.setDefaultTimeout(10000);
 const errors=[],requests=[],gates=new Map(),arrivals=[];
 let auto=false,failId='';
 const assert=(ok,message)=>{if(!ok)throw new Error(message);};
 const nextArrival=()=>new Promise(resolve=>arrivals.push(resolve));
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/v1/**',async route=>{
  const req=route.request();
  if(req.method()==='PUT'&&req.url().includes('/knowledge/')&&req.url().endsWith('/favorite')) {
   const id=new URL(req.url()).pathname.split('/').at(-2),body=req.postDataJSON();requests.push({id,...body});
   if(id===failId)return route.fulfill({status:503,contentType:'application/problem+json',body:JSON.stringify({detail:'测试收藏保存失败'})});
   if(!auto){let release;const hold=new Promise(resolve=>release=resolve);gates.set(id,release);arrivals.shift()?.();await hold;}
   return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({favorite:body.favorite})});
  }
  return ['GET','HEAD'].includes(req.method())?route.continue():route.abort('blockedbyclient');
 });
 await page.setViewportSize({width:1440,height:900});
 await page.goto('http://127.0.0.1:3100/lesson/demo-01?tab=vocabulary&english=1&version=demo-01-v2&sentence=demo-01-v2-s10');
 const buttons=page.locator('.vocabulary-favorite');await buttons.first().waitFor();
 const originals=await buttons.evaluateAll(bs=>bs.map(b=>b.getAttribute('aria-pressed')));
 await page.evaluate(()=>{
  window.favoriteNodes=[...document.querySelectorAll('.vocabulary-favorite')];window.favoriteMutations=[];
  window.favoriteObserver=new MutationObserver(rows=>rows.forEach(row=>window.favoriteMutations.push({index:window.favoriteNodes.indexOf(row.target),attribute:row.attributeName})));
  window.favoriteNodes.forEach(b=>window.favoriteObserver.observe(b,{attributes:true}));
 });
 let arrived=nextArrival();await buttons.nth(0).click();await arrived;
 const first=await buttons.evaluateAll(bs=>bs.map(b=>({disabled:b.disabled,busy:b.getAttribute('aria-busy'),opacity:getComputedStyle(b).opacity})));
 assert(first[0].disabled&&first[0].busy==='true','Only clicked word pending');
 assert(first.slice(1).every(b=>!b.disabled&&b.opacity==='1'),'Other favorites must not dim/disable');
 await buttons.nth(0).evaluate(b=>{b.click();b.click();});assert(requests.length===1,'No duplicate request for pending word');
 arrived=nextArrival();await buttons.nth(1).click();await arrived;
 assert(await buttons.evaluateAll(bs=>bs.slice(2).every(b=>!b.disabled&&getComputedStyle(b).opacity==='1')),'Other favorites remain stable during concurrent requests');
 await page.screenshot({path:'docs/evidence/favorite-feedback/concurrent-pending.png'});
 // Resolve the second word first to exercise independent state updates.
 gates.get(requests[1].id)();
 await page.waitForFunction(expected=>document.querySelectorAll('.vocabulary-favorite')[1]?.getAttribute('aria-pressed')===expected,originals[1]==='true'?'false':'true');
 assert(await buttons.nth(0).isDisabled(),'First pending lock retained');
 gates.get(requests[0].id)();
 await page.waitForFunction(expected=>document.querySelectorAll('.vocabulary-favorite')[0]?.getAttribute('aria-pressed')===expected,originals[0]==='true'?'false':'true');
 await page.waitForFunction(()=>[...document.querySelectorAll('.vocabulary-favorite')].every(b=>!b.disabled));
 const mutations=await page.evaluate(()=>({rows:window.favoriteMutations,sameNodes:window.favoriteNodes.every((node,i)=>node===document.querySelectorAll('.vocabulary-favorite')[i])}));
 assert(mutations.sameNodes&&mutations.rows.every(row=>row.index===0||row.index===1),'Unrelated favorite DOM attributes changed');
 auto=true;failId='demo-01-v2-kp-beside';
 await page.getByRole('button',{name:'收藏 beside',exact:true}).click();await page.getByRole('button',{name:'重新读取收藏',exact:true}).waitFor();
 const failed=await buttons.evaluateAll(bs=>bs.map(b=>({name:b.getAttribute('aria-label'),disabled:b.disabled,opacity:getComputedStyle(b).opacity})));
 assert(failed.every(b=>b.name==='收藏 beside'?b.disabled:!b.disabled&&b.opacity==='1'),'Error affects only failed word');
 const healthy=page.getByRole('button',{name:'收藏 watering can',exact:true}),previous=await healthy.getAttribute('aria-pressed');
 await healthy.click();await page.waitForFunction(expected=>document.querySelector('[aria-label="收藏 watering can"]')?.getAttribute('aria-pressed')===expected,previous==='true'?'false':'true');
 assert(await page.getByRole('button',{name:'收藏 beside',exact:true}).isDisabled(),'Uncertain word stays blocked until reload');
 await page.evaluate(()=>window.favoriteObserver.disconnect());
 await page.getByRole('button',{name:'重新读取收藏',exact:true}).click();await buttons.first().waitFor();
 assert(await buttons.evaluateAll(bs=>bs.every(b=>!b.disabled)),'Explicit reload clears uncertain state');
 assert(new URL(page.url()).searchParams.get('sentence')==='demo-01-v2-s10','Favorite must not select source');
 assert(errors.length===0,errors.join(';'));
 return {passed:true,checks:['Only target dims/busy; other favorites keep opacity and DOM attributes','Concurrent different-word saves, duplicate guard and reverse response order','Failure scoped to one word; healthy words remain usable; explicit reload clears error'],requests:requests.length,unrelatedMutations:0,pageErrors:errors};
}
