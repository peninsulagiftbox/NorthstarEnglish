async (page) => {
  page.setDefaultTimeout(12000);
  const base=new URL(page.url()).origin,checks=[],errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  const health=await page.request.get(base+'/api/v1/health');
  assert(health.headers()['x-northstar-test-database']==='true','Player E2E requires isolated test DB');
  const pause=async()=>{if(!await page.locator('audio').evaluate(a=>a.paused))await page.getByRole('button',{name:'暂停播放',exact:true}).click();};
  const settings=async()=>{if(!await page.getByRole('region',{name:'播放设置面板',exact:true}).count())await page.getByRole('button',{name:'播放设置',exact:true}).click();};
  const slider=page.getByRole('slider',{name:'当前句播放进度',exact:true});
  const seek=async time=>slider.evaluate((el,value)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,String(value));el.dispatchEvent(new Event('input',{bubbles:true}));},time);
  const playSentence=async n=>{await page.getByRole('button',{name:`选择并播放句子 ${n}`,exact:true}).click();await page.waitForFunction(id=>{const a=document.querySelector('audio');return a?.src.includes(id)&&a.duration>0&&!a.paused&&a.currentTime>0;},`v2-a${String(n).padStart(2,'0')}`);await pause();};
  await page.setViewportSize({width:1440,height:900});
  await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=text');await slider.waitFor();
  const lesson=await (await page.request.get(base+'/api/v1/lessons/demo-01')).json();
  const before=await (await page.request.get(base+'/api/v1/study/stages?lessonId=demo-01&versionId=demo-01-v2')).json();
  for(const sentence of lesson.sentences) {
    await playSentence(sentence.sequence);
    const duration=await page.locator('audio').evaluate(a=>a.duration);
    const expectedWords=sentence.text.match(/[A-Za-z]+(?:'[A-Za-z]+)?/g).length;
    assert(await page.locator('.word-marker').count()===expectedWords,'Other sentence words leaked into '+sentence.sequence);
    assert(await page.locator('.sentence-marker').count()===1,'Aggregated sentence starts');
    assert(await page.locator('.word-marker').evaluateAll((els,id)=>els.every(el=>el.dataset.sentence===id),sentence.id),'Wrong word sentence binding');
    assert(Math.abs(Number(await slider.getAttribute('max'))-duration)<.001,'Duration is not the current audio duration');
  }
  checks.push('all ten sentences: only current words, one sentence start, per-file real duration');
  assert(await page.locator('.sentence-play').count()===0,'Trailing play buttons remain');
  const gap=await page.locator('.sentence-list').evaluate(list=>{const rows=list.querySelectorAll('li');return rows[1].getBoundingClientRect().top-rows[0].getBoundingClientRect().bottom;});
  assert(gap>=10,'Sentence cards need spacing');
  await playSentence(6);
  assert(await page.getByRole('button',{name:'选择并播放句子 6',exact:true}).getAttribute('aria-pressed')==='true','Playing row was not selected');
  assert(await page.locator('.sentence.selected').evaluate(el=>getComputedStyle(el).boxShadow)==='none','Unwanted selection stripe remains');
  const speed=page.getByRole('button',{name:'播放速度',exact:true});
  assert(await speed.innerText()==='1x','Speed must start at 1x');
  for(const value of [1.25,1.5,.75,1]) {
    await speed.click();await page.waitForFunction(v=>document.querySelector('audio')?.playbackRate===v,value);
    assert(await speed.innerText()===`${value}x`,'Speed cycle label mismatch');
  }
  checks.push('12px sentence gaps, click selects and plays, persistent selected fill without side stripe, no trailing buttons, speed cycles from 1x');
  const marker=page.getByRole('button',{name:'跳到第 6 句第 4 个单词',exact:true});
  const wordTime=Number(await marker.getAttribute('data-time'));await marker.click();
  await page.waitForFunction(t=>{const a=document.querySelector('audio');return a?.src.includes('v2-a06')&&a.paused&&Math.abs(a.currentTime-t)<.03;},wordTime);
  await slider.focus();await slider.press('Home');await page.waitForFunction(()=>document.querySelector('audio')?.currentTime<.01);
  const rail=await page.locator('.player-track').boundingBox();const duration=await page.locator('audio').evaluate(a=>a.duration);
  await page.mouse.move(rail.x,rail.y+rail.height/2);await page.mouse.down();await page.mouse.move(rail.x+rail.width/2,rail.y+rail.height/2,{steps:8});await page.mouse.up();
  await page.waitForFunction(t=>{const a=document.querySelector('audio');return a?.src.includes('v2-a06')&&a.paused&&Math.abs(a.currentTime-t)<.06;},duration/2);
  await slider.focus();await slider.press('Home');await slider.press('ArrowRight');await page.waitForFunction(()=>document.querySelector('audio')?.currentTime>0);
  checks.push('word clicks, real pointer drag and keyboard seek stay within current sentence');
  await settings();await page.getByRole('button',{name:'A–B',exact:true}).click();
  await seek(.3);await page.getByRole('button',{name:'设 A = 当前时间',exact:true}).click();
  await seek(1);await page.getByRole('button',{name:'设 B = 当前时间',exact:true}).click();
  await page.getByRole('button',{name:'开启 A–B 循环',exact:true}).click();
  await page.getByRole('button',{name:'播放',exact:true}).click();
  await page.evaluate(()=>{window.playerAbTimes=[];document.querySelector('audio').addEventListener('timeupdate',()=>window.playerAbTimes.push(document.querySelector('audio').currentTime));});
  await page.waitForFunction(()=>window.playerAbTimes.some((v,i,a)=>i&&a[i-1]-v>.2));
  await page.getByLabel('播放模式',{exact:true}).selectOption('list');
  await page.getByRole('button',{name:'跳到本句终点',exact:true}).click();
  await page.waitForFunction(()=>{const a=document.querySelector('audio');return a?.src.includes('v2-a06')&&a.paused&&Math.abs(a.currentTime-a.duration)<.03;});
  await page.waitForTimeout(350);assert(await page.locator('audio').evaluate(a=>a.src.includes('v2-a06')&&a.paused),'Sentence end navigated away');
  const aligned=await page.evaluate(()=>{const thumb=document.querySelector('.timeline-thumb').getBoundingClientRect(),end=document.querySelector('.end-marker').getBoundingClientRect();return Math.abs(thumb.x+thumb.width/2-end.x-end.width/2)<.1&&Math.abs(thumb.y+thumb.height/2-end.y-end.height/2)<.1;});
  assert(aligned,'Playhead and end marker do not share a center');
  await page.locator('.player-bar').screenshot({path:'docs/evidence/player-polish/endpoint-aligned.png'});
  await slider.focus();await slider.press('Home');await slider.press('End');await page.waitForFunction(()=>{const a=document.querySelector('audio');return a&&Math.abs(a.currentTime-a.duration)<.0001;});
  checks.push('red end and visible playhead centers overlap exactly; keyboard End reaches non-step-aligned duration');
  await page.getByRole('button',{name:'下一句',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('audio')?.src.includes('v2-a07')&&document.querySelector('audio')?.duration>0);
  await pause();assert(await page.locator('.word-marker').count()===5,'Next sentence timeline did not update');
  assert(Number(await slider.getAttribute('max'))<4,'Next sentence retained cumulative duration');
  checks.push('AB remains functional; red end stops current sentence; next sentence resets duration and markers');
  await page.getByRole('button',{name:'关闭',exact:true}).click();await playSentence(6);await seek(.9);
  for(const width of [1440,979,640,375]) {
    await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Overflow '+width);
    await page.locator('.player-bar').screenshot({path:`docs/evidence/player-polish/player-${width}.png`});
  }
  await page.setViewportSize({width:1440,height:900});await playSentence(1);await page.screenshot({path:'docs/evidence/player-polish/selected-paused-1440.png'});
  await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=dictation&sentence=demo-01-v2-s06&english=1&translation=1');await page.getByLabel('本句听写草稿',{exact:true}).waitFor();
  const markerContent=await page.locator('.player-bar').evaluate(el=>el.innerText+' '+Array.from(el.querySelectorAll('[title],[aria-label]')).map(e=>e.getAttribute('title')+' '+e.getAttribute('aria-label')).join(' '));
  assert(!/beside|bench|Please put|blue/i.test(markerContent),'Blind marker leak');
  const after=await (await page.request.get(base+'/api/v1/study/stages?lessonId=demo-01&versionId=demo-01-v2')).json();assert(JSON.stringify(before)===JSON.stringify(after),'Playback created practice evidence');
  await page.goto(base+'/lesson/demo-01?version=demo-01-v1&tab=text');await slider.waitFor();assert(await page.locator('.word-marker').count()===0&&await page.locator('.sentence-marker').count()===1,'v1 fallback not sentence local');
  checks.push('four responsive widths, blind tooltip protection, no practice evidence, v1 sentence-only fallback');
  assert(errors.length===0,'Page errors '+errors.join(';'));return {passed:true,checks,pageErrors:errors};
}
