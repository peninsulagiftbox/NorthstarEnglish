// Mock every write. Count projection is one lesson-wide read, then local numeric selection.
async page=>{
 let reads=0,failRead=false,revision=0;const counts=Array.from({length:10},(_,i)=>i%3===0?12:i),errors=[],results=[];
 const sid=n=>`demo-01-v2-s${String(n).padStart(2,'0')}`;page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(12000);
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),u=new URL(req.url());
  if(req.method()==='GET'&&u.pathname==='/api/v1/study/stages'){reads++;await new Promise(r=>setTimeout(r,600));if(failRead){failRead=false;return route.fulfill({status:503,json:{detail:'模拟次数读取失败'}});}return route.fulfill({json:counts.map((n,i)=>({sentenceId:sid(i+1),state:'not_started',practiceCount:n}))});}
  if(req.method()==='GET'&&u.pathname.startsWith('/api/v1/drafts/')){await new Promise(r=>setTimeout(r,500));return route.fulfill({json:{text:'',rowVersion:1}});}
  if(req.method()==='POST'&&u.pathname.endsWith('/attempts')){const body=req.postDataJSON(),i=Number(body.sentenceId.slice(-2))-1;counts[i]++;return route.fulfill({json:{attemptId:crypto.randomUUID(),eventId:body.eventId,state:'practiced',rawText:body.text,standardText:body.text,answerExposed:true,result:{correct:true,edits:[]}}});}
  if(req.method()==='POST'&&u.pathname==='/api/v1/study/events'){const b=req.postDataJSON();return route.fulfill({json:{eventId:b.eventId,state:({start:'in_progress',pause:'paused',skip:'skipped'})[b.action]}});}
  if(req.method()!=='GET')return route.fulfill({json:{rowVersion:++revision}});
  return route.continue();
 });
 const assert=(v,m)=>{if(!v)throw Error(m);};
 for(const width of [1440,375]){
  await page.setViewportSize({width,height:900});const before=reads;await page.goto(`http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=dictation&sentence=${sid(1)}&english=1`);
  await page.waitForFunction(n=>document.querySelector('[data-testid="practice-count"]')?.textContent===String(n),counts[0]);
  await page.evaluate(()=>{window.__badge=document.querySelector('[data-testid="practice-state"]');window.__numbers=[];window.__trace=true;const tick=()=>{window.__numbers.push({same:document.querySelector('[data-testid="practice-state"]')===window.__badge,n:document.querySelector('[data-testid="practice-count"]')?.textContent,status:!!document.querySelector('.draft-status')});if(window.__trace)requestAnimationFrame(tick);};tick();});
  for(const n of [2,3,4,5,6,7,8,9,10,1]){await page.getByRole('button',{name:`选择句子 ${n}`,exact:true}).click();await page.waitForFunction(expected=>document.querySelector('[data-testid="practice-count"]')?.textContent===String(expected),counts[n-1]);await page.waitForTimeout(70);}
  await page.waitForFunction(()=>document.querySelector('#dictation-text')&&!document.querySelector('#dictation-text').readOnly);
  const samples=await page.evaluate(()=>{window.__trace=false;return window.__numbers;});assert(samples.every(s=>s.same&&/^\d+$/.test(s.n)&&!s.status),'Stable badge, digits only, no draft status');assert(reads===before+1,'Sentence switching must not reread counts');
  const readBefore=reads;await page.getByRole('button',{name:'暂停本轮',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.dictation-actions').getAttribute('aria-busy')==='false');assert(reads===readBefore,'Pause does not reread unchanged count');
  await page.getByRole('button',{name:'播放本句',exact:true}).click();await page.waitForFunction(()=>document.querySelector('audio')?.currentTime>.2);await page.getByLabel('本句听写草稿',{exact:true}).fill('A test answer.');await page.waitForFunction(()=>document.querySelector('.dictation-actions').getAttribute('aria-busy')==='false');
  const previous=counts[0];await page.getByRole('button',{name:'检查听写',exact:true}).click();await page.waitForFunction(n=>document.querySelector('[data-testid="practice-count"]')?.textContent===String(n),previous+1);assert(reads===readBefore+1,'Formal attempt refreshes count once');
  await page.screenshot({path:`docs/evidence/dictation-count/count-${width}.png`});results.push({width,sentenceSwitches:10,countReads:1,sameBadge:true,noDraftStatus:true,formalAttemptUpdates:true});
 }
 failRead=true;await page.reload();await page.getByRole('button',{name:'重试读取次数',exact:true}).waitFor();assert(await page.getByTestId('practice-count').textContent()==='—','Unknown count never displayed as zero');await page.getByRole('button',{name:'重试读取次数',exact:true}).click();await page.waitForFunction(n=>document.querySelector('[data-testid="practice-count"]')?.textContent===String(n),counts[0]);assert(!errors.length,errors.join(';'));
 return{passed:true,results,failedReadExplicit:true,retryRecovers:true,pageErrors:errors};
}
