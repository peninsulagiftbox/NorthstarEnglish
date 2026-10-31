async page => {
 const base=new URL(page.url()).origin;const assert=(v,m)=>{if(!v)throw Error(m);};
 if((await page.request.get(base+'/api/v1/health')).headers()['x-northstar-test-database']!=='true')throw Error('isolated DB required');
 await page.goto(base+'/lesson/c1-shared?version=c1-shared-v1&tab=text');await page.getByRole('button',{name:'选择并播放句子 1',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('audio').paused);await page.getByRole('button',{name:'暂停播放',exact:true}).click();await page.getByText('浏览位置已保存 · 不计练习完成',{exact:true}).waitFor();
 await page.getByRole('button',{name:'内容来源',exact:true}).click();
 const target=page.getByRole('link',{name:/版本 2/});await target.waitFor();
 let started;const pending=new Promise(r=>{started=r;});let delayed=false;const statuses=[];
 page.on('response',r=>{if(r.url().endsWith('/study/resume')&&r.request().method()==='PUT')statuses.push(r.status());});
 await page.route('**/api/v1/study/resume',async route=>{
  const req=route.request();if(req.method()==='PUT'&&!delayed&&req.postDataJSON().versionId==='c1-shared-v1'){delayed=true;started();await new Promise(r=>setTimeout(r,250));}
  await route.continue();
 });
 await page.getByRole('slider',{name:'当前句播放进度'}).evaluate(el=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,'1');el.dispatchEvent(new Event('input',{bubbles:true}));});
 await pending;await target.click();await page.getByRole('tab',{name:'课文',exact:true}).waitFor();await page.waitForURL(/version=c1-shared-v2/);await page.getByText('浏览位置已保存 · 不计练习完成',{exact:true}).waitFor();
 const resume=await (await page.request.get(base+'/api/v1/study/resume')).json();assert(resume.versionId==='c1-shared-v2','new version checkpoint retained');assert(!statuses.some(s=>s===412),'same-tab old request cannot create a false CAS conflict');await page.unrouteAll({behavior:'wait'});
 return {passed:true,delayedOldWrite:delayed,putStatuses:statuses,newVersion:resume.versionId,externalTabCAS:'unchanged; API integration checks remain'};
}
