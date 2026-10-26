async page => {
 const base=new URL(page.url()).origin,assert=(ok,m)=>{if(!ok)throw Error(m);};let blockedWrites=0;
 await page.route('**/api/v1/**',route=>{if(!['GET','HEAD','OPTIONS'].includes(route.request().method())){blockedWrites++;return route.abort('blockedbyclient');}return route.continue();});
 try {
 const response=await page.request.get(base+'/api/v1/reports');assert(response.ok(),'Fresh report');const report=await response.json();
 for(const value of Object.values(report.metrics))assert(Object.values(value).every(n=>n===0),'Fresh metrics all zero');
 assert((await page.request.get(base+'/api/v1/study/resume')).status()===204,'No fabricated checkpoint');
 await page.setViewportSize({width:1440,height:900});await page.goto(base+'/dashboard');await page.getByRole('link',{name:/开始浏览原创课/}).waitFor();
 await page.getByRole('heading',{name:'六步学习路径',exact:true}).waitFor();await page.screenshot({path:'docs/evidence/phase-09r/screenshots/fresh-dashboard-1440.png'});
 await page.getByRole('navigation',{name:'主导航'}).getByRole('link',{name:'课程中心',exact:true}).click();await page.getByText('仅目录 · 暂不可学习',{exact:true}).first().waitFor();
 assert(await page.getByText('仅目录 · 暂不可学习',{exact:true}).count()===4,'Four unavailable catalog books');
 await page.getByRole('link',{name:/开始浏览原创课/}).click();await page.getByRole('tab',{name:'课文',exact:true,selected:true}).waitFor();assert(await page.locator('.sentence-list li').count()===10,'Original ten sentences');
 await page.screenshot({path:'docs/evidence/phase-09r/screenshots/fresh-lesson-1440.png'});
 return {passed:true,zeroMetrics:true,initialCheckpointAbsent:true,tenSentences:true,blockedWrites};
 }finally{ /* Keep write interception active until the CLI closes this browser. */ }
}
