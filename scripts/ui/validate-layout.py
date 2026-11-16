import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'output/ui-review/visual-rhythm'
before=json.loads((out/'before-metrics.json').read_text());after=json.loads((out/'after-metrics.json').read_text())
assert len(before)==len(after)==81
assert [(r['name'],r['width'])for r in before]==[(r['name'],r['width'])for r in after]
for r in after:
 for field in ['viewportOverflow','mainOverflow','shellOverflow','overflow','playerCoversEnd','reviewFooterClipped']:
  assert not r.get(field),(r['name'],r['width'],field)
 assert not r.get('toolbarIssues') and not r.get('cardIssues'),r
 assert r.get('headerMainGap',0)>=-1,r
 assert r.get('tabsPanelGap') is None or r['tabsPanelGap']>=16,r
 if r['name'] in ['review','populated-review']:
  assert r['gap']==(20 if r['width']<=640 else 24),r
 if r['name']=='review':assert r['emptyHeight']==(240 if r['width']<=640 else 280),r
for r in before:
 if r['name']=='review':assert r['gap']==0,r
manifest=json.loads((out/'candidate-manifest.json').read_text())
for f in manifest['sourceFiles']:
 assert hashlib.sha256((root/f['path']).read_bytes()).hexdigest()==f['afterSha256'],f['path']
 assert hashlib.sha256((root/'.local/ui-rhythm/build-source'/f['path']).read_bytes()).hexdigest()==f['afterSha256'],f['path']
assert manifest['afterBuildId']!=manifest['frozenBuildId']
result={'status':'PASS','pairedCases':81,'protectedPageCases':75,'authCases':6,'noOverflow':True,'toolbarContainment':True,'cardContainment':True,'noMeasuredOverlap':True,'footerAndPlayerSafe':True,'reviewGapDesktop':24,'reviewGapMobile':20,'reviewEmptyDesktop':280,'reviewEmptyMobile':240,'sourceMatchesTestedBuild':True}
(out/'layout-validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
