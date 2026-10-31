async page => {
 const {rate,track,index,name}=windowGroup;
 const n=track==='shared'?[1,6,12][index]:index+1;
 if(!await page.getByRole('region',{name:'播放设置面板'}).count())await page.getByRole('button',{name:'播放设置',exact:true}).click();
 await page.getByLabel('播放模式',{exact:true}).selectOption('sentence');
 for(let k=0;await page.getByRole('button',{name:'播放速度',exact:true}).getAttribute('data-speed')!==String(rate);k++){
  if(k>4)throw Error('speed selection');await page.getByRole('button',{name:'播放速度',exact:true}).click();
 }
 await page.evaluate(()=>window.c01.begin());
 await page.getByRole('button',{name:`选择并播放句子 ${n}`,exact:true}).click();
 await page.waitForFunction(rate=>document.querySelector('audio').playbackRate===rate,rate);
 const bounds=await page.evaluate(()=>({time:document.querySelector('audio').currentTime,visibility:document.visibilityState,actualRate:document.querySelector('audio').playbackRate}));
 await page.waitForFunction(()=>window.c01.events().filter(x=>x.event==='seeking').length>=11,null,{timeout:65000});
 // The initial selection seeks once; ten further acoustic restarts delimit ten complete cycles.
 await page.waitForTimeout(180);
 await page.getByRole('button',{name:'暂停播放',exact:true}).click();
 return {rate,track,index,bounds,capture:await page.evaluate(name=>window.c01.end(name),name)};
}
