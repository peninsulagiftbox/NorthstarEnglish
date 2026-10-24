#!/bin/sh
set -eu
exec python3 "$(dirname "$0")/data-transfer.py" backup "$@"
