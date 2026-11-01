// Real API-backed 5/12/100-question UI, scoped drafts, HTTP 500 refresh/retry and multiple histories.
async page => {
 const fixtures=__FIXTURES__, base='http://127.0.0.1:3195',checks=[],metrics=[],errors=[];
 const assert=(ok,text)=>{if(!ok)throw Error(text);};
 page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));
 const get=async path=>{const r=await page.request.get(base+'/api/v1'+path);assert(r.ok(),'GET '+path);return r.json();};
 assert((await page.request.get(base+'/api/v1/health')).headers()['x-northstar-test-database']==='true','isolated schema required');
 const url=f=>base+'/lesson/'+f.lessonId+'?version='+f.versionId+'&tab=quiz';
 const key=(f,q)=>`northstar:quiz:v2:${f.lessonId}:${f.versionId}:${q.setId}:${q.setHash}`;
 const waitDraft=async(k,count)=>{
   await page.waitForFunction(async ({k,count})=>new Promise(resolve=>{
     const open=indexedDB.open('northstar-learning-v1',1);
     open.onsuccess=()=>{const tx=open.result.transaction('drafts','readonly'),rq=tx.objectStore('drafts').get(k);tx.oncomplete=()=>{open.result.close();resolve(Object.keys(rq.result?.answers??{}).length===count);};};
   }),{k,count});
 };
 await page.setViewportSize({width:1440,height:900});
 for(const f of fixtures) {
   const q=await get('/quiz?lessonId='+f.lessonId+'&versionId='+f.versionId);
   assert(q.questions.length===f.total&&q.totalCount===f.total,'API real denominator');
   assert(q.questions.every((x,i)=>x.ordinal===i+1&&!('answerKey' in x)&&!('explanation' in x)),'public questions hide keys and preserve ordinal');
   await page.goto(url(f));await page.locator('.quiz-question').first().waitFor();
   assert(await page.locator('.quiz-question').count()===f.total,'all fieldsets rendered');
   const submit=()=>page.getByRole('button',{name:`提交本轮 ${f.total} 题`,exact:true});
   assert(await submit().isDisabled(),'incomplete submit disabled');
   await page.getByRole('radio',{name:'Choice A 1',exact:true}).check();await waitDraft(key(f,q),1);
   if(f.total===5) {
     for(const other of fixtures.slice(1)) {
       await page.goto(url(other));await page.locator('.quiz-question').first().waitFor();
       assert(await page.locator('.quiz-question input:checked').count()===0,'cross-course/version drafts never merge');
     }
     await page.goto(url(f));await page.getByRole('radio',{name:'Choice A 1',exact:true}).waitFor();
     await page.waitForFunction(()=>document.querySelectorAll('.quiz-question input:checked').length===1);
     checks.push('cross-course and cross-version drafts isolated');
   }
   await page.reload();await page.waitForFunction(()=>document.querySelectorAll('.quiz-question input:checked').length===1);
   for(let i=2;i<=f.total;i++){await page.getByRole('radio',{name:'Choice A '+i,exact:true}).check();await waitDraft(key(f,q),i);}
   await page.getByText('全部题目已作答，可以交卷。',{exact:true}).waitFor();
   assert(!await submit().isDisabled(),'complete submit enabled');
   assert(await page.locator('.quiz-question legend').allTextContents().then(xs=>xs.every((s,i)=>s.startsWith((i+1)+'. '))),'ordinal order in DOM');
   let savedRequest=null;
   const path='**/api/v1/quiz/sets/'+q.setId+'/attempts';
   await page.route(path,async route=>{
     savedRequest=route.request().postDataJSON();
     await route.fulfill({status:500,contentType:'application/problem+json',body:JSON.stringify({detail:'Isolated HTTP 500 acceptance probe.'})});
   });
   await submit().click();await page.getByRole('button',{name:'重试原提交',exact:true}).waitFor();
   assert(Object.keys(savedRequest.answers).length===f.total,'full request answers, no truncation');
   await page.unroute(path);await page.reload();
   await page.getByRole('button',{name:'重试原提交',exact:true}).waitFor();
   const response=page.waitForResponse(r=>r.url().endsWith('/sets/'+q.setId+'/attempts')&&r.request().method()==='POST');
   const started=Date.now();await page.getByRole('button',{name:'重试原提交',exact:true}).click();const returned=await response;
   assert(JSON.stringify(returned.request().postDataJSON())===JSON.stringify(savedRequest),'refresh retry preserves original event and body');
   const result=await returned.json();assert(result.totalCount===f.total&&result.correctCount===f.total,'real response denominator');
   await page.getByRole('heading',{name:`本轮结果：${f.total} / ${f.total} 题正确`,exact:true}).waitFor();
   metrics.push({count:f.total,elapsedMs:Date.now()-started,requestBytes:JSON.stringify(savedRequest).length});
   for(let i=1;i<=f.total;i++){await page.getByRole('radio',{name:'Choice B '+i,exact:true}).check();await waitDraft(key(f,q),i);}
   await submit().click();await page.getByRole('heading',{name:`本轮结果：0 / ${f.total} 题正确`,exact:true}).waitFor();
   const history=(await get('/quiz?lessonId='+f.lessonId+'&versionId='+f.versionId)).history;
   assert(history.length===2,'two independent rounds only');
   assert(history[0].correctCount===0&&history[1].correctCount===f.total,'history preserves first result');
   assert(history.every(r=>r.totalCount===f.total&&r.answers.length===f.total&&r.verified),'complete verified snapshots');
   await page.locator('.quiz-history summary').click();
   assert(await page.locator('.quiz-history article').count()===2,'both histories visible');
   await page.screenshot({path:'output/playwright/phase10c2-retest/quiz-'+f.total+'.png'});
   checks.push(f.total+' questions: progress/order/draft refresh/500 original-event retry/two-round history');
 }
 // A stale set/hash scope must never be consumed by a different current set.
 const first=fixtures[0],q=await get('/quiz?lessonId='+first.lessonId+'&versionId='+first.versionId);
 await page.evaluate(async ({k,answers})=>new Promise(resolve=>{const open=indexedDB.open('northstar-learning-v1',1);open.onsuccess=()=>{const tx=open.result.transaction('drafts','readwrite');tx.objectStore('drafts').put({protocolVersion:'quiz-submit-v2',answers},k);tx.oncomplete=()=>{open.result.close();resolve();};};}),{k:key(first,q)+':stale',answers:{[q.questions[0].id]:q.questions[0].options[0].id}});
 await page.goto(url(first));await page.locator('.quiz-question').first().waitFor();assert(await page.locator('.quiz-question input:checked').count()===0,'stale set/hash draft not imported');
 assert(errors.length===0,errors.join(';'));return {passed:true,checks,metrics,pageErrors:errors};
}
