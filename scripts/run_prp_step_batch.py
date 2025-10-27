#!/usr/bin/env python3
"""
DEPRECATED: Use scripts/prp_steps_run.py instead.

This shim forwards all arguments to prp_steps_run to preserve backward compatibility
with existing commands while the repo transitions to clearer script names.
"""
import sys
from prp_steps_run import main

if __name__ == "__main__":
    print("NOTE: run_prp_step_batch.py is deprecated. Use scripts/prp_steps_run.py.")
    sys.exit(main())