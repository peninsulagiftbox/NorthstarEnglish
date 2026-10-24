// Open about:blank#<isolated-api-port> first. Every app API request is forwarded
// to that verified test schema; the browser must never write to the main API.
async page => {
 page.setDefaultTimeout(12000);
 const port=Number(new URL(page.url()).hash.slice(1));
 if(!Number.isInteger(port)||port<1024||port>65535)throw new Error('Isolated API port required in blank-page hash');
 const api='http://127.0.0.1:'+port,base='http://127.0.0.1:3100';
 const health=await page.request.get(api+'/api/v1/health');
 if(health.headers()['x-northstar-test-database']!=='true')throw new Error('Isolated DB required');
 const errors=[],checks=[],skipEvents=[];page.on('pageerror',e=>errors.push(e.message));
 const assert=(ok,message)=>{if(!ok)throw new Error(message);};
 let fault='',release,accepted;
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),url=new URL(req.url());
  const skip=req.method()==='POST'&&url.pathname.endsWith('/study/events')&&req.postDataJSON().action==='skip';
  if(skip)skipEvents.push(req.postDataJSON().eventId);
  if(skip&&fault==='failure'){fault='';return route.fulfill({status:503,contentType:'application/problem+json',body:JSON.stringify({detail:'测试跳过保存失败'})});}
  const response=await route.fetch({url:api+url.pathname+url.search});
  if(skip&&fault==='loss'){fault='';assert(response.status()===200,'Accepted skip');return route.abort('failed');}
  if(skip&&fault==='delay'){fault='';accepted();await new Promise(resolve=>release=resolve);}
  return route.fulfill({response});
 });
 const stages=async()=> (await page.request.get(api+'/api/v1/study/stages?lessonId=demo-01&versionId=demo-01-v2')).json();
 const reviewsBefore=(await(await page.request.get(api+'/api/v1/reviews/items')).json()).length;
 const before=await stages();
 const target=async n=>{await page.waitForFunction(id=>new URL(location.href).searchParams.get('sentence')===id,`demo-01-v2-s${String(n).padStart(2,'0')}`);await page.waitForFunction(n=>{const t=document.querySelector('#dictation-text');return t&&!t.disabled&&!t.readOnly&&document.querySelector('.draft-editor')?.textContent.includes(`听写目标为第 ${n} 句`);},n);};
 const pick=async n=>{await page.getByRole('button',{name:`选择句子 ${n}`,exact:true}).click();await target(n);};
 const idle=()=>page.waitForFunction(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.textContent==='跳过本句');return b&&!b.disabled&&b.getAttribute('aria-disabled')!=='true';});
 const editor=page.getByLabel('本句听写草稿',{exact:true});
 await page.setViewportSize({width:1440,height:900});
 await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=dictation&sentence=demo-01-v2-s01');await target(1);await idle();
 await editor.fill('Keep this draft when skipping.');await editor.blur();await idle();
 await page.getByRole('button',{name:'播放本句',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('audio')?.currentTime>.1);
 await page.getByRole('button',{name:'跳过本句',exact:true}).click();await target(2);await idle();
 await page.waitForFunction(()=>{const a=document.querySelector('audio');return a?.paused&&a.src.includes('a02');});
 const first=(await stages()).find(s=>s.sentenceId==='demo-01-v2-s01');assert(first.state==='skipped','Source sentence skipped');
 assert(first.practiceCount===before.find(s=>s.sentenceId==='demo-01-v2-s01').practiceCount,'Skip is not practice');
 await page.screenshot({path:'docs/evidence/dictation-skip/next-sentence-1440.png'});
 await pick(1);assert(await editor.inputValue()==='Keep this draft when skipping.','Source draft preserved');await idle();
 fault='failure';await page.getByRole('button',{name:'跳过本句',exact:true}).click();
 await page.getByRole('button',{name:'重试同一次提交',exact:true}).waitFor();assert(new URL(page.url()).searchParams.get('sentence').endsWith('s01'),'Failure must not advance');
 fault='loss';await page.getByRole('button',{name:'重试同一次提交',exact:true}).click();
 await page.waitForFunction(()=>document.body.textContent.includes('暂时无法连接本地服务'));
 assert(new URL(page.url()).searchParams.get('sentence').endsWith('s01'),'Uncertain receipt must not advance');
 await page.reload();await page.getByRole('button',{name:'重试同一次提交',exact:true}).waitFor();
 await page.getByRole('button',{name:'重试同一次提交',exact:true}).click();await target(2);await idle();
 assert(new Set(skipEvents.slice(-3)).size===1,'Retry keeps original event ID');
 checks.push('Confirmed skip advances exactly one sentence, pauses old audio, loads next without autoplay and preserves draft; failures stay put, refresh/retry reuses event');
 const acceptedPromise=new Promise(resolve=>accepted=resolve);fault='delay';
 await page.getByRole('button',{name:'跳过本句',exact:true}).click();await acceptedPromise;
 await pick(3);release();await page.waitForLoadState('networkidle');
 assert(new URL(page.url()).searchParams.get('sentence').endsWith('s03'),'Late skip response must not steal manually selected target');
 await idle();await page.getByRole('button',{name:'暂停本轮',exact:true}).click();await idle();
 assert(new URL(page.url()).searchParams.get('sentence').endsWith('s03'),'Pause must not advance');
 await pick(10);await idle();await page.getByRole('button',{name:'跳过本句',exact:true}).click();
 await page.getByText('已跳过最后一句。可选择其他句子补练，或切换到精读词汇继续学习；跳过不计练习完成。',{exact:true}).waitFor();
 assert(new URL(page.url()).searchParams.get('sentence').endsWith('s10'),'Last sentence does not wrap');
 await page.screenshot({path:'docs/evidence/dictation-skip/last-sentence-1440.png'});
 const after=await stages();assert(after.every(row=>row.practiceCount===before.find(s=>s.sentenceId===row.sentenceId).practiceCount),'No new practice for any target');
 assert((await(await page.request.get(api+'/api/v1/reviews/items')).json()).length===reviewsBefore,'No new error evidence from skip');
 assert(errors.length===0,errors.join(';'));checks.push('Late response retains manual target; pause stays put; last sentence explains boundary without wrap; no practice/review increments');
 return {passed:true,checks,pageErrors:errors,isolatedApiPort:port};
}
