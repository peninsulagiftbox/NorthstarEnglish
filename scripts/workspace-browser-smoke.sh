#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p output/playwright docs/evidence/phase-03/screenshots
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase03 open "${NORTHSTAR_BASE_URL:-http://127.0.0.1:${WEB_PORT:-3100}}/dashboard"
trap 'npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase03 close' EXIT
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase03 snapshot
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase03 run-code "$(cat scripts/workspace-browser-smoke.js)" > output/playwright/workspace-smoke-result.txt
cat output/playwright/workspace-smoke-result.txt
python3 -c 'import pathlib,re; s=pathlib.Path("output/playwright/workspace-smoke-result.txt").read_text(); assert re.search(r"\"passed\"\s*:\s*true",s) and "### Error" not in s,"Workspace browser smoke failed"'
