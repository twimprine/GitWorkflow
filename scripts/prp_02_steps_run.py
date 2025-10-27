#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path
from datetime import datetime
import re

from dotenv import load_dotenv, find_dotenv  # pip install python-dotenv
import anthropic

from parse_prp_steps import parse_prp_steps, SpecError
# Reuse helper functions from the builder
from build_prp_batch import (
    MODEL_ID,
    load_agent_text,
    resolve_mapping,
    build_user_instruction_for_step,
)

def build_single_request(step, runtime_args: dict, prior_outputs: dict, model: str, max_tokens: int) -> dict:
    agent_text = load_agent_text(step.agent)
    resolved_inputs = resolve_mapping(step.inputs, runtime_args, prior_outputs)
    user_text = build_user_instruction_for_step(step, resolved_inputs)
    return {
        "custom_id": f"single-{step.id}",
        "params": {
            "model": model,
            "max_tokens": int(max_tokens),
            "temperature": 0.2,
            "system": [
                {
                    "type": "text",
                    "text": agent_text,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_text}],
                }
            ],
        },
    }



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="tmp/draft.md", help="Markdown file with prp-steps")
    ap.add_argument("--template", default="templates/prp/draft-prp-template.md", help="PRP template markdown file")
    ap.add_argument("--arg", dest="feature_description", required=True, help="Value for $ARGUMENTS/feature_description")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--max-tokens", type=int, default=8192, help="Max tokens per response (default 8192)")
    ap.add_argument("--step", default="create_draft", help="Step id to run (default: create_draft)")
    ap.add_argument("--steps", nargs="+", help="Multiple step ids to run in one batch (space-separated)")
    ap.add_argument("--all-steps", action="store_true", help="Run all steps defined in the spec in one batch")
    ap.add_argument(
        "--draft-ext",
        choices=["md", "mdx", "json", "preserve"],
        default="json",
        help="File extension policy for saved drafts: json (default), md, mdx, or preserve suggested extension",
    )
    args = ap.parse_args()

    # Load .env if present
    try:
        load_dotenv(find_dotenv(usecwd=True), override=False)
    except Exception:
        pass

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in environment or .env")
        return 2

    try:
        spec = parse_prp_steps(args.md)
    except SpecError as e:
        print(f"SpecError: {e}")
        return 1

    # Determine steps to run
    available_ids = [s.id for s in spec.steps]
    if args.all_steps:
        selected_ids = available_ids
    elif args.steps:
        selected_ids = args.steps
    else:
        selected_ids = [args.step]

    # Validate selected ids
    missing = [sid for sid in selected_ids if sid not in available_ids]
    if missing:
        print(f"Unknown step ids: {missing}. Available: {available_ids}")
        return 2

    # Build a batch of requests
    runtime_args = {"feature_description": args.feature_description}
    prior_outputs: dict = {}
    requests = []
    batch_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    for sid in selected_ids:
        step = next(s for s in spec.steps if s.id == sid)
        req = build_single_request(step, runtime_args, prior_outputs, args.model, args.max_tokens)
        # Ensure unique, step-specific custom_id
        req["custom_id"] = f"step-{sid}"
        requests.append(req)

    client = anthropic.Anthropic(api_key=api_key)
    batch = client.messages.batches.create(requests=requests)
    print(f"batch_id={batch.id} status={batch.processing_status} count={len(requests)}")

    # Poll until done
    while True:
        b = client.messages.batches.retrieve(batch.id)
        print(f"poll: status={b.processing_status}")
        if b.processing_status in ("ended", "failed", "expired"):
            break
        time.sleep(2)

    # Fetch raw results
    results_iter = client.messages.batches.results(batch.id)
    items = list(results_iter)
    print(f"results_count={len(items)}")
    if not items:
        print("No results returned.")
        return 3

    seen_steps = set()
    # Process each item independently
    for item in items:
        blocks: list[str] = _extract_text_blocks_from_result(item)
        cid = _get_custom_id(item)
        step_id = cid.replace("step-", "") if cid else "unknown-step"
        seen_steps.add(step_id)
        if not blocks:
            print(f"WARN: no text blocks for {cid or 'unknown'}; raw=\n{item}")
            continue

        print(f"\n--- assistant output (raw) [{step_id}] ---")
        print("\n\n".join(blocks))

        combined = "\n\n".join(blocks)
        payload = _extract_first_json_object(combined) or _extract_fenced_json(combined)
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                pass
        if payload is None:
            print(f"No JSON detected for step {step_id}; saving raw output for debugging.")
            raw_out = f"tmp/raw/{_slugify(args.feature_description)}-{step_id}-{batch_ts}.txt"
            _ensure_parent_dir(raw_out)
            Path(raw_out).write_text(combined, encoding="utf-8")
            print(f"Saved raw -> {raw_out}")
            continue

        feature = args.feature_description
        slug = _slugify(feature)
        data = payload
        # Validate required wrapper keys for JSON mode
        def _is_valid_payload(obj: dict) -> bool:
            if not isinstance(obj, dict):
                return False
            outs = obj.get("outputs")
            content = obj.get("content")
            return isinstance(outs, dict) and isinstance(outs.get("draft_file"), str) and isinstance(content, dict)

        if isinstance(data, dict) and _is_valid_payload(data):
            dest = None
            outputs = data.get("outputs", {}) if isinstance(data.get("outputs", {}), dict) else {}
            if "draft_file" in outputs and isinstance(outputs["draft_file"], str):
                dest = outputs["draft_file"]
                dest = (dest
                        .replace("{slug}", slug)
                        .replace("{timestamp}", batch_ts)
                        .replace("{variant}", "a")
                        .replace("{prp_id}", "000"))
            if not dest:
                dest = f"{slug}-{step_id}-{batch_ts}.json" if args.draft_ext == "json" else f"{slug}-{step_id}-{batch_ts}.md"
            # Normalize to always save under prp/drafts/ and keep only basename
            dest = _normalize_draft_path(dest, slug, step_id, batch_ts, args.draft_ext)
            _ensure_parent_dir(dest)
            content_text = data.get("content", "")
            # In JSON mode, save the full payload (content + outputs) as canonical JSON
            if args.draft_ext == "json":
                Path(dest).write_text(json.dumps(data, indent=2), encoding="utf-8")
            else:
                # Markdown-like modes: write the content text
                Path(dest).write_text(content_text, encoding="utf-8")
            print(f"Saved draft -> {dest}")
            # Only create a separate panel artifact if not already saving JSON as the main output
            if args.draft_ext != "json":
                embedded = _extract_fenced_json(content_text)
                if isinstance(embedded, dict) and ("proposed_tasks" in embedded or "atomicity" in embedded):
                    panel_path = f"tmp/panel/{slug}-{step_id}-{batch_ts}.json"
                    _ensure_parent_dir(panel_path)
                    Path(panel_path).write_text(json.dumps(embedded, indent=2), encoding="utf-8")
                    print(f"Saved embedded panel tasks -> {panel_path}")
            continue

        if isinstance(data, dict) and "report" in data:
            report_path = f"tmp/reports/{slug}-size-{step_id}-{batch_ts}.json"
            _ensure_parent_dir(report_path)
            Path(report_path).write_text(json.dumps(data["report"], indent=2), encoding="utf-8")
            print(f"Saved report -> {report_path}")
            continue

        if isinstance(data, dict) and ("proposed_tasks" in data or "atomicity" in data):
            out_path = f"tmp/panel/{slug}-{step_id}-{batch_ts}.json"
            _ensure_parent_dir(out_path)
            Path(out_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Saved panel tasks -> {out_path}")
            continue

        # Fallback: if we have a dict but invalid wrapper keys, save to tmp/raw for diagnostics instead of prp/drafts
        if isinstance(data, dict) and args.draft_ext == "json":
            raw_out = f"tmp/raw/{_slugify(args.feature_description)}-{step_id}-{batch_ts}-invalid.json"
            _ensure_parent_dir(raw_out)
            Path(raw_out).write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"WARN: invalid JSON payload for {step_id} (missing outputs.draft_file and/or content object). Saved diagnostics -> {raw_out}")
            continue

    return 0
    # end main


