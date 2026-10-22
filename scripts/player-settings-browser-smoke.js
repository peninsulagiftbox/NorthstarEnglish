async(page)=>{
 const checks=[],errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(12000);
 const base=new URL(page.url()).origin,assert=(ok,msg)=>{if(!ok)throw new Error(msg);};
 const health=await page.request.get(base+'/api/v1/health');assert(health.headers()['x-northstar-test-database']==='true','Isolated DB required');
 await page.route('**/api/v1/study/resume',r=>r.request().method()==='GET'?r.fulfill({status:200,contentType:'application/json',body:'null'}):r.abort());
 await page.setViewportSize({width:1440,height:900});
 const open=async()=>{await page.getByRole('button',{name:'播放设置',exact:true}).click();await page.getByRole('region',{name:'播放设置面板',exact:true}).waitFor();};
 const pause=async()=>{if(!await page.locator('audio').evaluate(a=>a.paused))await page.getByRole('button',{name:'暂停播放',exact:true}).click();};
 const seek=async time=>{await page.getByRole('slider',{name:'当前句播放进度',exact:true}).evaluate((el,v)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,String(v));el.dispatchEvent(new Event('input',{bubbles:true}));},time);await page.waitForFunction(t=>Math.abs(document.querySelector('audio').currentTime-t)<.01,time);};
 await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=text&sentence=demo-01-v2-s06');await page.getByRole('button',{name:'播放设置',exact:true}).waitFor();await open();
 assert(await page.getByText('单词时间点由合成语音自动提供，尚未经人工逐词校正。',{exact:true}).isVisible()===false,'Technical notes not collapsed');
 const panel=page.getByRole('region',{name:'播放设置面板',exact:true});await panel.screenshot({path:'docs/evidence/player-settings/default-1440.png'});
 await page.getByRole('button',{name:'A–B',exact:true}).click();await page.getByRole('button',{name:'加载本句',exact:true}).waitFor();await panel.screenshot({path:'docs/evidence/player-settings/unloaded-1440.png'});
 await page.route('**/api/v1/audio/demo-01-v2-a06',async r=>{await new Promise(resolve=>setTimeout(resolve,700));await r.continue();});
 await page.getByRole('button',{name:'加载本句',exact:true}).click();await page.getByRole('button',{name:'加载中…',exact:true,disabled:true}).waitFor();
 await page.waitForFunction(()=>document.querySelector('audio')?.duration>0);await page.unroute('**/api/v1/audio/demo-01-v2-a06');
 assert(await page.locator('audio').evaluate(a=>a.paused),'Loading unexpectedly autoplayed');
 assert(await page.getByRole('button',{name:'设 B = 当前时间',exact:true}).isDisabled(),'B must follow A');
 assert(await page.getByRole('button',{name:'开启 A–B 循环',exact:true}).isDisabled(),'Unconfigured AB is enabled');
 checks.push('compact default, collapsed help, unloaded/loading/loaded states, B follows A');
 await seek(.3);await page.getByRole('button',{name:'设 A = 当前时间',exact:true}).click();await seek(1.2);await page.getByRole('button',{name:'设 B = 当前时间',exact:true}).click();
 await page.getByRole('button',{name:'开启 A–B 循环',exact:true,disabled:false}).waitFor();await panel.screenshot({path:'docs/evidence/player-settings/configured-1440.png'});
 await page.getByRole('button',{name:'开启 A–B 循环',exact:true}).click();await page.getByText('A–B 已开启，点击底部播放即可复读。',{exact:true}).waitFor();
 await page.evaluate(()=>{window.abSamples=[];document.querySelector('audio').addEventListener('timeupdate',()=>window.abSamples.push(document.querySelector('audio').currentTime));});
 await page.getByRole('button',{name:'播放',exact:true}).click();await page.waitForFunction(()=>window.abSamples.some((v,i,a)=>i&&a[i-1]-v>.3));
 await panel.screenshot({path:'docs/evidence/player-settings/running-1440.png'});await pause();await page.getByRole('button',{name:'停止 A–B 循环',exact:true}).click();
 await seek(1.5);await page.getByRole('button',{name:'设 A = 当前时间',exact:true}).click();await page.getByText('终点需晚于起点，请向后定位并重新设置 B。',{exact:true}).waitFor();assert(await page.getByRole('button',{name:'开启 A–B 循环',exact:true}).isDisabled(),'Invalid interval enabled');
 await page.getByRole('button',{name:'清除区间',exact:true}).click();assert(await page.locator('.ab-point output.unset').count()===2,'Clear interval failed');
 checks.push('two time points, valid/invalid instructions, real AB wraps, paused state honest, stop and clear');
 await page.getByText('时间点与复读说明',{exact:true}).click();await page.getByText('单词时间点由合成语音自动提供，尚未经人工逐词校正。',{exact:true}).waitFor();
 for(const [width,height] of [[979,900],[640,900],[375,700]]){await page.setViewportSize({width,height});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Page overflow '+width);const box=await panel.boundingBox();assert(box.x>=0&&box.y>=0&&box.x+box.width<=width&&box.y+box.height<=height-76,'Panel out of bounds');await page.getByRole('button',{name:'开启 A–B 循环',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:`docs/evidence/player-settings/panel-${width}.png`});}
 await page.keyboard.press('Escape');assert(await panel.count()===0,'Escape did not close');assert(await page.getByRole('button',{name:'播放设置',exact:true}).evaluate(e=>e===document.activeElement),'Focus not restored');
 checks.push('help disclosure, 979/640/375 fits viewport and scrolls internally, Escape returns focus');
 await page.setViewportSize({width:1440,height:900});await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=text&sentence=demo-01-v2-s06');await page.getByRole('button',{name:'播放设置',exact:true}).waitFor();await open();await page.getByRole('button',{name:'A–B',exact:true}).click();
 await page.route('**/api/v1/audio/**',r=>r.abort());await page.getByRole('button',{name:'加载本句',exact:true}).click();await panel.getByRole('alert').waitFor();assert(await page.locator('.media-error').count()===0,'Duplicate floating error');await panel.screenshot({path:'docs/evidence/player-settings/error-1440.png'});
 await page.unroute('**/api/v1/audio/**');await page.getByRole('button',{name:'重试播放',exact:true}).click();await page.waitForFunction(()=>{const a=document.querySelector('audio');return a?.duration>0&&!a.paused;});await pause();
 checks.push('inline audio error and real retry recover without duplicate error banner');
 assert(errors.length===0,errors.join(';'));await page.unrouteAll({behavior:'wait'});return{passed:true,checks,pageErrors:errors};
}
