import argparse,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[2]
env=dict(os.environ,PATH='/opt/homebrew/opt/node@22/bin:'+os.environ['PATH'],API_PORT='5197')
node=shutil.which('node',path=env['PATH'])
parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['before','after']);args=parser.parse_args()
for phase,directory in [('before','baseline-build'),('after','build-source')]:
 if args.phase and phase!=args.phase:continue
 app=root/'.local/ui-rhythm'/directory/'apps/web'
 with (root/f'.local/ui-rhythm/{phase}-production-server.log').open('wb') as log:
  proc=subprocess.Popen([node,str(root/'node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port','3197'],cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT)
  try:
   for _ in range(60):
    if proc.poll() is not None:raise RuntimeError('production server exited')
    try:
     urllib.request.urlopen('http://127.0.0.1:3197/login',timeout=1).close();break
    except OSError:time.sleep(.2)
   else:raise RuntimeError('readiness timeout')
   script=root/f'.local/ui-rhythm/production-{phase}.js';script.write_text((root/'scripts/ui/capture.js').read_text().replace("'PHASE'",repr(phase)))
   with (root/f'output/ui-review/visual-rhythm/production-{phase}.log').open('w') as output:
    response=subprocess.run(['python3',str(root/'scripts/ui/run-browser.py'),str(script)],cwd=root,env=env,stdout=output,stderr=subprocess.STDOUT)
   if response.returncode:raise RuntimeError(phase+' capture failed')
   raw=(root/f'output/ui-review/visual-rhythm/production-{phase}.log').read_text()
   data=json.loads(raw.split('### Result\n')[1].split('\n###')[0]);(root/f'output/ui-review/visual-rhythm/{phase}-metrics.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
   print(phase,len(data),'cases complete',flush=True)
  finally:
   proc.terminate();proc.wait(timeout=20)
