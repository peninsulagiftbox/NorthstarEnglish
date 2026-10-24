// Read-only UI verification; all writes intercepted and practice data mocked.
async page=>{
 const errors=[],results=[];let writes=0;page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(12000);
 await page.route('**/api/v1/**',async route=>{const r=route.request(),u=new URL(r.url());if(r.method()!=='GET'){writes++;return route.fulfill({json:{rowVersion:writes}});}
  if(u.pathname==='/api/v1/recordings')return route.fulfill({json:{state:'not_started',recordings:[]}});
  if(u.pathname==='/api/v1/writing')return route.fulfill({json:{taskId:'controls-fixture',prompt:'Write a short reply.',sourceSentenceIds:[],draft:{text:'',rowVersion:1},state:'not_started',revisions:[]}});
  if(u.pathname==='/api/v1/quiz')return route.fulfill({json:{questions:[],state:'not_started',history:[]}});
  return route.continue();
 });
 const assert=(v,m)=>{if(!v)throw Error(m);},toolbar=()=>page.locator('[aria-label="内容显示设置"]');
 const url=(tab,english=1,translation=1)=>`http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=${tab}&sentence=demo-01-v2-s01&english=${english}&translation=${translation}`;
 for(const width of [1440,375]){
  await page.setViewportSize({width,height:900});
  for(const [tab,labels] of [['text',['隐藏译文','盲听模式']],['dictation',[]],['vocabulary',['隐藏译文']],['speaking',['盲听模式']],['writing',[]],['quiz',[]]]){
   await page.goto(url(tab));await page.locator('#lesson-panel').waitFor();
   const actual=await toolbar().locator('button').allTextContents();assert(JSON.stringify(actual)===JSON.stringify(labels),`${width}/${tab} controls ${actual}`);
   if(!labels.length)assert(await toolbar().count()===0,`${tab} no empty toolbar`);
   if(tab==='dictation')assert(await page.locator('.tutor-current').first().textContent().then(t=>t.includes('目标文本已隐藏')),'Dictation keeps blind protection');
   results.push({width,tab,buttons:actual});
  }
  await page.goto(url('text'));await toolbar().waitFor();await toolbar().getByRole('button',{name:'隐藏译文',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.sentence .translation').length===0);
  await toolbar().getByRole('button',{name:'盲听模式',exact:true}).click();await toolbar().getByRole('button',{name:'显示英文',exact:true}).waitFor();assert(await toolbar().locator('button').allTextContents().then(a=>JSON.stringify(a)==='["显示英文"]'),'Blind text hides ineffective translation control');
  await toolbar().getByRole('button',{name:'显示英文',exact:true}).click();await toolbar().getByRole('button',{name:'显示译文',exact:true}).waitFor();assert(await toolbar().getByRole('button',{name:'显示译文',exact:true}).isVisible(),'English restoration preserves translation preference');
  await page.getByRole('tab',{name:'精听听写',exact:true}).click();await page.getByRole('tab',{name:'精听听写',exact:true,selected:true}).waitFor();assert(await toolbar().count()===0,'Dictation hides controls after tab switch');await page.getByRole('tab',{name:'课文',exact:true}).click();await toolbar().getByRole('button',{name:'显示译文',exact:true}).waitFor();assert(await toolbar().getByRole('button',{name:'显示译文',exact:true}).isVisible(),'Dictation did not change translation preference');assert(await toolbar().getByRole('button',{name:'盲听模式',exact:true}).isVisible(),'Dictation did not change English preference');
  await page.goto(url('vocabulary'));await page.locator('.vocabulary-source').waitFor();assert(await page.locator('.vocabulary-source p').count()===2,'Vocabulary source translation shown');await toolbar().getByRole('button',{name:'隐藏译文',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.vocabulary-source p').length===1);
  await page.goto(url('vocabulary',0));await page.getByRole('button',{name:'显示英文并开始精读',exact:true}).waitFor();assert(await toolbar().count()===0,'Blind vocabulary has no ineffective controls');await page.getByRole('button',{name:'显示英文并开始精读',exact:true}).click();await page.locator('.vocabulary-grid').waitFor();assert(await toolbar().getByRole('button',{name:'隐藏译文',exact:true}).isVisible(),'Vocabulary has explicit restore path');
  await page.goto(url('speaking'));await page.locator('.speaking-target').waitFor();await toolbar().getByRole('button',{name:'盲听模式',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.speaking-target')?.textContent.includes('原文已隐藏'));await toolbar().getByRole('button',{name:'显示英文',exact:true}).click();await page.locator('.speaking-target p[lang=en]').waitFor();
  await page.goto(url('dictation'));await page.locator('#dictation-text').waitFor();await page.screenshot({path:`docs/evidence/context-controls/dictation-${width}.png`});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow');
 }
 assert(!errors.length,errors.join(';'));return{passed:true,results,workingControls:true,dictationPreferencesPreserved:true,interceptedWrites:writes,pageErrors:errors};
}
