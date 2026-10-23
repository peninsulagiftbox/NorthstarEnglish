async page => {
 const errors=[], checks=[];let writes=0;
 page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(10000);
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),url=new URL(req.url());
  if(req.method()!=='GET'){writes++;if(url.pathname.endsWith('/delete'))await new Promise(resolve=>setTimeout(resolve,800));return route.fulfill({status:200,json:{}});}
  if(url.pathname==='/api/v1/recordings')return route.fulfill({json:{state:'in_progress',recordings:[{id:'modal-fixture',mimeType:'audio/webm',durationMs:5000,byteSize:100,status:'missing',createdAt:'2026-10-23T10:48:14Z',playbackCount:3}]}});
  if(url.pathname==='/api/v1/writing')return route.fulfill({json:{taskId:'fixture',prompt:'Write a short reply.',sourceSentenceIds:[],draft:{text:'Keep my current draft.',rowVersion:1},state:'in_progress',revisions:[{id:'fixture-revision',versionNo:1,text:'An older draft.',createdAt:'2026-10-23T10:48:14Z',parentRevisionId:null}]}});
  return route.continue();
 });
 const base='http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&sentence=demo-01-v2-s01&english=1&tab=';
 const assert=(v,m)=>{if(!v)throw Error(m);};
 for(const width of [1440,375,320]){
  await page.setViewportSize({width,height:900});await page.goto(base+'speaking');
  const trigger=page.getByRole('button',{name:'删除这段录音',exact:true});await trigger.click();
  const dialog=page.getByRole('dialog');await dialog.waitFor();
  assert(await page.getByRole('button',{name:'取消',exact:true}).evaluate(b=>b===document.activeElement),'Safe initial focus');
  assert(await dialog.evaluate(d=>{const r=d.getBoundingClientRect();return r.x>=0&&r.right<=innerWidth&&d.scrollWidth<=d.clientWidth;}),'Dialog fits');
  assert(await dialog.locator('.danger.button').evaluate(b=>getComputedStyle(b).backgroundColor==='rgb(180, 60, 60)'),'Danger variant');
  for(let i=0;i<8;i++){await page.keyboard.press('Tab');assert(await dialog.evaluate(d=>d.contains(document.activeElement)),'Focus stays in modal');}
  await dialog.click({position:{x:2,y:100}});assert(await dialog.isVisible(),'Inner edge must not dismiss');
  await page.screenshot({path:`docs/evidence/modal-redesign/delete-${width}.png`});
  await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});assert(await trigger.evaluate(b=>b===document.activeElement),'Focus restored');
  await trigger.click();await page.getByRole('button',{name:'取消',exact:true}).click();await dialog.waitFor({state:'hidden'});
  await trigger.click();await page.getByRole('button',{name:'关闭弹窗',exact:true}).click();await dialog.waitFor({state:'hidden'});
  await trigger.click();await page.mouse.click(3,3);await dialog.waitFor({state:'hidden'});
  checks.push(`${width}: fit, danger, focus trap/restore, Escape, Cancel, Close, backdrop, inner edge`);
 }
 await page.getByRole('button',{name:'删除这段录音',exact:true}).click();
 await page.getByRole('button',{name:'删除录音',exact:true}).click();await page.getByRole('button',{name:'正在删除…',exact:true}).waitFor();
 await page.keyboard.press('Escape');assert(await page.getByRole('dialog').isVisible(),'Busy delete cannot dismiss');
 assert(await page.getByRole('button',{name:'取消',exact:true}).isDisabled(),'Busy cancel disabled');
 await page.getByRole('dialog').waitFor({state:'hidden'});checks.push('Mock delete: busy guard and successful completion');
 await page.evaluate(() => new Promise((resolve,reject)=>{const r=indexedDB.open('northstar-learning-v1',1);r.onsuccess=()=>{const tx=r.result.transaction('drafts','readwrite');tx.objectStore('drafts').put({eventId:'modal-fixture-buffer',blob:new Blob(['fixture'],{type:'audio/webm'}),durationMs:1000,createdAt:new Date().toISOString()},'recording:demo-01-v2:demo-01-v2-s01');tx.oncomplete=()=>{r.result.close();resolve();};tx.onerror=()=>reject(tx.error);};}));
 await page.reload();await page.getByRole('button',{name:'丢弃本机上传缓冲',exact:true}).click();await page.getByRole('dialog').waitFor();
 await page.screenshot({path:'docs/evidence/modal-redesign/discard-320.png'});await page.getByRole('button',{name:'取消',exact:true}).click();
 assert(await page.getByRole('button',{name:'重试上传原录音',exact:true}).isVisible(),'Cancel preserves buffer');
 await page.setViewportSize({width:1440,height:900});await page.goto(base+'writing');
 await page.getByRole('button',{name:'回载 V1 到草稿',exact:true}).click();
 await page.getByRole('dialog').waitFor();await page.screenshot({path:'docs/evidence/modal-redesign/writing-1440.png'});
 assert(await page.getByRole('dialog').locator('.button.primary').count()===1,'Writing primary action');
 await page.getByRole('button',{name:'取消',exact:true}).click();assert(await page.locator('#writing-text').inputValue()==='Keep my current draft.','Cancel preserves draft');
 await page.getByRole('button',{name:'内容来源',exact:true}).click();await page.getByRole('dialog').waitFor();
 await page.screenshot({path:'docs/evidence/modal-redesign/source-1440.png'});
 await page.setViewportSize({width:375,height:400});assert(await page.getByRole('dialog').locator('.modal-actions').evaluate(el=>{const r=el.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;}),'Short viewport footer stays visible');
 assert(await page.getByRole('dialog').locator('.modal-body').evaluate(el=>el.scrollHeight>el.clientHeight),'Long content scrolls inside body');
 await page.screenshot({path:'docs/evidence/modal-redesign/source-short.png'});await page.getByRole('button',{name:'知道了',exact:true}).click();
 await page.setViewportSize({width:375,height:900});await page.getByRole('button',{name:'打开句子助教',exact:true}).click();
 assert(await page.locator('dialog.drawer').isVisible(),'Mobile drawer shares modal');await page.screenshot({path:'docs/evidence/modal-redesign/drawer-375.png'});await page.keyboard.press('Escape');
 assert(!errors.length,errors.join(';'));return{passed:true,checks,writingCancel:true,source:true,drawer:true,interceptedWrites:writes,pageErrors:errors};
}
