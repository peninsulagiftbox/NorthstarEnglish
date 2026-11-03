async (page) => {
  const base='http://127.0.0.1:3197';
  await page.setViewportSize({width:1440,height:900});
  await page.goto(base+'/review');
  await page.getByRole('button',{name:'全部概念卡',exact:true}).click();
  const card=page.locator('.review-card').filter({has:page.getByRole('heading',{name:'bank — financial institution',exact:true})});
  await card.waitFor();
  await card.locator('summary').click();
  await card.getByText(/条可见/).waitFor();
  const sources=await page.request.get(base+'/api/v1/concept-reviews/f87999e5-8838-4981-b2a2-c616c5d3eb96/sources?limit=100',{headers:{'X-Northstar-Request':'local-workspace'}});
  const rows=(await sources.json()).items;
  const restricted=rows.filter(x=>x.restricted);
  if(restricted.length)await card.getByText(/内容不可用（课程已撤回或无访问权限）/).first().waitFor();
  else await card.getByRole('link',{name:/查看这次练习/}).first().waitFor();
  const text=await card.innerText();
  if(restricted.length){
    if(!text.includes('内容不可用（课程已撤回或无访问权限）'))throw Error('restricted label missing');
    if(text.includes('Concept Review Fixture CR-A'))throw Error('withdrawn title leaked');
    for(const r of restricted){
      for(const k of Object.keys(r))if(!['attemptId','occurrenceId','lessonId','versionId','recordedAt','visible','restricted'].includes(k))throw Error('restricted field leak: '+k);
    }
  }else{
    if(!rows.some(x=>x.lessonId==='cr-a')||!rows.some(x=>x.lessonId==='cr-b'))throw Error('two lessons missing');
    const link=card.getByRole('link',{name:/查看这次练习/}).first();
    if(!(await link.getAttribute('href')).includes('attempt='))throw Error('trace link missing');
  }
  const details=await page.request.get(base+'/api/v1/concept-reviews/f87999e5-8838-4981-b2a2-c616c5d3eb96',{headers:{'X-Northstar-Request':'local-workspace'}});
  const c=await details.json();
  if(c.visibleSourceCount!==rows.filter(x=>!x.restricted).length)throw Error('aggregate leaked count');
  return {result:'PASS',url:page.url(),restricted:restricted.length,visible:c.visibleSourceCount,rows,text};
}
