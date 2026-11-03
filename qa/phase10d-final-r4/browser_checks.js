async (providedPage) => {
  const root = '/Users/wangshiqi/Project/NorthstarEnglish';
  const out = root + '/qa/phase10d-final-r4/evidence';
  const identity = {web:'http://127.0.0.1:3198',cardId:'d3d3c982-4bd9-4780-a3ac-1c024a1f9a21',jarSha256:'771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6',buildId:'-npvkMs_s7of_JgI9yxq7'};
  const context = await providedPage.context().browser().newContext({viewport:{width:1440,height:900}});
  const page = await context.newPage();
  const errors=[], requests=[], responses=[];
  page.on('pageerror',e=>errors.push({type:'pageerror',message:e.message}));
  page.on('requestfailed',r=>errors.push({type:'networkerror',url:r.url(),failure:r.failure()}));
  page.on('request',r=>{if(r.url().includes('/api/v1/'))requests.push({url:r.url(),method:r.method()});});
  page.on('response',r=>{if(r.url().includes('/api/v1/'))responses.push({url:r.url(),status:r.status()});});
  try {
    await context.tracing.start({screenshots:true,snapshots:true,sources:false});
    await page.goto(identity.web+'/review');
    await page.getByRole('button',{name:'全部概念卡',exact:true}).click();
    const card=page.locator('.review-card').filter({has:page.getByRole('heading',{name:'bank — financial institution',exact:true})});
    await card.waitFor();
    await card.locator('summary').click();
    await card.getByText(/内容不可用（课程已撤回或无访问权限）/).first().waitFor();
    const headers={'X-Northstar-Request':'local-workspace','Origin':identity.web};
    let cursor=null,apiRows=[],apiPages=[];
    do {
      const url=identity.web+'/api/v1/concept-reviews/'+identity.cardId+'/sources'+(cursor?'?cursor='+encodeURIComponent(cursor):'');
      const response=await page.request.get(url,{headers});
      const json=await response.json();
      if(response.status()!==200)throw Error('API source request failed '+response.status());
      apiRows.push(...json.items);apiPages.push({status:response.status(),items:json.items.length,nextCursor:json.nextCursor});
      cursor=json.nextCursor;
      if(apiPages.length>90)throw Error('cursor did not terminate');
    } while(cursor);
    if(apiRows.length!==83||new Set(apiRows.map(r=>r.attemptId+':'+r.occurrenceId)).size!==83)throw Error('API source completeness failed');
    const restricted=apiRows.filter(r=>r.restricted), visible=apiRows.filter(r=>!r.restricted);
    if(restricted.length!==82||visible.length!==1)throw Error('wrong fixture visibility counts');
    for(const r of restricted)for(const key of Object.keys(r))if(!['attemptId','occurrenceId','lessonId','versionId','recordedAt','visible','restricted'].includes(key))throw Error('restricted field leak '+key);
    const firstRender={restricted:await card.getByText(/内容不可用（课程已撤回或无访问权限）/).count(),visible:await card.getByRole('link',{name:/查看这次练习/}).count(),text:await card.innerText(),buttons:await card.getByRole('button').allTextContents()};
    // Reopening and queue refresh must not hide the continuation needed to reach the remaining sources.
    await page.getByRole('button',{name:'刷新概念卡',exact:true}).click();
    await page.getByRole('button',{name:'全部概念卡',exact:true}).click();
    await card.waitFor();await card.locator('summary').click();
    await card.getByText(/内容不可用（课程已撤回或无访问权限）/).first().waitFor();
    const secondRender={restricted:await card.getByText(/内容不可用（课程已撤回或无访问权限）/).count(),visible:await card.getByRole('link',{name:/查看这次练习/}).count(),text:await card.innerText()};
    const uiTotal=secondRender.restricted+secondRender.visible;
    const result={result:uiTotal===83?'PASS':'FAIL',defect:uiTotal===83?null:'QA-D02-R4-FINAL-001',jarSha256:identity.jarSha256,buildId:identity.buildId,database:identity.database,cardId:identity.cardId,apiCount:apiRows.length,apiRestricted:restricted.length,apiVisible:visible.length,apiPages,firstRender,secondRender,uiCount:uiTotal,missing:83-uiTotal,requests,responses,pageErrors:errors,body:await page.locator('body').innerText()};
    await page.screenshot({path:root+'/output/playwright/phase10d-final-r4/sources-truncated.png',fullPage:true});
    await context.tracing.stop({path:root+'/output/playwright/phase10d-final-r4/sources-truncated-trace.zip'});
    return result;
  } finally {await context.close();}
}
