"""Independent QA adapter: isolated source snapshot, fresh database, original assertions."""
import sys
from pathlib import Path
import base as q

WORKTREE=Path(__file__).resolve().parents[2]
MAIN=Path('/Users/wangshiqi/Project/NorthstarEnglish')
q.ROOT=MAIN
q.TOOLS=Path(__file__).resolve().parent
q.OUT=q.TOOLS/'evidence'
q.PRIVATE=WORKTREE/'.local/qa-r5-independent'
q.SOURCE=q.PRIVATE/'source'
q.JAVA=MAIN/'.local/jdk21/jdk-21.0.12.1+1/Contents/Home/bin/java'
q.NAME='northstar-qa-r5-independent-20261103'
q.API_PORT=8196
q.WEB_PORT=3203
q.API=f'http://127.0.0.1:{q.API_PORT}/api/v1'
q.WEB=f'http://127.0.0.1:{q.WEB_PORT}'
q.JAR=q.PRIVATE/'candidate.jar'
q.JAR_SHA='771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6'

def seed():
    q.run('seed-original-fixture',['bash',q.SOURCE/'apps/api/mvnw','-f',q.SOURCE/'apps/api/pom.xml','test','-Dtest=FinalQaFixture,QueuePaginationQaFixture'],env=q.env())

if __name__=='__main__':
    {'create':q.create,'nodes':q.nodes,'regressions':q.regressions,'seed':seed}[sys.argv[1]]()
