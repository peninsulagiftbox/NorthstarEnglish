#!/usr/bin/env python3
"""Run scripts/data-transfer.py with the R7 adapter preceding scripts/phase10d_isolated."""
import runpy
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(TOOLS))
runpy.run_path(str(ROOT / "scripts/data-transfer.py"), run_name="__main__")
