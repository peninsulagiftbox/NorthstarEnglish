// Read-only focused UI audit; not a complete WCAG conformance claim.
async page => {
 const base=new URL(page.url()).origin,checks=[],ratios=[];let blockedWrites=0;
 const assert=(ok,message)=>{if(!ok)throw Error(message);};
 page.setDefaultTimeout(15000);
 await page.route('**/api/v1/**',route=>{if(!['GET','HEAD','OPTIONS'].includes(route.request().method())){blockedWrites++;return route.abort('blockedbyclient');}return route.continue();});
 try{
 for(const path of ['/dashboard','/reports','/settings','/lesson/demo-01?version=demo-01-v2&tab=dictation&sentence=demo-01-v2-s06']){
  await page.setViewportSize({width:1440,height:900});await page.goto(base+path);await page.getByRole('heading',{level:1}).waitFor();
  if(path.includes('lesson/'))await page.getByLabel('本句听写草稿',{exact:true}).waitFor();
  else if(path==='/settings')await page.getByRole('button',{name:'保存偏好',exact:true}).waitFor();
  else await page.getByRole('heading',{name:path==='/dashboard'?'六步学习路径':'真实行为与样本',exact:true}).waitFor();
  const result=await page.evaluate(()=>{
   const rgb=s=>(s.match(/[\d.]+/g)||[]).map(Number);
   const lum=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
   return [...document.querySelectorAll('.muted,.boundary,.intro,.sync-status,.message')].filter(e=>e.getClientRects().length&&e.textContent.trim()).map(e=>{
    let n=e,bg=null,complex=false;while(n){const style=getComputedStyle(n),c=rgb(style.backgroundColor);if(style.backgroundImage!=='none')complex=true;if(c.length===3||c[3]===1){bg=c;break;}n=n.parentElement;}
    if(complex||!bg)return null;const fg=rgb(getComputedStyle(e).color),l1=lum(fg),l2=lum(bg);return {className:e.className,foreground:fg,background:bg,ratio:(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05)};
   }).filter(Boolean);
  });
  assert(result.length>0,'Contrast samples exist');assert(result.every(r=>r.ratio>=4.5),'Secondary text contrast below4.5: '+JSON.stringify(result.filter(r=>r.ratio<4.5)));
  ratios.push({path,samples:result.length,minimum:Math.min(...result.map(r=>r.ratio))});
  const missing=await page.locator('input:not([type=hidden]),textarea,select').evaluateAll(nodes=>nodes.filter(e=>!e.labels?.length&&!e.getAttribute('aria-label')&&!e.getAttribute('aria-labelledby')).map(e=>e.tagName));assert(missing.length===0,'Form labels');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'1440 no overflow');
  await page.screenshot({path:'docs/evidence/phase-09r/screenshots/audit-'+path.split('?')[0].replaceAll('/','-')+'-1440.png'});
  await page.setViewportSize({width:375,height:900});await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'375 no overflow');
  if(path.includes('lesson/'))assert(await page.locator('.player-bar').evaluate(e=>{const r=e.getBoundingClientRect();return r.left===0&&r.right<=innerWidth&&Math.abs(r.bottom-innerHeight)<1;}),'Mobile player remains in viewport');
  await page.screenshot({path:'docs/evidence/phase-09r/screenshots/audit-'+path.split('?')[0].replaceAll('/','-')+'-375.png'});
 }
 checks.push('Secondary text >=4.5 on sampled solid backgrounds (gradients excluded)','Visible form controls labeled','1440/375 no overflow');
 return {passed:true,checks,ratios,blockedWrites,scope:'Focused contrast/labels/layout; keyboard and dialog checks in release-boundaries'};
 }finally{ /* Keep write interception active until the CLI closes this browser. */ }
}
