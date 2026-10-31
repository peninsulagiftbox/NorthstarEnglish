// Read-only production smoke; intercept persistence writes instead of generating learning evidence.
async page => {
  const base='http://127.0.0.1:3100', errors=[], blocked=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/v1/**',route=>{
    if(!['GET','HEAD','OPTIONS'].includes(route.request().method())) {
      blocked.push(route.request().method()+' '+new URL(route.request().url()).pathname);
      return route.abort();
    }
    return route.continue();
  });
  const health=await (await page.request.get(base+'/api/v1/health')).json();
  if(health.migrationVersion!=='011.09')throw Error('Unexpected deployed schema');
  await page.setViewportSize({width:1440,height:900});
  await page.goto(base+'/dashboard');
  await page.getByRole('heading',{name:'今天，来学一点英语。',exact:true}).waitFor();
  await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=quiz');
  await page.locator('.quiz-question').first().waitFor();
  if(await page.locator('.quiz-question').count()!==3)throw Error('Demo question count');
  await page.getByRole('button',{name:'提交本轮 3 题',exact:true}).waitFor();
  const quiz=await (await page.request.get(base+'/api/v1/quiz?lessonId=demo-01&versionId=demo-01-v2')).json();
  if(quiz.protocolVersion!=='quiz-submit-v2'||quiz.questions.some(q=>'answerKey' in q))throw Error('Invalid public quiz projection');
  await page.screenshot({path:'output/playwright/phase10c-deployment/quiz.png'});
  await page.goto(base+'/reports');
  await page.getByRole('heading',{name:'学习报告',exact:true}).waitFor();
  const report=await (await page.request.get(base+'/api/v1/reports')).json();
  if(!report.metrics.quiz.note.includes('真实题目数'))throw Error('Report denominator note');
  await page.screenshot({path:'output/playwright/phase10c-deployment/reports.png'});
  if(errors.length)throw Error(errors.join(';'));
  return {passed:true,version:health.migrationVersion,dashboard:true,quiz:true,reports:true,pageErrors:errors,blockedWrites:blocked.length};
}
