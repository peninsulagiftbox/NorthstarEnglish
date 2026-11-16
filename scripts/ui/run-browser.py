import json, os, shutil, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
env=dict(os.environ, PATH='/opt/homebrew/opt/node@22/bin:'+os.environ['PATH'])
packages=list((Path.home()/'.npm/_npx').glob('*/node_modules/@playwright/cli/package.json'))
cli=max(packages,key=lambda p:tuple(map(int,json.loads(p.read_text())['version'].split('.')))).parent/'playwright-cli.js'
node=shutil.which('node',path=env['PATH'])
code=Path(sys.argv[1]).read_text()
for account in ['empty','populated']:
 marker='/* AUTH:'+account+' */'
 if marker in code:
  cookies=json.loads((root/('.local/ui-rhythm/'+account+'-auth.json')).read_text())['cookies']
  code=code.replace(marker,'await page.context().clearCookies(); await page.context().addCookies('+json.dumps(cookies)+');')
result=subprocess.run([node,str(cli),'--session=ui-rhythm','run-code',code],cwd=root,env=env,capture_output=True,text=True)
print(result.stdout.split('### Ran Playwright code')[0]);print(result.stderr,file=sys.stderr)
sys.exit(result.returncode or (1 if '### Error' in result.stdout else 0))
