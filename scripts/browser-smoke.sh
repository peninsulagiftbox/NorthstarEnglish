#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p output/playwright
# Pinned CLI, isolated session. Run through local.py exec for project Node22.
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase01 open "${NORTHSTAR_BASE_URL:-http://127.0.0.1:${WEB_PORT:-3100}}"
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase01 snapshot
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase01 run-code "$(cat scripts/browser-smoke.js)" > output/playwright/smoke-result.txt
cat output/playwright/smoke-result.txt
python3 -c 'import pathlib,re; s=pathlib.Path("output/playwright/smoke-result.txt").read_text(); assert re.search(r"\"passed\"\s*:\s*true", s) and "### Error" not in s, "Browser smoke failed"'
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase01 close
