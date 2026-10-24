// Mocked writing API only; all other application writes are intercepted.
async page=>{
 const base='http://127.0.0.1:3100',errors=[],posts=[],receipts=new Map();let failPost=true,failClear=false,concurrent=false,clears=0,blocked=0;
 page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push(e.message));
 const state={taskId:'demo-01-v2-writing-01',prompt:'Write about helping in a garden.',sourceSentenceIds:['demo-01-v2-s06'],draft:{text:'',rowVersion:1},state:'not_started',revisions:[]};
 const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname;
  if(path==='/api/v1/writing' && req.method()==='GET')return route.fulfill({json:state});
  if(path==='/api/v1/writing/draft' && req.method()==='PUT'){
   const body=req.postDataJSON();if(body.rowVersion!==state.draft.rowVersion)return route.fulfill({status:412,json:{detail:'测试：另一页面已更新草稿'}});
   if(body.text==='' && failClear)return route.fulfill({status:503,json:{detail:'测试：清空暂不可用'}});
   if(body.text==='')clears++;
   state.draft={text:body.text,rowVersion:state.draft.rowVersion+1};return route.fulfill({json:{rowVersion:state.draft.rowVersion}});
  }
  if(path==='/api/v1/writing/revisions' && req.method()==='POST'){
   const body=req.postDataJSON();posts.push(body);
   if(failPost)return route.fulfill({status:503,json:{detail:'测试：保存暂不可用'}});
   if(receipts.has(body.eventId))return route.fulfill({json:receipts.get(body.eventId)});
   const saved={id:await page.evaluate(()=>crypto.randomUUID()),versionNo:state.revisions.length+1,text:body.text,createdAt:'2026-10-24T04:00:00Z',parentRevisionId:body.parentRevisionId};
   state.revisions.push(saved);state.state='practiced';receipts.set(body.eventId,saved);
   if(concurrent)state.draft={text:'Other page newer draft.',rowVersion:state.draft.rowVersion+1};
   return route.fulfill({json:saved});
  }
  if(!['GET','HEAD'].includes(req.method())){blocked++;return route.fulfill({json:{rowVersion:2,state:'in_progress'}});}
  return route.continue();
 });
 await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=writing&sentence=demo-01-v2-s06');
 const editor=page.getByLabel('写作草稿',{exact:false});await editor.waitFor();
 await editor.fill('Please help me. I can bring water.');
 await page.getByRole('button',{name:'保存新版本',exact:true}).click();
 await page.locator('.writing-editor .message.error').waitFor();
 assert(await editor.inputValue()==='Please help me. I can bring water.','Failed save erased text');assert(state.revisions.length===0 && clears===0,'Failed save cleared draft');
 failPost=false;await page.getByRole('button',{name:'重试待确认版本',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('#writing-text')?.value==='');
 assert(state.revisions.length===1 && state.revisions[0].text==='Please help me. I can bring water.','Immutable text lost');
 assert(state.draft.text==='' && clears===1,'Server draft not cleared');
 assert(posts[0].eventId===posts[1].eventId,'Retry changed event');
 await page.reload();await editor.waitFor();assert(await editor.inputValue()==='','Refresh resurrected saved draft');
 await page.getByRole('button',{name:'回载 V1 到草稿',exact:true}).click();await page.getByRole('button',{name:'确认回载',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('#writing-text')?.value==='Please help me. I can bring water.');
 await page.getByRole('button',{name:'保存新版本',exact:true}).click();await page.getByText('新版本已保存，输入已清空；历史内容保持不变',{exact:true}).waitFor();
 assert(state.revisions[1].parentRevisionId===state.revisions[0].id,'Reloaded parent missing');
 await editor.fill('A fresh independent version.');await page.getByRole('button',{name:'保存新版本',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#writing-text')?.value==='');
 assert(state.revisions[2].parentRevisionId===null,'Cleared draft kept previous parent');
 failClear=true;await editor.fill('Preserve text if clearing fails.');await page.getByRole('button',{name:'保存新版本',exact:true}).click();
 await page.locator('.writing-editor .message.error').filter({hasText:'新版本已保存，但草稿未能完整清空'}).waitFor();
 assert(await editor.inputValue()==='Preserve text if clearing fails.' && state.revisions.length===4,'Clear failure lost text or saved history');
 failClear=false;await page.reload();await editor.waitFor();concurrent=true;const before=clears;
 await editor.fill('Submitted snapshot before another page edits.');await page.getByRole('button',{name:'保存新版本',exact:true}).click();
 await page.getByText('新版本已保存；草稿已有其他修改，保留当前输入',{exact:true}).waitFor();
 assert(state.draft.text==='Other page newer draft.' && clears===before,'Newer draft was erased');
 assert(await editor.inputValue()==='Submitted snapshot before another page edits.','Current input lost on concurrency');
 await page.setViewportSize({width:375,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile overflow');
 assert(errors.length===0,errors.join(';'));
 return{passed:true,checks:['Failed save preserves input','Success clears input/local/server drafts and refresh stays blank','Immutable history preserved','Reload parent reset after save','Clear failure preserves text and saved version','Another page newer draft not cleared'],simulatedRevisions:state.revisions.length,blockedOtherWrites:blocked,pageErrors:errors};
}
