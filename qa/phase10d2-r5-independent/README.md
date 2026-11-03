# D02 R5 fix: independent QA retest

This directory records the 2026-11-03 independent retest. The queue pagination P1 passed; the overall phase remains CONDITIONAL PASS. See `docs/qa/phase10d/10D_D02_QA_R5_RETEST.md` for the tested scope and remaining gates.

This QA branch contains reports, test helpers, and reviewed synthetic-data summaries. It does not contain the CORE implementation. Tests used a separate snapshot of the CORE frozen candidate: HEAD baseline `a5084cb` plus the 219 inputs identified by manifest SHA-256 `31a9a13065af5113a56929a2ba1aa5856f32228124b34750079fef7087683eb7`. Running these helpers requires that implementation, project runtimes, synthetic media, and the local Playwright installation; paths and ports are explicit in the scripts.

`evidence/summary.json`, `matrix-*.json`, `pagination-api-results.json`, and `independent-audit.json` are reviewed test summaries. Source hashes bind the test input to the frozen candidate. Raw command/HTTP logs, runtime identities, browser traces, databases, and credentials remain local under the repository's evidence policy.

The independently verified 871-file archive remains local at `output/review/northstar-phase10d2-r5-independent-evidence.zip`; SHA-256: `91d0a3757d9916a7a663ff683ad696908563c3437694db06c8e7ededdda6a9de`. Extract it and run `python3 verify.py` to validate its members. It is not uploaded by this source-only Git submission.

The fixtures create original synthetic content. Destructive fixture tests must use a newly created, identity-checked QA schema. Personal port 3308 must never be used.
