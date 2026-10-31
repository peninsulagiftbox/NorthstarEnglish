// Run inside the pinned Playwright CLI against the loopback measurement proxy.
async page => {
 const origin='http://127.0.0.1:3185';
 await page.goto(origin+'/lesson/c1-shared?version=c1-shared-v1&tab=text');
 await page.getByRole('slider').waitFor();
 await page.evaluate(async()=>{
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const ac=new AudioContext({sampleRate:48000}); await ac.resume();
  const code=`class Tap extends AudioWorkletProcessor {
   process(inputs,outputs){const input=inputs[0]?.[0];const out=outputs[0][0];if(input)out.set(input);
    const pcm=out.slice();this.port.postMessage({frame:currentFrame,pcm},[pcm.buffer]);return true;}
  }registerProcessor('c01-tap',Tap);`;
  const url=URL.createObjectURL(new Blob([code],{type:'text/javascript'}));await ac.audioWorklet.addModule(url);URL.revokeObjectURL(url);
  const tap=new AudioWorkletNode(ac,'c01-tap',{outputChannelCount:[1]});tap.connect(ac.destination);
  const stream=ac.createMediaStreamDestination();tap.connect(stream);
  const audio=document.querySelector('audio');const input=ac.createMediaElementSource(audio);input.connect(tap);
  let blocks=[],active=false,events=[],chunks=[],recorder;
  tap.port.onmessage=e=>{if(active)blocks.push(e.data);};
  const stamp=e=>{if(active)events.push({event:e.type,at:performance.now(),context:ac.currentTime,media:audio.currentTime,paused:audio.paused,seeking:audio.seeking,playbackRate:audio.playbackRate,defaultPlaybackRate:audio.defaultPlaybackRate,visibility:document.visibilityState});};
  for(const name of ['play','playing','pause','seeking','seeked','ended'])audio.addEventListener(name,stamp);
  const save=async(name,data)=>{const r=await fetch('/__c01/save/'+name,{method:'POST',body:data});if(r.status!==201)throw Error('save '+name+' '+r.status);};
  window.c01={ac,tap,audio,wait,events:()=>events,
   begin:async()=>{blocks=[];events=[];chunks=[];active=true;recorder=new MediaRecorder(stream.stream,{mimeType:'audio/webm;codecs=opus'});recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};recorder.start();await wait(300);},
   end:async name=>{await wait(350);await new Promise(r=>{recorder.onstop=r;recorder.stop();});active=false;
    const gaps=[];let n=0;for(let i=0;i<blocks.length;i++){n+=blocks[i].pcm.length;if(i&&blocks[i].frame!==blocks[i-1].frame+blocks[i-1].pcm.length)gaps.push({index:i,expected:blocks[i-1].frame+blocks[i-1].pcm.length,actual:blocks[i].frame});}
    const pcm=new Float32Array(n);let offset=0;for(const b of blocks){pcm.set(b.pcm,offset);offset+=b.pcm.length;}
    await save(name+'.f32',pcm.buffer);const webm=await new Blob(chunks).arrayBuffer();await save(name+'.webm',webm);
    const decoded=await ac.decodeAudioData(webm.slice(0));await save(name+'.opus.f32',decoded.getChannelData(0).buffer);
    const meta={name,sampleRate:ac.sampleRate,firstFrame:blocks[0]?.frame,frames:n,gaps,events,visibility:document.visibilityState,actualRate:audio.playbackRate,
      browser:navigator.userAgent,baseLatency:ac.baseLatency,outputLatency:ac.outputLatency,
      outputPath:'HTMLAudioElement -> MediaElementSource -> pass-through AudioWorklet -> AudioContext.destination; parallel same-tap Opus',
      blocks:blocks.map(b=>({frame:b.frame,length:b.pcm.length}))};
    await save(name+'.json',JSON.stringify(meta));return {name,frames:n,gaps,events:events.length};},
   reference:async(asset,rate,name)=>{const a=new Audio('/api/v1/audio/'+asset);a.playbackRate=rate;a.preservesPitch=true;
    const s=ac.createMediaElementSource(a);s.connect(tap);await window.c01.begin();
    const ended=new Promise((r,j)=>{a.onended=r;a.onerror=j;});await a.play();await ended;
    const result=await window.c01.end(name);s.disconnect();a.remove();return result;},
   known:async()=>{const data=new Float32Array(48000);let seed=71;for(let i=0;i<data.length;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;data[i]=(seed/4294967296-.5)*.2;}
    const buffer=ac.createBuffer(1,data.length,48000);buffer.copyToChannel(data,0);const source=ac.createBufferSource();source.buffer=buffer;source.connect(tap);
    await window.c01.begin();const start=ac.currentTime+.2;source.start(start);await new Promise(r=>source.onended=r);
    const result=await window.c01.end('known-pcm');await save('known-pcm-input.f32',data.buffer);await save('known-pcm-schedule.json',JSON.stringify({startFrame:Math.round(start*48000),sampleRate:48000}));source.disconnect();return result;}
  };
  await wait(1200);
 });
 return {ready:true,known:await page.evaluate(()=>window.c01.known())};
}
