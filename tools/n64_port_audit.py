#!/usr/bin/env python3
"""Target-neutral entry point for N64 decomp/recomp host-port semantic checks.

The implementation currently lives in r36s_semantic_audit.py for history and
backward compatibility. New automation should call this file. As project
profiles land, target/game-specific configuration will move here while the
shared detector engine remains reusable.
"""
from pathlib import Path
import runpy

_IMPL = Path(__file__).with_name("r36s_semantic_audit.py")
runpy.run_path(str(_IMPL), run_name="__main__")
