#!/usr/bin/env python3
"""Build a local-only listening companion from evaluate-edge-tts.py results."""
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.local/tts-evaluation'
if '--stop' in __import__('sys').argv:
    import local, os, signal, time
    record=local.LOCAL/'tts-preview.json'
    if record.exists():
        value=json.loads(record.read_text())
        if not local.owns_process(value): raise RuntimeError('Preview PID/cwd mismatch; refuse stop')
        os.kill(value['pid'],signal.SIGTERM)
        for _ in range(40):
            if not local.owns_process(value): break
            time.sleep(.25)
        else: raise RuntimeError('Preview still running; preserve process record')
        record.unlink()
    print('Stopped only the owned TTS comparison preview; learning services untouched.')
    raise SystemExit(0)
results=json.loads((OUT/'results.json').read_text())
assert len(results['files'])==30,'All 30 baseline/candidate files must be decoded first'
preview=OUT/'preview';preview.mkdir(exist_ok=True)
for row in results['files']:
    for kind,original in [('normalized',OUT/row['normalizedPath']),('raw',OUT/row['path'])]:
        target=preview/kind/row['group']/original.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,target)
# Fixed blinded order; revealed only on demand. This is a convenience, not a
# preregistered or independent double-blind listening experiment.
config={'order':['edge-us','current','edge-gb'],'labels':{'current':'现有音频 · 合成引擎未知','edge-gb':'Edge 英式 · Sonia / Ryan','edge-us':'Edge 美式 · Aria / Guy'},'files':results['files'],'summary':results['summary']}
data=json.dumps(config,ensure_ascii=False).replace('<','\\u003c')
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Northstar · 语音试听对比</title>
<style>:root{color-scheme:light}*{box-sizing:border-box}body{font:16px/1.6 system-ui,sans-serif;background:#f5f7fa;color:#192740;margin:0;padding:32px}main{max-width:1000px;margin:auto}h1{margin:4px 0}small,.muted{color:#61748e}.card{background:white;padding:24px;border:1px solid #dce5ee;border-radius:16px;margin:20px 0}.toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap}button,select{font:inherit;border:1px solid #a8bdbb;border-radius:8px;background:white;padding:8px 16px;color:#155e56;cursor:pointer}button.active{background:#087f70;color:white}button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid #47af9d;outline-offset:2px}.choices{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.source{padding:16px;border:1px solid #dce5ee;border-radius:10px}.source button{width:100%}audio{width:100%;margin:18px 0}label{display:inline-flex;align-items:center;gap:6px}.metrics{font-size:12px;display:block;margin-top:8px;color:#61748e}#text{font-size:24px}#status{min-height:30px}details{margin-top:18px}.warning{color:#7c4928}a{color:#087f70}@media(max-width:600px){body{padding:16px}.card{padding:16px}.choices{grid-template-columns:1fr}#text{font-size:21px}}</style>
<main><small>NORTHSTAR ENGLISH · LOCAL AUDIO EVALUATION</small><h1>同一句话，三组声音</h1><p class="muted">10句原创英文；仅试听，不产生练习记录。请比较清晰度、重音、自然度和漏词，不能仅按音量判断。</p>
<section class="card"><div class="toolbar"><label>句子<select id="sentence" aria-label="选择句子"></select></label><label><input id="reveal" type="checkbox">显示来源</label><label><input id="normalized" type="checkbox" checked>等响度副本</label><label>播放速度<select id="rate"><option>.75</option><option selected>1</option><option>1.25</option><option>1.5</option></select></label></div>
<p id="text" lang="en"></p><div class="choices" id="choices"></div><audio id="player" controls preload="metadata"></audio><p role="status" id="status">请选择 A / B / C 开始试听，不会自动播放。</p>
<div class="toolbar"><label>本句总体偏好<select id="vote"><option value="">尚未判断</option><option>A</option><option>B</option><option>C</option><option>无明显差别</option><option>三组均有问题</option></select></label><button id="previous">上一句</button><button id="next">下一句</button><button id="download">下载试听判断</button></div><p class="muted" id="saved"></p></section>
<section class="card"><h2>怎么判断是否值得换</h2><p>先听第6句的 beside、blue bench，再听第1句 community garden、第8句 soil / still wet，以及第3、4句 Mia / Leo。逐句核对疑问句语调、礼貌请求、词尾和停顿。</p><p>只有音频技术验证通过，且试听确认整体更自然、无新的错读或漏词，才满足更换条件。未人工判断的维度保持“未验证”，不生成MOS或专业发音分数。</p><details><summary>等响度处理说明</summary><p>试听副本只施加恒定增益，目标为能量超过−45dBFS的10ms帧均方根−22dBFS，峰值最多−1dBFS。不降噪、不变速、不删停顿。关闭开关可听原始MP3。该能量统计不是语音识别或发音评分。</p></details><p class="warning">英式声音已获选，课程版本以工作台显示为准；本页保留三组对照。Edge生成需要联网，已经下载的试听副本不再请求微软。</p></section></main>
<script>const config=__DATA__;
const $=id=>document.getElementById(id),key='northstar-tts-listening-2026-10-22';let selected=1,source=null,votes={},storageError=false;
try{votes=JSON.parse(localStorage.getItem(key)||'{}')}catch{storageError=true}
const sentences=config.files.filter(f=>f.group==='current');sentences.forEach(s=>{let o=document.createElement('option');o.value=s.sequence;o.textContent=String(s.sequence).padStart(2,'0');$('sentence').append(o)});
function save(){try{localStorage.setItem(key,JSON.stringify(votes));storageError=false}catch{storageError=true}$('saved').textContent=storageError?'浏览器保存失败，请使用下载按钮保存判断。':`${Object.values(votes).filter(Boolean).length}/10句已判断 · 仅保留在此浏览器`}
function render(){const row=sentences.find(s=>s.sequence===selected);$('text').textContent=row.text;$('sentence').value=selected;$('vote').value=votes[selected]||'';$('choices').replaceChildren();config.order.forEach((group,i)=>{let box=document.createElement('div');box.className='source';let b=document.createElement('button');b.textContent='播放 '+String.fromCharCode(65+i);b.className=source===group?'active':'';b.onclick=()=>play(group);box.append(b);let m=document.createElement('span');m.className='metrics';const f=config.files.find(f=>f.group===group&&f.sequence===selected);m.textContent=$('reveal').checked?`${config.labels[group]} · ${f.decodedDurationSec.toFixed(2)}秒`:'来源已隐藏';box.append(m);$('choices').append(box)});save()}
async function play(group){source=group;render();const f=config.files.find(f=>f.group===group&&f.sequence===selected);$('player').pause();$('player').src=$('normalized').checked?`normalized/${group}/${String(selected).padStart(2,'0')}.wav`:`raw/${group}/${String(selected).padStart(2,'0')}.mp3`;$('player').playbackRate=Number($('rate').value);$('player').preservesPitch=true;try{await $('player').play();$('status').textContent=`正在试听第${selected}句 · ${String.fromCharCode(65+config.order.indexOf(group))}`}catch{$('status').textContent='播放失败，请检查本地音频文件。'}}
function choose(n){$('player').pause();selected=Math.max(1,Math.min(10,n));source=null;$('player').removeAttribute('src');$('player').load();$('status').textContent='已切换句子，请选择A / B / C。';render()}
$('sentence').onchange=e=>choose(Number(e.target.value));$('previous').onclick=()=>choose(selected-1);$('next').onclick=()=>choose(selected+1);$('vote').onchange=e=>{votes[selected]=e.target.value;save()};$('reveal').onchange=render;$('normalized').onchange=()=>{if(source)play(source)};$('rate').onchange=()=>{$('player').playbackRate=Number($('rate').value)};
$('download').onclick=()=>{const rows=sentences.map(s=>({sentence:s.sequence,text:s.text,vote:votes[s.sequence]||null,preferredGroup:/^[ABC]$/.test(votes[s.sequence]||'')?config.order[votes[s.sequence].charCodeAt(0)-65]:null}));const url=URL.createObjectURL(new Blob([JSON.stringify({schemaVersion:1,createdAt:new Date().toISOString(),kind:'human-listening-preference-not-pronunciation-score',mapping:config.order,rows},null,2)],{type:'application/json'}));let a=document.createElement('a');a.href=url;a.download='northstar-tts-listening.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};render();</script></html>'''.replace('__DATA__',data)
(preview/'index.html').write_text(html)
print(preview/'index.html')

if '--serve' in __import__('sys').argv:
    import local
    import sys
    env=local.environment()
    port_file=OUT/'preview-port.json'
    record=local.LOCAL/'tts-preview.json'
    if record.exists() and local.owns_process(json.loads(record.read_text())):
        port=json.loads(port_file.read_text())['port']
    else:
        port=next(n for n in range(3102,3120) if local.available(n))
        local.start_process('tts-preview',[sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1','--directory',str(preview)],ROOT,env,'http.server')
        port_file.write_text(json.dumps({'port':port}))
    print(f'Preview URL: http://127.0.0.1:{port}/')
