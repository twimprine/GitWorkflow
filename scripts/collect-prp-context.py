#!/usr/bin/env python3
"""
Minimal Anthropic Batch POC with Prompt Caching

- Creates ONE batch request with a cached text block (ephemeral cache)
- Polls until finished
- Dumps results to batch/<batch_id>-results.jsonl

Run it twice (unchanged input) to exercise the cache.
"""

import os
import time
from pathlib import Path
import json
import fnmatch
import glob
import anthropic
import argparse

from claude_agent_sdk import query, ClaudeAgentOptions

try:
    from dotenv import load_dotenv, find_dotenv
    # Load nearest .env (repo root) without overriding already-set env vars
    load_dotenv(find_dotenv(usecwd=True), override=False)
except Exception:
    # If python-dotenv isn't present, we just rely on the environment
    pass


def _load_schema(base: Path) -> dict:
    schema_path = base / "docs/schema.json"
    if schema_path.exists():
        try:
            return json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # safe defaults if schema missing or invalid
    return {
        "include": ["docs/**", "README.md"],
        "exclude": [
            "node_modules/**", "venv/**", ".venv/**", ".git/**", "logs/**", "batch/**", "prp/**"
        ],
        "extensions": [".md", ".txt", ".json", ".yaml", ".yml"],
        "maxFileKB": 256,
        "followSymlinks": False,
    }


def _gather_files_from_schema(base: Path, schema: dict) -> list[Path]:
    include = schema.get("include", [])
    exclude = schema.get("exclude", [])
    exts = schema.get("extensions", [])
    max_kb = int(schema.get("maxFileKB", 256))
    follow = bool(schema.get("followSymlinks", False))

    def is_excluded(rel: str) -> bool:
        for pat in exclude:
            if fnmatch.fnmatch(rel, pat):
                return True
        return False

    def has_allowed_ext(rel: str) -> bool:
        if not exts:
            return True
        return any(rel.endswith(e) for e in exts)

    seen: set[str] = set()
    results: list[Path] = []

    for pat in include:
        for path_str in glob.iglob(str(base / pat), recursive=True):
            p = Path(path_str)
            if not p.is_file():
                continue
            if (not follow) and p.is_symlink():
                continue
            rel = str(p.relative_to(base))
            if is_excluded(rel):
                continue
            if not has_allowed_ext(rel):
                continue
            try:
                size = p.stat().st_size
            except Exception:
                continue
            if size > max_kb * 1024:
                continue
            if rel in seen:
                continue
            seen.add(rel)
            results.append(p)

    results.sort(key=lambda x: str(x.relative_to(base)))
    return results


def read_docs() -> str:
    base = Path(__file__).parent.parent
    schema = _load_schema(base)
    files = _gather_files_from_schema(base, schema)
    if not files:
        return "No docs found via schema; POC content."
    parts: list[str] = []
    for p in files:
        rel = str(p.relative_to(base))
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        parts.append(f"--- {rel} ---\n{txt}")
    return "\n\n".join(parts)


def build_grouped_contexts() -> tuple[dict[str, str], list[str]]:
    """Return mapping of group->content (concatenated text) and discovered groups.

    Group is the first path segment (e.g., docs, prp, contracts). Root files map to 'root'.
    """
    base = Path(__file__).parent.parent
    schema = _load_schema(base)
    files = _gather_files_from_schema(base, schema)
    groups: dict[str, list[tuple[str, str]]] = {}
    discovered: set[str] = set()
    for p in files:
        rel = str(p.relative_to(base))
        top = rel.split("/", 1)[0] if "/" in rel else "root"
        discovered.add(top)
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        groups.setdefault(top, []).append((rel, txt))
    # determinism within each group
    result: dict[str, str] = {}
    for grp, items in groups.items():
        items.sort(key=lambda x: x[0])
        chunks = [f"--- {rel} ---\n{txt}" for rel, txt in items]
        result[grp] = "\n\n".join(chunks)
    return result, sorted(discovered)


MODEL_ID = "claude-sonnet-4-5"


def main():
    parser = argparse.ArgumentParser(description="Anthropic Batch POC with cached system blocks per group")
    parser.add_argument("--groups", type=str, help="Comma-separated top-level groups to include (e.g., docs,contracts,prp)")
    parser.add_argument("--dupe", action="store_true", help="Duplicate each request to observe cache hits within the same batch")
    parser.add_argument("--model", type=str, default=MODEL_ID, help=f"Model to use (default: {MODEL_ID})")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in environment or .env at repo root")
        raise SystemExit(2)

    client = anthropic.Anthropic(api_key=api_key)

    grouped, discovered = build_grouped_contexts()
    # Determine which groups to include
    if args.groups:
        selected = [g.strip() for g in args.groups.split(",") if g.strip()]
    else:
        # default to the common ones if they exist; else include all discovered
        preferred = ["docs", "prp", "contracts"]
        selected = [g for g in preferred if g in grouped] or list(grouped.keys())

    requests_payload = []
    for grp in selected:
        content = grouped.get(grp)
        if not content:
            continue
        req = {
            "custom_id": f"{grp}-req1",
            "params": {
                "model": args.model,
                "max_tokens": 2560,
                "temperature": 0.2,
                "system": [
                    {"type": "text", "text": f"You are an expert planner. Focus on the '{grp}' context."},
                    {"type": "text", "text": content, "cache_control": {"type": "ephemeral", "ttl": "1h"}}
                ],
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": f"Summarize the {grp} context succinctly."}]}
                ],
            },
        }
        requests_payload.append(req)
        if args.dupe:
            # exact duplicate (different custom_id) to observe cache read in same batch
            dup = json.loads(json.dumps(req))
            dup["custom_id"] = f"{grp}-req2"
            requests_payload.append(dup)

    if not requests_payload:
        print("No groups selected produced content. Nothing to send.")
        return

    batch = client.messages.batches.create(requests=requests_payload)

    print(f"batch_id={batch.id} status={batch.processing_status}")

    # Simple poll
    while True:
        b = client.messages.batches.retrieve(batch.id)
        print(f"poll: status={b.processing_status}")
        if b.processing_status in ("ended", "failed", "expired"):
            break
        time.sleep(2)

    # Dump results
    try:
        results = client.messages.batches.results(batch.id)
        out_path = Path("batch") / f"{batch.id}-results.jsonl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for line in results:
                f.write(line if isinstance(line, str) else str(line))
                if not str(line).endswith("\n"):
                    f.write("\n")
        print(f"results -> {out_path}")
    except Exception as e:
        print(f"Could not fetch results: {e}")


if __name__ == "__main__":
    main()