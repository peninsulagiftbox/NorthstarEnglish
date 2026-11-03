#!/bin/sh
# Independent verification of the frozen Phase 10D-2-R1 candidate. Read-only; exits non-zero on any drift.
set -eu
cd "$(dirname "$0")/../../.."
list=qa/phase10d2/evidence/candidate-sha256.txt
expected=$(sed -n 's/^# hash_of_candidate-sha256.txt.*: //p' qa/phase10d2/evidence/candidate-filelist-sha256.txt)
actual=$(tail -n +5 "$list" | shasum -a 256 | awk '{print $1}')
[ "$actual" = "$expected" ] || { echo "FAIL: manifest hash drifted: $actual != $expected"; exit 1; }
tail -n +5 "$list" | while read -r hash file; do
  current=$(shasum -a 256 "$file" | awk '{print $1}')
  [ "$current" = "$hash" ] || { echo "DRIFT: $file $current != $hash"; exit 1; }
done
echo "PASS: ${actual} — all $(tail -n +5 "$list" | wc -l | tr -d ' ') candidate files byte-identical"
