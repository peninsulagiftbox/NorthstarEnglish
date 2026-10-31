async page => {
 const response = await page.request.get(new URL(page.url()).origin+'/api/v1/health');
 if(response.headers()['x-northstar-test-database']!=='true')throw Error('isolated target required');
 return page.evaluate(async()=>{
  const bytes=await (await fetch('/api/v1/audio/c1-shared-v1-a1')).arrayBuffer();
  const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  const ac=new AudioContext({sampleRate:48000});
  try {
   const decoded=await ac.decodeAudioData(bytes.slice(0));const pcm=decoded.getChannelData(0).slice(0,72000);
   let binary='';for(const b of new Uint8Array(pcm.buffer))binary+=String.fromCharCode(b);
   return {status:'MP3 decode reference; no sound played',captures:[{rate:'shared-mp3-reference',
    assetSha256:hash,source:'Chrome decodeAudioData first 1500ms; source PCM marker at 800ms',
    sampleRate:decoded.sampleRate,totalFrames:decoded.length,frames:pcm.length,pcmBase64:btoa(binary)}]};
  } finally {await ac.close();}
 });
}
