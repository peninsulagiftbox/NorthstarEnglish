// Compare simultaneous raw PCM and Opus capture of real decoded MP3 output.
// This is a calibration experiment, not a substitute for 240 boundary measurements.
async page => {
 const origin = new URL(page.url()).origin;
 if ((await page.request.get(origin+'/api/v1/health')).headers()['x-northstar-test-database'] !== 'true') throw Error('isolated target required');
 const result = await page.evaluate(async () => {
  const captures = [], base64 = data => { let s=''; for(const x of new Uint8Array(data)) s+=String.fromCharCode(x); return btoa(s); };
  const uri='/api/v1/audio/c1-independent-v1-a1';
  const encoded=await (await fetch(uri)).arrayBuffer();
  const decoder=new AudioContext({sampleRate:48000});
  const reference=await decoder.decodeAudioData(encoded.slice(0));
  captures.push({rate:'mp3-reference',type:'Chrome decodeAudioData MP3 reference',sampleRate:reference.sampleRate,frames:reference.length,pcmBase64:base64(reference.getChannelData(0).buffer)});
  await decoder.close();
  for(const rate of [.75,1,1.25,1.5]) {
   const a=new Audio(uri); a.preload='auto'; a.playbackRate=rate; a.preservesPitch=true;
   document.body.append(a);
   let ac,stream,recorder,source,node,workletUrl;
   try {
    await a.play(); a.pause(); a.currentTime=0;
    if(a.seeking) await new Promise((resolve,reject)=>{a.addEventListener('seeked',resolve,{once:true});setTimeout(()=>reject(Error('seek calibration timeout')),5000);});
    stream=a.captureStream(); if(!stream.getAudioTracks().length) throw Error('no captured audio track');
    ac=new AudioContext({sampleRate:48000}); await ac.resume();
    workletUrl=URL.createObjectURL(new Blob([`class Raw extends AudioWorkletProcessor {
      process(inputs,outputs){const x=inputs[0]?.[0];const pcm=x?new Float32Array(x):new Float32Array(128);
       this.port.postMessage({frame:currentFrame,pcm},[pcm.buffer]); return true;}
     } registerProcessor('r-raw',Raw);`],{type:'text/javascript'}));
    await ac.audioWorklet.addModule(workletUrl);
    source=ac.createMediaStreamSource(stream);node=new AudioWorkletNode(ac,'r-raw');
    source.connect(node);node.connect(ac.destination);
    const blocks=[];node.port.onmessage=e=>blocks.push(e.data);
    const chunks=[];recorder=new MediaRecorder(stream,{mimeType:'audio/webm;codecs=opus'});
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
    const stopped=new Promise(resolve=>recorder.onstop=resolve);
    recorder.start();await new Promise(resolve=>setTimeout(resolve,300));
    const begin={performance:performance.now(),contextTime:ac.currentTime,media:a.currentTime};
    const ended=new Promise((resolve,reject)=>{a.addEventListener('ended',resolve,{once:true});setTimeout(()=>reject(Error('calibration playback timeout')),10000);});
    await a.play();await ended;
    const end={performance:performance.now(),contextTime:ac.currentTime,media:a.currentTime};
    await new Promise(resolve=>setTimeout(resolve,300));
    recorder.stop();await stopped;node.port.onmessage=null;
    const webm=await new Blob(chunks).arrayBuffer(); const decoded=await ac.decodeAudioData(webm.slice(0));
    let total=0;for(const block of blocks)total+=block.pcm.length;
    const raw=new Float32Array(total);let at=0;const gaps=[];
    for(let i=0;i<blocks.length;i++){const b=blocks[i];raw.set(b.pcm,at);at+=b.pcm.length;
     if(i&&b.frame!==blocks[i-1].frame+blocks[i-1].pcm.length)gaps.push({index:i,previous:blocks[i-1].frame,frame:b.frame});}
    captures.push({rate,type:'simultaneous raw/Opus browser capture',actualRate:a.playbackRate,preservesPitch:a.preservesPitch,
     visibility:document.visibilityState,sampleRate:ac.sampleRate,rawFrames:raw.length,rawFirstFrame:blocks[0]?.frame,rawBlocks:blocks.length,rawBlockGaps:gaps,
     opusFrames:decoded.length,opusSampleRate:decoded.sampleRate,begin,end,
     encodedBase64:base64(webm),pcmBase64:base64(decoded.getChannelData(0).buffer),rawBase64:base64(raw.buffer)});
   } finally {
    a.pause();a.remove();if(recorder?.state==='recording')recorder.stop();
    node?.disconnect();source?.disconnect();if(ac)await ac.close();
    if(stream)for(const t of stream.getTracks())t.stop();if(workletUrl)URL.revokeObjectURL(workletUrl);
   }
  }
  return {status:'CALIBRATION EXPERIMENT',captures,acceptanceStatus:'NOT VERIFIED',validAcceptanceMeasurements:0};
 });
 return result;
}
