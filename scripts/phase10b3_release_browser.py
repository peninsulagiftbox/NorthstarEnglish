#!/usr/bin/env python3
"""Read-only verification of the deployed 3100 origin. All browser API writes are blocked."""
import importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('b3_release',ROOT/'scripts/deploy-phase10b3.py');deploy=importlib.util.module_from_spec(spec);spec.loader.exec_module(deploy)
run=sys.argv[1];assert run.isalnum();out=deploy.OUT/run
assert deploy.read(out/'DEPLOYED.json')['status']=='PASS'
cli=next((p.parent/'playwright-cli.js' for p in (Path.home()/'.npm/_npx').glob('*/node_modules/@playwright/cli/package.json') if json.loads(p.read_text()).get('version')=='0.1.22'),None)
assert cli,'Pinned existing CLI required'
command=['node',str(cli),'--session=northstar-phase10b3-release']
code='''async page=>{
 const assert=(v,m)=>{if(!v)throw Error(m);};const origin='http://127.0.0.1:3100',errors=[];let blocked=0;
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/v1/**',route=>{if(!['GET','HEAD','OPTIONS'].includes(route.request().method())){blocked++;return route.abort();}return route.continue();});
 const get=async path=>{const response=await page.request.get(origin+'/api/v1'+path);assert(response.ok(),path);return response.json();};
 const health=await page.request.get(origin+'/api/v1/health');assert(health.headers()['x-northstar-test-database']==='false','Personal origin required');assert((await health.json()).migrationVersion==='009.15','Deployed schema');
 const catalog=await get('/books');assert(catalog.books.length===4&&catalog.books.every(b=>b.actualLessonCount===0),'Real four-book empty catalog retained');assert(catalog.standaloneLessons.length===1&&catalog.standaloneLessons[0].id==='demo-01','No isolated fixture in personal DB');
 await page.setViewportSize({width:1440,height:900});await page.goto(origin+'/courses');await page.getByRole('heading',{name:'独立原创课程',exact:true}).waitFor();
 await page.locator('.book-card').first().getByRole('button',{name:/查看实际课程/}).click();await page.getByRole('dialog').waitFor();await page.getByText('本册尚无已导入课程',{exact:true}).waitFor();await page.getByRole('button',{name:'返回目录',exact:true}).click();
 assert(await page.getByRole('dialog').count()===0,'Existing catalog modal remains functional');await page.screenshot({path:'output/playwright/phase10b3-deployed-catalog.png'});
 const lesson=await get('/lessons/demo-01?versionId=demo-01-v2');assert(lesson.contentReadiness==='legacy_unassessed'&&lesson.publicationState==='published'&&!lesson.releaseReady,'Legacy boundary');assert(lesson.sentences.length===10&&new Set(lesson.sentences.map(s=>s.identityId)).size===10,'Stable identities');
 const versions=await get('/lessons/demo-01/versions');assert(versions.versions.length===2&&versions.versions.filter(v=>v.isCurrent).length===1,'Preserved two versions');
 await page.goto(origin+'/lesson/demo-01?version=demo-01-v2&tab=text&sentence=demo-01-v2-s01');await page.getByRole('tab',{name:'课文',exact:true}).waitFor();await page.getByText('已发布 · 历史内容，教学就绪度未评估',{exact:true}).waitFor();
 assert(await page.locator('.sidebar').evaluate(e=>e.getBoundingClientRect().width)===224,'Sidebar retained');assert(await page.locator('.player-bar').evaluate(e=>e.getBoundingClientRect().height)===76,'Player retained');
 await page.getByRole('button',{name:'内容来源',exact:true}).click();await page.getByRole('link',{name:/版本 1/}).waitFor();await page.screenshot({path:'output/playwright/phase10b3-deployed-workspace.png'});
 assert(!errors.length,'No page errors');return {passed:true,migrationVersion:'009.15',stableIdentities:10,legacyBoundary:true,existingDialogPreserved:true,pageErrors:errors,blockedBrowserWrites:blocked,serverLearningWrites:0,note:'Automatic resume writes are intentionally blocked; this does not verify personal learning submission'};
}'''
try:
 deploy.command(out,'live-browser-open',command+['open','about:blank'])
 deploy.command(out,'live-browser-snapshot',command+['snapshot'])
 result=deploy.command(out,'live-browser-readonly',command+['run-code',code]);text=result.stdout.decode();assert re.search(r'"passed"\s*:\s*true',text) and '### Error' not in text
finally:deploy.command(out,'live-browser-close',command+['close'],expected=(0,1))
