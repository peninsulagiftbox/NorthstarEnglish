// Real report/history UI and literal filter reads; no personal database or fake success responses.
async page => {
 const fixture=__FIXTURE__,base='http://127.0.0.1:3195',errors=[];
 const assert=(ok,text)=>{if(!ok)throw Error(text);};
 const get=async path=>{const r=await page.request.get(base+'/api/v1'+path);assert(r.ok(),'GET '+path);return r.json();};
 assert((await page.request.get(base+'/api/v1/health')).headers()['x-northstar-test-database']==='true','test schema required');
 page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(15000);await page.setViewportSize({width:1440,height:900});
 const report=await get('/reports');assert(JSON.stringify(report.metrics.quiz)===JSON.stringify(fixture.metrics),'aggregate unchanged by reads');
 for(const f of fixture.fixtures){const detail=report.quizRuns.find(r=>r.id===f.runId);assert(detail&&detail.verified===(f.mode==='legacy-good'),'report detail verification '+f.mode);}
 for(const name of ['lessonId','versionId','setId'])for(const value of ["\\' OR 1=1 -- ",'课程\\\'測驗','invalid/id']){
   const query=new URLSearchParams({[name]:value}),filtered=await get('/reports?'+query);
   assert(filtered.quizRuns.length===0&&filtered.metrics.quiz.total===0&&filtered.metrics.quiz.unverifiedRuns===0,'literal filter '+name);
 }
 const combined=await get('/reports?'+new URLSearchParams({lessonId:'demo-01',versionId:'demo-01-v2',setId:fixture.setId,from:'2020-01-01T00:00:00Z',to:'2050-01-01T00:00:00Z'}));
 assert(combined.quizScope.setId===fixture.setId&&combined.quizRuns.length>0,'combined filter scope');
 await page.goto(base+'/reports');await page.getByRole('heading',{name:'测验交卷明细',exact:true}).waitFor();
 assert(await page.locator('li').filter({hasText:'未核验 · 不猜分母，不计入汇总'}).count()>=2,'invalid runs clearly labeled in report');
 const quizMetric=page.locator('.service-list > div').filter({has:page.getByText('测验正确 / 总作答题次（仅核验通过的交卷）',{exact:true})}).locator('dd');
 assert((await quizMetric.innerText()).includes(`${fixture.metrics.correct} / ${fixture.metrics.total}`),'UI numerator/denominator use verified scores');
 await page.screenshot({path:'output/playwright/phase10c2-r1/report.png'});
 await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=quiz');await page.locator('.quiz-question').first().waitFor();
 await page.locator('.quiz-history summary').click();
 assert(await page.locator('.quiz-history h3').filter({hasText:'未核验历史'}).count()>=2,'history exposes unverified status');
 const history=(await get('/quiz?lessonId=demo-01&versionId=demo-01-v2')).history;
 for(const f of fixture.fixtures)assert(history.find(r=>r.id===f.runId).verified===(f.mode==='legacy-good'),'history agrees '+f.mode);
 const legacy=fixture.fixtures[0];
 const replay=await page.request.post(base+'/api/v1'+legacy.path,{headers:{Origin:base,'X-Northstar-Request':'local-workspace'},data:legacy.payload});
 const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])])):value;
 assert(replay.ok()&&JSON.stringify(canonical(await replay.json()))===JSON.stringify(canonical(legacy.result)),'legacy receipt replay content remains unchanged');
 await page.screenshot({path:'output/playwright/phase10c2-r1/history.png'});
 assert(errors.length===0,errors.join(';'));
 return {passed:true,checks:['report invalid-history labels and verified-only totals','history/report verification agree','quote/backslash/Unicode and combined filters','legacy response replay unchanged'],pageErrors:errors};
}
