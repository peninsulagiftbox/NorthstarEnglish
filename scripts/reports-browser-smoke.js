async (page) => {
  const base = new URL(page.url()).origin;
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const check=(value,label)=>{if(!value)throw new Error(label);};
  const get=path=>page.evaluate(async p=>{const r=await fetch('/api/v1'+p);if(!r.ok)throw new Error('GET '+p+':'+r.status);return r.json();},path);
  await page.setViewportSize({width:1440,height:900});
  await page.getByRole('heading',{name:'六步学习路径'}).waitFor();
  check(await page.locator('.learning-path').first().locator('li').count()===6,'six stages');
  await page.screenshot({path:'docs/evidence/phase-08/screenshots/dashboard-1440.png',fullPage:true});
  await page.goto(base+'/reports');await page.getByRole('heading',{name:'真实行为与样本'}).waitFor();
  const report=await get('/reports');check(report.metrics.quiz.total===report.metrics.quiz.runs*3,'quiz denominator');
  check((await page.locator('main').innerText()).includes('样本'),'samples visible');
  await page.screenshot({path:'docs/evidence/phase-08/screenshots/reports-1440.png',fullPage:true});
  await page.goto(base+'/settings');await page.getByRole('button',{name:'保存偏好',exact:true}).waitFor();
  const original=await get('/settings');
  try {
    for(let i=0;i<4 && await page.getByRole('button',{name:'默认播放倍速',exact:true}).getAttribute('data-speed')!=='1.25';i++)await page.getByRole('button',{name:'默认播放倍速',exact:true}).click();
    await page.getByLabel('显示键盘快捷键提示').uncheck();
    await page.getByLabel('启用播放器快捷键').uncheck();
    await page.getByRole('button',{name:'保存偏好',exact:true}).click();
    await page.getByText('偏好已保存到本地服务，刷新后保留。重新进入工作台时应用。').waitFor();
    await page.reload();await page.getByRole('button',{name:'保存偏好',exact:true}).waitFor();
    check(await page.getByRole('button',{name:'默认播放倍速',exact:true}).getAttribute('data-speed')==='1.25','settings persisted');
    await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=text');
    await page.getByRole('button',{name:'播放速度',exact:true}).waitFor();
    check(await page.getByRole('button',{name:'播放速度',exact:true}).getAttribute('data-speed')==='1.25','default speed applied');
    check(await page.getByText(/键盘提示：/).count()===0,'hints disabled');
    await page.keyboard.press('Space');await page.waitForTimeout(250);
    check(await page.locator('audio[hidden]').evaluate(a=>a.paused),'shortcut disabled');
    check(await page.getByText('本地预置讲解 · 未接入 AI',{exact:true}).count()>0,'AI explicit');
    await page.goto(base+'/settings');await page.getByRole('button',{name:'导出学习 JSON',exact:true}).waitFor();
    const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'导出学习 JSON',exact:true}).click();
    const download=await downloadPromise;await download.saveAs('output/playwright/phase08-download.json');
    await page.getByLabel('选择恢复 JSON').setInputFiles('output/playwright/phase08-download.json');
    await page.getByRole('heading',{name:'格式预检通过 · 尚未恢复'}).waitFor();
    const exported=await get('/data/export');
    await page.getByLabel('选择恢复 JSON').setInputFiles({name:'broken.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({...exported,sha256:'broken'}))});
    await page.getByText('数据包格式、版本、归属或内容基线不匹配；未导入任何数据。',{exact:true}).waitFor();
    await page.screenshot({path:'docs/evidence/phase-08/screenshots/settings-1440.png',fullPage:true});
  } finally {
    const current=await get('/settings');
    const result=await page.evaluate(async value=>{const r=await fetch('/api/v1/settings',{method:'PUT',headers:{'Content-Type':'application/json','X-Northstar-Request':'local-workspace'},body:JSON.stringify(value)});return r.status;},{...original,rowVersion:current.rowVersion});
    check(result===200,'restore test preferences');
  }
  for(const route of ['/dashboard','/reports','/settings']) {
    await page.setViewportSize({width:375,height:900});await page.goto(base+route);
    await page.getByRole('heading',{level:1}).waitFor();await page.waitForTimeout(350);
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),route+' mobile overflow');
    await page.screenshot({path:'docs/evidence/phase-08/screenshots/'+route.slice(1)+'-375.png',fullPage:true});
  }
  await page.route('**/api/v1/reports',r=>r.fulfill({status:503,contentType:'application/problem+json',body:JSON.stringify({detail:'测试：统计服务暂不可用'})}));
  await page.goto(base+'/reports');await page.getByText('测试：统计服务暂不可用',{exact:true}).waitFor();
  check(await page.getByRole('button',{name:'重新读取统计'}).count()===1,'error retry');await page.unroute('**/api/v1/reports');
  await page.getByRole('button',{name:'重新读取统计'}).click();await page.getByRole('heading',{name:'真实行为与样本'}).waitFor();
  const empty=structuredClone(report);for(const metric of Object.values(empty.metrics))for(const k of Object.keys(metric))metric[k]=0;empty.readingHistory=[];
  await page.route('**/api/v1/reports',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(empty)}));
  await page.reload();await page.getByRole('heading',{name:'真实行为与样本'}).waitFor();
  check((await page.locator('main').innerText()).includes('暂无数据'),'empty report');
  await page.screenshot({path:'docs/evidence/phase-08/screenshots/reports-empty-375.png',fullPage:true});
  await page.unroute('**/api/v1/reports');
  check(errors.length===0,'page errors: '+errors.join(','));return {passed:true,pageErrors:errors,emptyAnd503:'explicit GET response injection',reportMetrics:report.metrics};
}
