const fs = require('node:fs');
const { chromium } = require('/Users/wangshiqi/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const fs = require('node:fs');
  const check = eval(fs.readFileSync(__dirname + '/fix_browser_checks.js', 'utf8'));
  const result = await check(page);
  const path = 'qa/phase10d-final-r4/evidence/fix-browser-result.json';
  fs.writeFileSync(path, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
  if (result.result !== 'PASS') process.exit(1);
}
main().catch(error => { console.error(error); process.exit(1); });
