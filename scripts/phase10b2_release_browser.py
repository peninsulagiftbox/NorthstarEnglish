#!/usr/bin/env python3
"""Read-only catalog check of the deployed personal origin; all browser write requests are aborted."""
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('phase10b2_deploy',ROOT/'scripts/deploy-phase10b2.py')
deploy=importlib.util.module_from_spec(spec);spec.loader.exec_module(deploy)
run=sys.argv[1];assert run.isalnum();out=deploy.OUT/run
latest=deploy.read(out/'STATUS.json')['latestResult'] if (out/'STATUS.json').exists() else 'result.json'
assert deploy.read(out/latest)['status']=='PASS'
cli=next((p.parent/'playwright-cli.js' for p in (Path.home()/'.npm/_npx').glob('*/node_modules/@playwright/cli/package.json') if json.loads(p.read_text()).get('version')=='0.1.22'),None)
assert cli,'Existing pinned Playwright CLI required'
command=['node',str(cli),'--session=northstar-phase10b2-release']
code='''async page=>{
 const assert=(v,m)=>{if(!v)throw Error(m);};let blocked=0;const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/v1/**',route=>{if(!['GET','HEAD','OPTIONS'].includes(route.request().method())){blocked++;return route.abort();}return route.continue();});
 const origin='http://127.0.0.1:3100';
 const health=await page.request.get(origin+'/api/v1/health');assert(health.ok(),'Live health');
 assert(health.headers()['x-northstar-test-database']==='false','Must verify actual personal origin');
 assert((await health.json()).migrationVersion==='009.05','Live version009.05');
 await page.setViewportSize({width:1440,height:900});await page.goto(origin+'/courses');
 await page.getByRole('heading',{name:'独立原创课程',exact:true}).waitFor();
 const catalog=await (await page.request.get(origin+'/api/v1/books')).json();
 assert(catalog.books.length===4,'Four existing catalogs');assert(catalog.standaloneLessons.some(l=>l.id==='demo-01'),'Preserved Demo entry');
 assert(catalog.standaloneLessons.every(l=>!l.id.startsWith('fixture-')),'No isolated fixture copied into personal DB');
 assert(await page.locator('.book-card').count()===4,'Real deployed new catalog UI');
 await page.locator('.book-card').first().getByRole('button',{name:'查看实际课程'}).click();
 await page.getByText('本册尚无已导入课程',{exact:true}).waitFor();
 assert(await page.locator('.book-card').first().getByRole('link').count()===0,'No fake textbook study links');
 await page.screenshot({path:'output/playwright/phase10b2-deployed-catalog.png'});
 assert(blocked===0,'Catalog unexpectedly attempted a browser write');assert(errors.length===0,'Live page errors');
 return {passed:true,sourceVersion:'009.05',books:4,preservedDemo:true,isolatedFixturesAbsent:true,browserWriteRequests:blocked,pageErrors:errors};
}'''
try:
 deploy.command(out,'live-browser-open',command+['open','about:blank'])
 deploy.command(out,'live-browser-snapshot',command+['snapshot'])
 p=deploy.command(out,'live-readonly-browser',command+['run-code',code])
 assert re.search(r'"passed"\s*:\s*true',p.stdout.decode()) and '### Error' not in p.stdout.decode()
finally:deploy.command(out,'live-browser-close',command+['close'],expected=(0,1))
