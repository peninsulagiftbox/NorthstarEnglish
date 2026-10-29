// Real isolated APIs; no mocked publication state, score, mapping or media.
async page => {
  const base=new URL(page.url()).origin, errors=[], checks=[];
  const assert=(value,message)=>{if(!value)throw Error(message);};
  page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(15000);
  const health=await page.request.get(base+'/api/v1/health');assert(health.headers()['x-northstar-test-database']==='true','isolated origin required');
  assert((await health.json()).migrationVersion==='009.15','new migration loaded');
  await page.setViewportSize({width:1440,height:900});
  await page.goto(base+'/lesson/demo-01?version=demo-01-v1&sentence=demo-01-v1-s06&tab=text');
  await page.getByRole('tab',{name:'课文',exact:true}).waitFor();
  await page.getByText('已发布 · 历史内容，教学就绪度未评估',{exact:true}).waitFor();
  await page.getByRole('button',{name:'内容来源',exact:true}).click();
  const version=page.getByRole('link',{name:/版本 2/});await version.waitFor();
  const href=await version.getAttribute('href');assert(new URL(href,base).searchParams.get('sentence')==='','unreviewed Demo mapping must not guess suffix');
  assert((await page.locator('body').innerText()).includes('无确定映射'),'uncertain mapping explicitly shown');
  await version.click();await page.getByRole('tab',{name:'课文',exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelector('.sentence.selected')?.getAttribute('aria-label')==='选择并播放句子 1');
  checks.push('legacy readiness, explicit current/history versions, no guessed Demo suffix, first-sentence fallback');
  const get=async path=>{const r=await page.request.get(base+'/api/v1'+path);assert(r.ok(),path);return r.json();};
  const demo=await get('/lessons/demo-01?versionId=demo-01-v1');assert(demo.sentences.every(s=>s.identityId),'stable identities returned');
  assert(new Set(demo.sentences.map(s=>s.identityId)).size===10,'version identity uniqueness');
  const versions=await get('/lessons/pub-main/versions');const withdrawn=versions.versions.find(v=>v.publicationState==='withdrawn');assert(withdrawn&&!withdrawn.readable,'withdrawn metadata explicit');
  const refused=await page.request.get(base+'/api/v1/lessons/pub-main?versionId='+withdrawn.versionId);assert(refused.status()===410&&(await refused.json()).code==='VERSION_WITHDRAWN','withdrawn content explicit 410');
  const id=crypto.randomUUID();const result=await page.request.post(base+'/api/v1/study/events',{headers:{Origin:base,'X-Northstar-Request':'local-workspace'},data:{eventId:id,lessonId:'pub-main',versionId:'pub-v1',sentenceId:'pub-v1-s1',action:'start',clientOccurredAt:new Date().toISOString()}});
  assert(result.status()===410&&(await result.json()).code==='VERSION_WITHDRAWN','open-client new event rejected');
  const history=await get('/reviews/items');assert(history.some(r=>r.lessonId==='pub-main'&&r.versionId==='pub-v1'),'withdrawn old evidence traceable');
  checks.push('withdrawn content/new events rejected by real API, original evidence still traceable');
  await page.screenshot({path:'output/playwright/phase10b3-version-1440.png'});
  await page.goto(base+'/lesson/pub-hint?version=pub-hint-v2&tab=text');
  await page.getByText('该课程存在旧版本学习记录，仅作参考，不代表新版已掌握。',{exact:true}).waitFor();
  const stages=await get('/study/stages?lessonId=pub-hint&versionId=pub-hint-v2');assert(stages.every(s=>s.practiceCount===0&&s.state==='not_started'),'equivalent old evidence does not become new practice');
  await page.getByRole('button',{name:'内容来源',exact:true}).click();
  const link=page.getByRole('link',{name:/版本 2/});await link.waitFor();
  await page.screenshot({path:'output/playwright/phase10b3-equivalent-reference-1440.png'});
  checks.push('real reviewed equivalent reference shown; new-version practice remains empty');
  assert(!errors.length,'no page errors');return {passed:true,checks,pageErrors:errors};
}
