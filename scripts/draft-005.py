#!/usr/bin/env python3
from __future__ import annotations
"""
draft-005.py — TASK005 PRP Break Tasks into individual PRPs

Actions:
- Read latest PRP-004.json from prp/active/
- For each task in tasks[], create a new PRP-005 JSON file in prp/active/
- Each PRP-005 gets a unique prp_id (P-###-T-###), sequentially numbered
- Each PRP-005 references the parent PRP-004 in metadata.parent_prp_id
- Build dependency graph in metadata.prp_dependencies
- Use dependencies to set up step inputs/outputs appropriately
- Schedule batches according to dependencies (no parallel steps if dependent)
    - E.g., if Task 2 depends on Task 1, Task 2's PRP-005 should run after Task 1's completes
    - Ouput of Task 1 becomes input to Task 2
    - Batch requests should reflect this sequencing
- Save each PRP-005 JSON to prp/active/PRP-005-T-###.json

Rules:
- If a task has no dependencies, it can be scheduled in parallel with other independent tasks
- If a task depends on another, it must be scheduled after its dependencies complete
- Each PRP-005 should be self-contained with its own inputs, outputs, and metadata
- The script should handle errors gracefully and log progress output raw data to tmp/


"""

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


def run(cmd: List[str], cwd: Optional[str] = None, check: bool = False) -> Tuple[int, str, str]:
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    if check and p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, cmd, out, err)
    return p.returncode, out.strip(), err.strip()


def ensure_git_repo() -> None:
    code, out, _ = run(["git", "rev-parse", "--is-inside-work-tree"])
    if code != 0 or out != "true":
        raise SystemExit("ERROR: Not inside a git repository.")


def get_default_branch() -> str:
    # Try origin/HEAD first
    code, out, _ = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])  # e.g., refs/remotes/origin/main
    if code == 0 and out:
        m = re.search(r"refs/remotes/origin/(.+)$", out)
        if m:
            return m.group(1)
    # Fallbacks
    for name in ("main", "master"):
        code, _, _ = run(["git", "rev-parse", "--verify", name])
        if code == 0:
            return name
    return "main"


def get_current_branch() -> str:
    code, out, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=True)
    return out


def working_tree_clean() -> bool:
    code, out, _ = run(["git", "status", "--porcelain"])
    return code == 0 and out == ""


def detect_prp_id(active_json: Path) -> Optional[str]:
    if not active_json.exists():
        return None
    try:
        obj = json.loads(active_json.read_text(encoding="utf-8"))
    except Exception:
        return None
    meta = obj.get("metadata", {}) if isinstance(obj, dict) else {}
    prp_id = meta.get("prp_id") if isinstance(meta, dict) else None
    if isinstance(prp_id, str) and re.match(r"^P-\d{3}-T-\d{3}$", prp_id):
        return prp_id
    return None


def plan_moves(prp_num: str, ts: str) -> List[Tuple[Path, Path]]:
    """
    Return list of (src, dest) moves for the PRP artifacts.
    prp_num is like 'P-206' (no trailing T-XXX)
    """
    moves: List[Tuple[Path, Path]] = []
    archive_root = Path("archive") / ts / prp_num
    dst_active = archive_root / "active"
    dst_drafts = archive_root / "drafts"

    # Active outputs
    for p in [Path("prp/active/PRP-004.json"), Path("prp/active/PRP-004.md")]:
        if p.exists():
            moves.append((p, dst_active / p.name))

    # Drafts matching P-###
    for p in sorted(Path("prp/drafts").glob(f"{prp_num}*.json")):
        moves.append((p, dst_drafts / p.name))

    return moves


def do_moves(moves: List[Tuple[Path, Path]], dry_run: bool = False) -> None:
    for src, dst in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dry_run:
            print(f"DRY-RUN: would move {src} -> {dst}")
            continue
        print(f"MOVE: {src} -> {dst}")
        shutil.move(str(src), str(dst))


def stage_commit_push(branch_name: str, commit_msg: str, remote: str, try_merge: bool) -> None:
    # Create new branch from current HEAD
    code, _, err = run(["git", "checkout", "-b", branch_name])
    if code != 0:
        print(f"WARN: failed to create branch '{branch_name}': {err}")
        # Fallback: sanitize ':' to '-' and retry
        alt = branch_name.replace(":", "-")
        code, _, err = run(["git", "checkout", "-b", alt], check=True)
        branch_name = alt

    run(["git", "add", "-A"], check=True)
    code, _, err = run(["git", "commit", "-m", commit_msg])
    if code != 0:
        print(f"WARN: nothing to commit or commit failed: {err}")

    # Try push
    code, _, err = run(["git", "push", "-u", remote, branch_name])
    if code != 0:
        print(f"WARN: push failed: {err}")

    if try_merge:
        default_branch = get_default_branch()
        # Checkout default branch and attempt merge
        run(["git", "checkout", default_branch], check=False)
        # Ensure up to date
        run(["git", "pull", remote, default_branch], check=False)
        # Attempt merge
        code, _, err = run(["git", "merge", "--no-ff", "-m", commit_msg, branch_name])
        if code == 0:
            # Push merge
            run(["git", "push", remote, default_branch], check=False)
            print(f"Merged '{branch_name}' into '{default_branch}' and pushed.")
        else:
            print(f"INFO: Merge into '{default_branch}' not possible now: {err}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Archive PRP artifacts to archive/<ts>/P-###/{active,drafts} and push via PRP branch")
    ap.add_argument("--dry-run", action="store_true", help="Show planned actions without modifying files or git")
    ap.add_argument("--remote", default="origin", help="Git remote to push to (default: origin)")
    ap.add_argument("--no-merge", action="store_true", help="Do not attempt to merge into default branch")
    ap.add_argument("--branch-prefix", default="PRP:archive", help="Branch name prefix (will fallback by replacing ':' if needed)")
    ap.add_argument("--commit-prefix", default="PRP:", help="Commit message prefix")
    ap.add_argument("--active-json", default="prp/active/PRP-004.json", help="Active PRP JSON path (to read prp_id)")

    args = ap.parse_args()

    ensure_git_repo()
    if not working_tree_clean():
        print("ERROR: Working tree is not clean. Commit or stash changes before running.")
        return 2

    active_json = Path(args.active_json)
    prp_id = detect_prp_id(active_json)
    if not prp_id:
        print(f"ERROR: Could not detect prp_id from {active_json} -> metadata.prp_id missing or invalid.")
        return 2

    m = re.match(r"^(P-\d{3})-T-\d{3}$", prp_id)
    prp_num = m.group(1) if m else prp_id.split('-T-')[0]
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    moves = plan_moves(prp_num, ts)
    if not moves:
        print("INFO: No PRP files found to archive.")
    else:
        print("Planned moves:")
        for s, d in moves:
            print(f"  {s} -> {d}")
    if args.dry_run:
        print("DRY-RUN: exiting without changes.")
        return 0

    # Perform moves on a new branch and push
    branch_name = f"{args.branch_prefix}-{prp_num}-{ts}"
    commit_msg = f"{args.commit_prefix} archive {prp_num} at {ts}"

    cur_branch = get_current_branch()
    try:
        do_moves(moves)
        stage_commit_push(branch_name, commit_msg, args.remote, try_merge=(not args.no_merge))
    finally:
        # Return to original branch for user convenience
        run(["git", "checkout", cur_branch], check=False)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
