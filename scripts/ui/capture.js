async page => {
 /* AUTH:empty */
 const phase='PHASE',base='http://127.0.0.1:3197',out='output/ui-review/visual-rhythm',results=[];
 const sizes=[[1280,800],[1440,900],[1920,1080],[768,1024],[390,844],[320,844]];
 const routes=[['dashboard','/dashboard'],['courses','/courses'],['review','/review'],['reports','/reports'],['settings','/settings'],...['text','dictation','vocabulary','speaking','writing','quiz'].map(tab=>['lesson-'+tab,'/lesson/demo-01?version=demo-01-v2&tab='+tab])];
 page.setDefaultTimeout(15000);
 async function capture(name,path,width,height) {
  await page.setViewportSize({width,height});await page.goto(base+path);
  await page.locator('#main-content h1').waitFor();
  if(name==='review') await page.getByRole('heading',{name:'当前没有到期的概念卡',exact:true}).waitFor();
  if(name==='populated-review') await page.locator('main>section').filter({has:page.getByRole('button',{name:'刷新概念卡',exact:true})}).locator('.review-card').first().waitFor();
  if(name.includes('lesson-')||name==='populated-quiz') await page.locator('.lesson-card').waitFor();
  if(['dashboard','reports','populated-reports'].includes(name)) await page.locator('.stats-grid').waitFor();
  if(name==='courses') await page.locator('.book-card').first().waitFor();
  if(name==='settings') await page.getByRole('button',{name:'保存偏好',exact:true}).waitFor();
  await page.waitForTimeout(180);
  const metrics=await page.evaluate(()=>{
   const main=document.querySelector('main'),shell=document.querySelector('.main-shell');
   const rect=e=>e.getBoundingClientRect(), box=e=>{const r=rect(e);return{x:r.x,y:r.y,w:r.width,h:r.height,bottom:r.bottom};};
   const toolbar=[...document.querySelectorAll('.toolbar')].find(e=>e.textContent.includes('刷新概念卡'));
   const result=toolbar?.nextElementSibling;
   const first=result?.matches('.review-results')?result.firstElementChild:result;
   const toolbarIssues=[];
   for(const t of document.querySelectorAll('.toolbar')) {
    const r=rect(t),items=[...t.children].filter(e=>rect(e).width>0);
    for(const e of items) {const c=rect(e);if(c.left<r.left-1||c.right>r.right+1) toolbarIssues.push('child outside toolbar');}
    for(let i=0;i<items.length;i++) for(let j=i+1;j<items.length;j++){const a=rect(items[i]),b=rect(items[j]);if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)toolbarIssues.push('toolbar children overlap');}
   }
   const cardIssues=[];for(const card of document.querySelectorAll('.surface')) {const r=rect(card);for(const child of card.children){const c=rect(child);if(c.width>0&&(c.left<r.left-1||c.right>r.right+1||c.top<r.top-1||c.bottom>r.bottom+1))cardIssues.push(child.className||child.tagName);}}
   const panel=document.querySelector('.workspace-grid'),tabs=document.querySelector('.tabs');
   const header=document.querySelector('.topbar');
   return{viewportOverflow:document.documentElement.scrollWidth>innerWidth,mainOverflow:main.scrollWidth>main.clientWidth+1,shellOverflow:shell.scrollWidth>shell.clientWidth+1,toolbarIssues,cardIssues,toolbar:toolbar?box(toolbar):null,firstPanel:first?box(first):null,gap:toolbar&&first?rect(first).top-rect(toolbar).bottom:null,emptyHeight:first?.querySelector('.empty-state')?rect(first).height:null,tabsPanelGap:panel&&tabs?rect(panel).top-rect(tabs).bottom:null,headerMainGap:rect(main).top-rect(header).bottom};
  });
  const file=`${phase}-${name}-${width}.png`;
  await page.screenshot({path:`${out}/${file}`,fullPage:true});
  await page.locator('.main-shell').evaluate(e=>e.scrollTop=e.scrollHeight);
  Object.assign(metrics,await page.evaluate(()=>{const player=document.querySelector('.player-bar'),sync=document.querySelector('.sync-status'),footer=document.querySelector('.review-results > .muted'),shell=document.querySelector('.main-shell');return {playerCoversEnd:!!(player&&sync&&sync.getBoundingClientRect().bottom>player.getBoundingClientRect().top+1),reviewFooterClipped:!!(footer&&footer.getBoundingClientRect().bottom>shell.getBoundingClientRect().bottom+1)};}));
  await page.screenshot({path:`${out}/${phase}-${name}-${width}-bottom.png`});
  if(name.endsWith('review'))await page.locator('main>section').filter({has:page.getByRole('button',{name:'刷新概念卡',exact:true})}).screenshot({path:`${out}/${phase}-${name==='review'?'concepts':'populated-concepts'}-${width}.png`});
  results.push({name,path,width,height,file,...metrics});
 }
 for(const [width,height] of sizes)for(const [name,path]of routes)await capture(name,path,width,height);
 /* AUTH:populated */
 for(const [width,height]of [[1440,900],[768,1024],[390,844]])for(const [name,path]of [['populated-review','/review'],['populated-quiz','/lesson/teaching-a?version=teaching-a-v1&tab=quiz'],['populated-reports','/reports']])await capture(name,path,width,height);
 await page.context().clearCookies();
 for(const [width,height]of sizes) {
  await page.setViewportSize({width,height});await page.goto(base+'/login');await page.getByRole('button',{name:'注册新账户',exact:true}).waitFor();
  await page.screenshot({path:`${out}/${phase}-login-${width}.png`,fullPage:true});
  await page.getByRole('button',{name:'注册新账户',exact:true}).click();await page.getByLabel('怎么称呼你').waitFor();
  await page.screenshot({path:`${out}/${phase}-register-${width}.png`,fullPage:true});
  const overflow=await page.locator('.login-page').evaluate(e=>e.scrollWidth>e.clientWidth+1);
  results.push({name:'auth',width,height,overflow});
 }
 return results;
}
