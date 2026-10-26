// Run only after exact snapshot verification of the dedicated recovery instance on Web3102.
async page => {
 const base=new URL(page.url()).origin,assert=(ok,m)=>{if(!ok)throw Error(m);};
 assert(base==='http://127.0.0.1:3102','Continuation requires dedicated restore Web3102');
 page.setDefaultTimeout(15000);
 const get=async p=>(await(await page.request.get(base+'/api/v1'+p)).json());
 const before=(await get('/reports')).metrics.dictation.submitted;
 await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=dictation&sentence=demo-01-v2-s10');
 const editor=page.getByLabel('本句听写草稿',{exact:true});await editor.waitFor();
 await page.getByRole('button',{name:'播放本句',exact:true}).click();
 await page.waitForFunction(()=>{const a=document.querySelector('audio[hidden]');return a?.src.includes('a10')&&a.currentTime>.25&&!a.paused;});
 await page.getByRole('button',{name:'暂停播放',exact:true}).click();
 await editor.fill('That would be grate. Thank you!');
 const response=page.waitForResponse(r=>r.url().endsWith('/demo-01-v2-s10-dictation/attempts')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'检查听写',exact:true}).click();const result=await response;assert(result.ok(),'Actual UI submission');
 const body=result.request().postDataJSON(),value=await result.json();assert(body.audioPlayed===true,'Client observed actual played sentence10');
 const retry=await page.request.post(result.url(),{headers:{Origin:base,'X-Northstar-Request':'local-workspace'},data:body});
 assert(retry.ok()&&(await retry.json()).attemptId===value.attemptId,'Idempotent continuation');
 assert((await get('/reports')).metrics.dictation.submitted===before+1,'Exactly one restored submission');
 await page.getByRole('region',{name:'听写对照'}).waitFor();await page.getByText('浏览位置已保存 · 不计练习完成',{exact:true}).waitFor();
 await page.screenshot({path:'docs/evidence/phase-09r/screenshots/restored-continued-1440.png'});
 return {passed:true,actualOriginalAudioDecoded:true,attemptId:value.attemptId,exactlyOneSubmission:true};
}
