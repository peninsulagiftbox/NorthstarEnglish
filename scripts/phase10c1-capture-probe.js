// Capability probe only; not a calibrated acoustic-boundary measurement.
async page => {
 const base=new URL(page.url()).origin;
 const health=await page.request.get(base+'/api/v1/health');if(health.headers()['x-northstar-test-database']!=='true')throw Error('isolated target required');
 await page.goto(base+'/lesson/c1-shared?version=c1-shared-v1&tab=text');await page.getByRole('button',{name:'选择并播放句子 1',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('audio').paused);
 const capture=await page.evaluate(async()=>{
  const a=document.querySelector('audio');
  if(!a.captureStream||!window.MediaRecorder)return {supported:false,reason:'Browser output capture unavailable'};
  const stream=a.captureStream();if(!stream.getAudioTracks().length)return {supported:false,reason:'No output audio track'};
  const chunks=[],recorder=new MediaRecorder(stream,{mimeType:'audio/webm;codecs=opus'});
  const finished=new Promise(resolve=>recorder.onstop=resolve);recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};recorder.start();await new Promise(r=>setTimeout(r,800));recorder.stop();await finished;
  const blob=new Blob(chunks,{type:recorder.mimeType}),encoded=await blob.arrayBuffer();
  const ac=new AudioContext();let decoded;
  try{const pcm=await ac.decodeAudioData(encoded.slice(0));const samples=pcm.getChannelData(0);let sum=0;for(const x of samples)sum+=x*x;decoded={duration:pcm.duration,sampleRate:pcm.sampleRate,frames:pcm.length,rms:Math.sqrt(sum/samples.length)};}
  finally{await ac.close();stream.getTracks().forEach(t=>t.stop());}
  let bytes='';for(const x of new Uint8Array(encoded))bytes+=String.fromCharCode(x);
  return {supported:true,mimeType:recorder.mimeType,encodedBytes:encoded.byteLength,decoded,base64:btoa(bytes)};
 });
 if(!await page.locator('audio').evaluate(a=>a.paused))await page.getByRole('button',{name:'暂停播放',exact:true}).click();
 return {passed:true,probe:capture,boundaryAcceptance:'NOT VERIFIED',reason:'Capture exists but device/output delay, encoder delay, marker mapping and <=30ms measurement uncertainty have not been calibrated; no acoustic PASS.',manualListening:'NOT VERIFIED'};
}
