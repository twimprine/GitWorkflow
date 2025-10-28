#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv, find_dotenv
import anthropic

from parse_prp_steps import parse_prp_steps, SpecError
from build_prp_batch import MODEL_ID, load_agent_text


CORE_PANEL = [
    "project-manager",
    "application-architect",
    "security-reviewer",
    "ux-designer",
    "test-runner",
    "devops-engineer",
]


def _slugify(text: str) -> str:
    import re
    txt = text.lower().strip()
    txt = re.sub(r"[^a-z0-9\-\s]", "", txt)
    txt = re.sub(r"\s+", "-", txt)
    txt = re.sub(r"-+", "-", txt)
    return txt or "draft"


def _ensure_parent_dir(path_str: str) -> None:
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)


def _extract_text_blocks_from_result(item) -> List[str]:
    # JSONL string
    if isinstance(item, str):
        try:
            obj = json.loads(item)
        except Exception:
            return [item]
        result = obj.get("result") if isinstance(obj, dict) else None
        message = (result or {}).get("message") if isinstance(result, dict) else None
        content = (message or {}).get("content", []) if isinstance(message, dict) else []
        out: List[str] = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                out.append(c.get("text", ""))
        return out
    # SDK object
    try:
        result = getattr(item, "result", None)
        message = getattr(result, "message", None)
        content = getattr(message, "content", [])
        out: List[str] = []
        for c in content:
            if hasattr(c, "type") and getattr(c, "type") == "text":
                out.append(getattr(c, "text", ""))
            elif isinstance(c, dict) and c.get("type") == "text":
                out.append(c.get("text", ""))
        return out
    except Exception:
        return []


def _extract_first_json_object(s: str):
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
    import re
    m = re.search(r"```json\s*(.*?)```", s, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    block = m.group(1).strip()
    try:
        return json.loads(block)
    except Exception:
        return block


def _panel_user_instruction(feature: str) -> str:
    return (
        "Task: Decompose the feature into ATOMIC tasks (no implementation). Respond with JSON only.\n\n"
        f"Feature: {feature}\n\n"
        "Atomicity Rules:\n"
        "- Single objective per task\n- <= 2 affected_components\n- <= 1 dependency (prefer 0)\n"
        "- Testable acceptance criteria (3-5)\n- No cross-service coupling unless trivial\n\n"
        "Output JSON schema:\n"
        "{\n"
        "  \"atomicity\": { \"is_atomic\": true|false, \"reasons\": [\"...\"] },\n"
        "  \"proposed_tasks\": [\n"
        "    {\n"
        "      \"id\": \"t-<agent>-001\",\n"
        "      \"objective\": \"one sentence\",\n"
        "      \"affected_components\": [\"x\"],\n"
        "      \"dependencies\": [],\n"
        "      \"acceptance\": [\"...\"],\n"
        "      \"risk\": [\"...\"],\n"
        "      \"effort\": \"S|M|L\"\n"
        "    }\n"
        "  ],\n"
        "  \"split_recommendation\": [\"t-...\"],\n"
        "  \"delegation_suggestions\": [\"agent-name: reason\"]\n"
        "}\n\n"
        "STRICT: JSON only, no commentary."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="tmp/draft.md", help="Markdown with prp-steps (for consistency; not required to contain panel step)")
    ap.add_argument("--arg", dest="feature_description", required=True, help="Feature description")
    ap.add_argument("--agents", default=",".join(CORE_PANEL), help="Comma-separated agent ids; defaults to core panel")
    ap.add_argument("--model", default=MODEL_ID)
    args = ap.parse_args()

    try:
        load_dotenv(find_dotenv(usecwd=True), override=False)
    except Exception:
        pass

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in environment or .env")
        return 2

    # Optionally parse md just to validate the file exists and keep similar UX
    if args.md and Path(args.md).exists():
        try:
            parse_prp_steps(args.md)
        except Exception:
            # It's fine if it doesn't contain the panel step; we proceed anyway
            pass

    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    feature = args.feature_description
    slug = _slugify(feature)

    client = anthropic.Anthropic(api_key=api_key)

    # Build one request per agent
    user_text = _panel_user_instruction(feature)
    requests = []
    for aid in agents:
        try:
            system_text = load_agent_text(aid)
        except FileNotFoundError as e:
            print(f"WARN: skipping unknown agent '{aid}': {e}")
            continue
        req = {
            "custom_id": f"panel-{aid}",
            "params": {
                "model": args.model,
                "max_tokens": 2048,
                "temperature": 0.9,
                "system": [
                    {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}}
                ],
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": user_text}]}
                ],
            },
        }
        requests.append(req)

    if not requests:
        print("No valid agents to query.")
        return 1

    batch = client.messages.batches.create(requests=requests)
    print(f"batch_id={batch.id} status={batch.processing_status}")

    while True:
        b = client.messages.batches.retrieve(batch.id)
        print(f"poll: status={b.processing_status}")
        if b.processing_status in ("ended", "failed", "expired"):
            break
        time.sleep(2)

    results = list(client.messages.batches.results(batch.id))
    print(f"results_count={len(results)}")

    out_dir = Path(f"tmp/panel/{slug}")
    out_dir.mkdir(parents=True, exist_ok=True)

    suggested: set[str] = set()

    for item in results:
        blocks = _extract_text_blocks_from_result(item)
        if not blocks:
            print(item)
            continue
        text = "\n\n".join(blocks)
        data = _extract_first_json_object(text) or _extract_fenced_json(text)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                pass
        if not isinstance(data, dict):
            print("WARN: non-JSON output, skipping save for one item")
            continue

        # Derive agent id from custom_id
        try:
            # If SDK object
            cid = getattr(item, "custom_id", None)
        except Exception:
            cid = None
        if cid is None and isinstance(item, str):
            try:
                obj = json.loads(item)
                cid = obj.get("custom_id")
            except Exception:
                pass
        agent_tag = (cid or "panel-unknown").replace("panel-", "")

        path = out_dir / f"{agent_tag}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"saved -> {path}")

        # collect delegation suggestions
        for s in data.get("delegation_suggestions", []) or []:
            if not isinstance(s, str):
                continue
            name = s.split(":", 1)[0].strip()
            if name:
                suggested.add(name)

    if suggested:
        print("\nSuggested agents (union):")
        print(", ".join(sorted(suggested)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
