#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p output/playwright docs/evidence/phase-02/screenshots
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase02 open "${NORTHSTAR_BASE_URL:-http://127.0.0.1:${WEB_PORT:-3100}}"
trap 'npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase02 close' EXIT
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase02 snapshot
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase02 run-code "$(cat scripts/content-browser-smoke.js)" > output/playwright/content-smoke-result.txt
cat output/playwright/content-smoke-result.txt
python3 -c 'import pathlib,re; s=pathlib.Path("output/playwright/content-smoke-result.txt").read_text(); assert re.search(r"\"passed\"\s*:\s*true", s) and "### Error" not in s, "Content browser smoke failed"'
