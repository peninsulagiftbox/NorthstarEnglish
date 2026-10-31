async page=>page.evaluate(async()=>{
 const rate=48000,frames=96000,channels=2;
 const config={codec:'opus',sampleRate:rate,numberOfChannels:channels,bitrate:128000};
 if(!globalThis.AudioEncoder||!(await AudioEncoder.isConfigSupported(config)).supported)return {status:'NOT VERIFIED',reason:'Opus WebCodecs encoder unavailable'};
 const signal=new Float32Array(frames);let seed=419;
 for(let i=4800;i<86400;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;signal[i]=(seed/4294967296-.5)*.2;}
 const packets=[];let decoderConfig,error;
 const encoder=new AudioEncoder({output:(chunk,meta)=>{const bytes=new Uint8Array(chunk.byteLength);chunk.copyTo(bytes);packets.push({bytes,timestamp:chunk.timestamp,duration:chunk.duration,type:chunk.type});if(meta.decoderConfig)decoderConfig=meta.decoderConfig;},error:e=>error=String(e)});
 encoder.configure(config);
 for(let at=0;at<frames;at+=960){const data=new Float32Array(960*channels);for(let c=0;c<channels;c++)data.set(signal.subarray(at,at+960),c*960);
  const input=new AudioData({format:'f32-planar',sampleRate:rate,numberOfFrames:960,numberOfChannels:channels,timestamp:at*1e6/rate,data});encoder.encode(input);input.close();}
 await encoder.flush();encoder.close();if(error)throw Error(error);
 const outputs=[];const decoder=new AudioDecoder({output:data=>{const pcm=new Float32Array(data.numberOfFrames);data.copyTo(pcm,{planeIndex:0,format:'f32-planar'});outputs.push({timestamp:data.timestamp,frames:data.numberOfFrames,pcm});data.close();},error:e=>error=String(e)});
 decoder.configure(decoderConfig);
 for(const p of packets)decoder.decode(new EncodedAudioChunk({type:p.type,timestamp:p.timestamp,duration:p.duration,data:p.bytes}));
 await decoder.flush();decoder.close();if(error)throw Error(error);
 const start=Math.min(...outputs.map(x=>x.timestamp));const end=Math.max(...outputs.map(x=>x.timestamp+x.frames*1e6/rate));
 const pcm=new Float32Array(Math.ceil((end-start)*rate/1e6));for(const x of outputs)pcm.set(x.pcm,Math.round((x.timestamp-start)*rate/1e6));
 const save=async(name,data)=>{const r=await fetch('/__c01/save/'+name,{method:'POST',body:data});if(r.status!==201)throw Error('save '+name);};
 await save('webcodecs-opus-input.f32',signal.buffer);await save('webcodecs-opus-decoded.f32',pcm.buffer);
 const desc=decoderConfig.description?Array.from(new Uint8Array(decoderConfig.description)):[];
 const result={status:'ENCODED AND DECODED',config,decoderConfig:{...decoderConfig,description:desc},packets:packets.map(({bytes,...rest})=>({...rest,bytes:bytes.length})),outputs:outputs.map(({pcm,...rest})=>rest),decodedOriginTimestampUs:start,sampleRate:rate,inputFrames:frames,
  description:'Known mathematical noise, explicit input/chunk/output timestamps; codec-only control, independent of MediaRecorder start callbacks and source speech.'};
 await save('webcodecs-opus.json',JSON.stringify(result));return {status:result.status,firstPacket:result.packets[0],firstOutput:result.outputs[0],description:desc};
})
