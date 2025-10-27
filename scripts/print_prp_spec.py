#!/usr/bin/env python3
"""Tiny CLI to print the parsed CommandSpec from a markdown file."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from parse_prp_steps import parse_prp_steps, SpecError


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("markdown", type=str, help="Path to markdown with prp-steps block")
    args = p.parse_args()

    try:
        spec = parse_prp_steps(args.markdown)
    except SpecError as e:
        print(f"SpecError: {e}")
        return 1

    print(json.dumps(spec.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