def _extract_text_blocks_from_result(item) -> list[str]:
    """Handle both JSONL strings and SDK response objects and return text blocks."""
    # Case 1: JSONL string
    if isinstance(item, str):
        try:
            obj = json.loads(item)
        except Exception:
            return [item]
        result = obj.get("result") if isinstance(obj, dict) else None
        message = (result or {}).get("message") if isinstance(result, dict) else None
        content = (message or {}).get("content", []) if isinstance(message, dict) else []
        blocks: list[str] = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                blocks.append(c.get("text", ""))
        return blocks
    
    # Case 2: SDK objects (MessageBatchIndividualResponse -> result -> message -> content)
    try:
        result = getattr(item, "result", None)
        message = getattr(result, "message", None)
        content = getattr(message, "content", [])
        blocks: list[str] = []
        for c in content:
            # c may be TextBlock or dict
            if hasattr(c, "type") and getattr(c, "type") == "text":
                blocks.append(getattr(c, "text", ""))
            elif isinstance(c, dict) and c.get("type") == "text":
                blocks.append(c.get("text", ""))
        return blocks
    except Exception:
        return []


def _get_custom_id(item) -> str | None:
    # SDK object path
    try:
        cid = getattr(item, "custom_id", None)
        if cid:
            return cid
    except Exception:
        pass
    # JSONL string path
    if isinstance(item, str):
        try:
            obj = json.loads(item)
            return obj.get("custom_id")
        except Exception:
            return None
    return None


