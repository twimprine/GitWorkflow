#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv, find_dotenv
import anthropic

#!/usr/bin/env python3
"""
Compatibility shim: forwards to the standalone Step 4 runner.

This keeps consolidation logic isolated in `prp_04_consolidate_run.py`
so you can modify step 4 independently without touching other steps.
"""

from prp_04_consolidate_run import main

if __name__ == "__main__":
    raise SystemExit(main())
def _ensure_parent_dir(path_str: str) -> None:
