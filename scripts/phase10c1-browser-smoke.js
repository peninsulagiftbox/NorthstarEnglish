async page => {
 let backgroundAcceptance='NOT VERIFIED',loopCount=0,elementSamples=[];
 const base=new URL(page.url()).origin,checks=[],errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(15000);
 const assert=(v,m)=>{if(!v)throw Error(m);};
 const get=async p=>{const r=await page.request.get(base+'/api/v1'+p);assert(r.ok(),p);return r.json();};
 assert((await page.request.get(base+'/api/v1/health')).headers()['x-northstar-test-database']==='true','isolated DB required');
 try {
 let firstLoadCount=0;
 const lesson=await get('/lessons/c1-shared?versionId=c1-shared-v1');
 const pause=async()=>{if(!await page.locator('audio').evaluate(a=>a.paused))await page.getByRole('button',{name:'暂停播放',exact:true}).click();};
 const settings=async()=>{if(!await page.getByRole('region',{name:'播放设置面板'}).count())await page.getByRole('button',{name:'播放设置',exact:true}).click();};
 const seek=async(value,full=false)=>page.getByRole('slider',{name:full?'整课音轨播放进度':'当前句播放进度',exact:true}).evaluate((el,v)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,String(v));el.dispatchEvent(new Event('input',{bubbles:true}));},value);
 await page.setViewportSize({width:1440,height:900});await page.goto(base+'/lesson/c1-shared?version=c1-shared-v1&tab=text');await page.getByRole('slider').waitFor();
 await page.evaluate(()=>{window.c1Loads=0;document.querySelector('audio').addEventListener('loadstart',()=>window.c1Loads++);});
 for(const n of [1,6,12]) {
  await page.getByRole('button',{name:`选择并播放句子 ${n}`,exact:true}).click();
  await page.waitForFunction(id=>document.querySelector('.player-bar').dataset.sentence===id&&!document.querySelector('audio').paused,'c1-shared-v1-s'+n);await pause();
  if(n===1)firstLoadCount=await page.evaluate(()=>window.c1Loads);
  const segment=lesson.sentences[n-1];assert(Math.abs(await page.getByRole('slider').evaluate(e=>Number(e.max))-(segment.endMs-segment.startMs)/1000)<.002,'segment slider duration');
 }
 assert(await page.evaluate(()=>window.c1Loads)===firstLoadCount,'same asset source reused');checks.push('first/middle/last segment on shared source, source reused');
 await page.getByRole('button',{name:'选择并播放句子 1',exact:true}).click();await pause();await seek(1.5);
 await page.getByText('浏览位置已保存 · 不计练习完成',{exact:true}).waitFor();
 let resume=await get('/study/resume');assert(resume.positionMs>=1499&&resume.positionMs<=1501,'saved segment offset');assert(!resume.fullAssetId,'no full coordinate in segment mode');
 await page.reload();await page.waitForFunction(start=>{const a=document.querySelector('audio');return a?.paused&&Math.abs(a.currentTime-start)<.04;},(lesson.sentences[0].startMs+1500)/1000);
 checks.push('nonzero segment offset saved and refreshed paused');
 // Rapid UI selection: real commands, no artificial metadata/play callbacks.
 for(let i=0;i<20;i++)await page.getByRole('button',{name:`选择并播放句子 ${i%12+1}`,exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.player-bar').dataset.sentence==='c1-shared-v1-s8'&&!document.querySelector('audio').paused);await pause();checks.push('20 rapid same-asset selections retain latest sentence');
 await settings();await page.getByLabel('播放模式',{exact:true}).selectOption('sentence');
 await page.getByRole('button',{name:'选择并播放句子 1',exact:true}).click();
 await page.evaluate(()=>{window.c1Loops=0;window.c1Last=0;window.c1Samples=[];const a=document.querySelector('audio');window.c1Timer=setInterval(()=>{if(!a.paused){if(a.currentTime<window.c1Last-.3)window.c1Loops++;window.c1Last=a.currentTime;window.c1Samples.push({t:performance.now(),asset:a.currentTime});}},10);});
 // All four rates, then ten actual sentence-loop returns at 1.5x.
 const speeds=page.getByRole('button',{name:'播放速度',exact:true});
 for(const rate of [1.25,1.5,.75,1]){await speeds.click();await page.waitForFunction(v=>document.querySelector('audio').playbackRate===v,rate);}
 await speeds.click();await speeds.click();
 await page.waitForFunction(()=>window.c1Loops>=10,{},{timeout:45000});await pause();loopCount=await page.evaluate(()=>window.c1Loops);elementSamples=await page.evaluate(()=>window.c1Samples);await page.evaluate(()=>clearInterval(window.c1Timer));checks.push('four rates and at least 10 sentence loops on real element (not acoustic accuracy)');
 await page.getByLabel('播放模式',{exact:true}).selectOption('sequence');await page.getByRole('button',{name:'选择并播放句子 1',exact:true}).click();await seek((lesson.sentences[0].endMs-lesson.sentences[0].startMs)/1000-.08);await page.waitForFunction(()=>document.querySelector('.player-bar').dataset.sentence==='c1-shared-v1-s2'&&!document.querySelector('audio').paused);await pause();
 await page.getByLabel('播放模式',{exact:true}).selectOption('list');await page.getByRole('button',{name:'选择并播放句子 12',exact:true}).click();await seek((lesson.sentences[11].endMs-lesson.sentences[11].startMs)/1000-.08);await page.waitForFunction(()=>document.querySelector('.player-bar').dataset.sentence==='c1-shared-v1-s1'&&!document.querySelector('audio').paused);await pause();checks.push('native segment-end sequence and list wrap without file ended');
 await page.getByRole('button',{name:'A–B',exact:true}).click();await seek(.3);await page.getByRole('button',{name:'设 A = 当前时间',exact:true}).click();await seek(.8);await page.getByRole('button',{name:'设 B = 当前时间',exact:true}).click();await page.getByRole('button',{name:'开启 A–B 循环',exact:true}).click();
 await page.evaluate(()=>{window.c1AB=0;let last=0;const a=document.querySelector('audio');window.c1ABTimer=setInterval(()=>{if(!a.paused){if(a.currentTime<last-.2)window.c1AB++;last=a.currentTime;}},10);});await page.getByRole('button',{name:'播放',exact:true}).click();await page.waitForFunction(()=>window.c1AB>=3);await pause();await page.evaluate(()=>clearInterval(window.c1ABTimer));checks.push('sentence-offset A/B actual playback and pause');
 await page.getByLabel('播放模式',{exact:true}).selectOption('full');await page.getByRole('slider',{name:'整课音轨播放进度',exact:true}).waitFor();await seek(.2,true);
 await page.waitForFunction(()=>document.querySelector('.player-bar').dataset.sentence==='');assert((await page.getByRole('slider').getAttribute('aria-valuetext')).includes('间隙'),'intro gap has no fake sentence');
 await seek(lesson.sentences[5].startMs/1000+.3,true);await page.waitForFunction(()=>document.querySelector('.player-bar').dataset.sentence==='c1-shared-v1-s6');await page.getByRole('button',{name:'播放',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('audio').paused);await pause();
 await page.getByText('浏览位置已保存 · 不计练习完成',{exact:true}).waitFor();resume=await get('/study/resume');assert(resume.playbackMode==='full'&&resume.fullAssetId==='c1-shared-v1-a1'&&resume.assetPositionMs>resume.positionMs,'full coordinate distinct');
 await page.reload();await page.waitForFunction(ms=>{const a=document.querySelector('audio');return a?.paused&&Math.abs(a.currentTime*1000-ms)<60;},resume.assetPositionMs);checks.push('full track intro/gap and independent full-coordinate refresh');
 await page.screenshot({path:'output/playwright/phase10c1/full-track-1440.png'});
 await page.goto(base+'/lesson/c1-shared?version=c1-shared-v2&tab=text');await page.getByRole('slider').waitFor();assert(await page.locator('audio').evaluate(a=>a.paused),'version change paused');await page.getByRole('button',{name:'选择并播放句子 1',exact:true}).click();await page.waitForFunction(()=>document.querySelector('audio').src.includes('c1-shared-v2-a1'));await pause();checks.push('version changes use new asset, no inherited audio coordinate');
 await page.goto(base+'/lesson/c1-independent?version=c1-independent-v1&tab=text');await page.getByRole('slider').waitFor();
 for(const n of [1,2,3]){await page.getByRole('button',{name:`选择并播放句子 ${n}`,exact:true}).click();await page.waitForFunction(id=>document.querySelector('audio').src.includes(id)&&!document.querySelector('audio').paused,'c1-independent-v1-a'+n);await pause();}
 for(let i=0;i<20;i++)await page.getByRole('button',{name:`选择并播放句子 ${i%3+1}`,exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('audio').src.includes('c1-independent-v1-a2')&&!document.querySelector('audio').paused);await pause();
 checks.push('independent audio resource switching');
 // A real new foreground tab hides this document; sentence playback must pause.
 await page.getByRole('button',{name:'选择并播放句子 1',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('audio').paused);
 const other=await page.context().newPage();await other.bringToFront();
 const hidden=await page.evaluate(()=>document.hidden);
 if(hidden) {await page.waitForFunction(()=>document.querySelector('audio').paused);backgroundAcceptance='PASS';}
 else backgroundAcceptance='NOT VERIFIED: automated browser kept original document visible after native tab change (headless and headed attempts retained)';
 await other.close();await page.bringToFront();if(hidden)assert(await page.locator('audio').evaluate(a=>a.paused),'foreground return never auto-resumes');else await pause();
 checks.push('background policy unit tested; native visibility result reported separately');
 await page.getByText('浏览位置已保存 · 不计练习完成',{exact:true}).waitFor();
 await page.goto(base+'/lesson/c1-long?version=c1-long-v2&tab=text');await page.getByRole('slider').waitFor();await settings();await page.getByLabel('播放模式',{exact:true}).selectOption('full');await page.getByRole('slider',{name:'整课音轨播放进度'}).waitFor();await page.waitForFunction(()=>document.querySelector('audio').duration>600);await seek(645,true);await page.getByText('浏览位置已保存 · 不计练习完成',{exact:true}).waitFor();
 resume=await get('/study/resume');assert(resume.assetPositionMs===645000&&resume.positionMs===5000,'long asset/segment coordinates distinct');await page.reload();await page.waitForFunction(()=>{const a=document.querySelector('audio');return a?.paused&&Math.abs(a.currentTime-645)<.06;});checks.push('660s real track seek/save/refresh at 645000ms with 5000ms segment offset');
 await page.screenshot({path:'output/playwright/phase10c1/long-track-1440.png'});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'desktop no overflow');assert(!errors.length,errors.join(';'));
 return {passed:true,checks,backgroundAcceptance,pageErrors:errors,loopCount,elementSamples,boundaryAcceptance:'NOT VERIFIED: element logs do not measure acoustic output',browser:await page.evaluate(()=>navigator.userAgent)};
 } catch(error) { await page.screenshot({path:'output/playwright/phase10c1/player-failure.png'}); throw Error('after '+(checks.at(-1)??'initial')+': '+error.message+' BODY '+(await page.locator('body').innerText()).slice(-1700)); }

}