def _ensure_parent_dir(path_str: str) -> None:
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    txt = text.lower().strip()
    txt = re.sub(r"[^a-z0-9\-\s]", "", txt)
    txt = re.sub(r"\s+", "-", txt)
    txt = re.sub(r"-+", "-", txt)
    return txt or "draft"


def _extract_first_json_object(s: str):
    """Extract the first top-level JSON object from a string; return parsed dict or None.

    This handles extra prose around the JSON by scanning for balanced braces.
    """
    start = s.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(s)):
            ch = s[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = s[start:i+1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        break
        start = s.find("{", start + 1)
    return None


def _extract_fenced_json(s: str):
    """Extract JSON from fenced code blocks like ```json ... ```.

    Returns dict or string or None.
    """
    import re as _re
    pattern = _re.compile(r"```json\s*(.*?)```", _re.DOTALL | _re.IGNORECASE)
    m = pattern.search(s)
    if not m:
        return None
    block = m.group(1).strip()
    try:
        return json.loads(block)
    except Exception:
        return block


def _normalize_draft_path(suggested: str, slug: str, step_id: str, ts: str, ext_mode: str) -> str:
    """Force drafts to be saved under prp/drafts/ using a unique basename to avoid overwrites.

    Behavior:
    - Keeps only the filename portion from any suggested path
    - Ensures a markdown-like extension according to ext_mode
    - Always appends "-<stepId>-<timestamp>" before the extension to guarantee uniqueness
    - If filename empty, uses <slug>
    """
    base = Path(str(suggested)).name.strip()
    if not base:
        base = slug
    # Split rightmost extension; preserve inner parts like ".json" within the stem
    if base.startswith(".") and base.count(".") == 1:
        # Edge case: hidden files like ".md"
        stem, right_ext = base, ""
    else:
        stem = base.rsplit(".", 1)[0] if "." in base else base
        right_ext = "." + base.rsplit(".", 1)[1] if "." in base else ""

    # Decide final extension
    if ext_mode == "preserve" and right_ext:
        final_ext = right_ext
    elif ext_mode == "mdx":
        final_ext = ".mdx"
    elif ext_mode == "json":
        final_ext = ".json"
    else:
        final_ext = ".md"

    # If we're forcing a markdown-like extension, strip any '.json' tokens from the stem
    # to avoid confusing names like 'foo.json.md' or 'bar.json-suffix.md'.
    if ext_mode not in ("preserve", "json"):
        try:
            stem = re.sub(r"\.json\b", "", stem, flags=re.IGNORECASE)
        except Exception:
            # Fallback safe replace if regex fails for any reason
            stem = stem.replace(".json", "")

    # If the suggested name already contains the timestamp, don't append another
    has_ts = ts in stem or bool(re.search(r"\b\d{8}-\d{6}\b", stem))
    # If it already mentions the step id, don't append it either
    has_step = step_id in stem

    new_stem = stem
    if not has_ts:
        new_stem = f"{new_stem}-{ts}"
    if not has_step:
        # Append step id after ts to prevent rare collisions across agents
        new_stem = f"{new_stem}-{step_id}"

    final_name = f"{new_stem}{final_ext}"
    return str(Path("prp/drafts") / final_name)

if __name__ == "__main__":
    raise SystemExit(main())
