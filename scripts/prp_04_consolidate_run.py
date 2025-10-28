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

# Standalone constants and helpers for agent registry
MODEL_ID = "claude-sonnet-4-5"
AGENT_DIRS = [
    Path(os.path.expanduser("~/.claude/agents")),
    Path("tmp/agents"),
]


def load_agent_text(name: str) -> str:
    fname = f"{name}.md"
    for base in AGENT_DIRS:
        p = Path(base) / fname
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
    raise FileNotFoundError(
        f"Agent file not found for '{name}' in: {', '.join(str(d) for d in AGENT_DIRS)}"
    )


def _slugify(text: str) -> str:
    import re as _re
    txt = text.lower().strip()
    txt = _re.sub(r"[^a-z0-9\-\s]", "", txt)
    txt = _re.sub(r"\s+", "-", txt)
    txt = _re.sub(r"-+", "-", txt)
    return txt or "draft"


def _ensure_parent_dir(path_str: str) -> None:
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)


def _normalize_draft_path(suggested: str, slug: str, label: str, ts: str) -> str:
    base = Path(str(suggested)).name.strip() or f"{slug}-consolidated.json"
    if base.lower().endswith(".json"):
        stem = base[:-5]
        ext = ".json"
    else:
        stem = base
        ext = ".json"
    has_ts = ts in stem or bool(re.search(r"\b\d{8}-\d{6}\b", stem))
    has_label = label in stem
    if not has_ts:
        stem = f"{stem}-{ts}"
    if not has_label:
        stem = f"{stem}-{label}"
    return str(Path("prp/drafts") / f"{stem}{ext}")


def _find_latest_timestamp_for_slug(slug: str) -> Optional[str]:
    d = Path("prp/drafts")
    if not d.exists():
        return None
    ts_re = re.compile(rf"{re.escape(slug)}-(?P<ts>\d{{8}}-\d{{6}})")
    hits: List[str] = []
    for p in d.glob("*.json"):
        m = ts_re.search(p.name)
        if m:
            hits.append(m.group("ts"))
    if not hits:
        return None
    hits.sort(reverse=True)
    return hits[0]


def _find_latest_timestamp_any() -> Optional[str]:
    d = Path("prp/drafts")
    if not d.exists():
        return None
    ts_re = re.compile(r"(?P<ts>\d{8}-\d{6})")
    hits: List[str] = []
    for p in d.glob("*.json"):
        m = ts_re.search(p.name)
        if m:
            hits.append(m.group("ts"))
    if not hits:
        return None
    hits.sort(reverse=True)
    return hits[0]


def _list_draft_files(slug: Optional[str], ts: str) -> List[Path]:
    d = Path("prp/drafts")
    if not d.exists():
        return []
    pattern = f"*{ts}*.json" if not slug else f"*{slug}*{ts}*.json"
    return sorted(d.glob(pattern))


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _select_consolidator_agent(preferred: Optional[str]) -> str:
    if preferred:
        return preferred
    # Try known consolidator-style agents in order
    candidates = [
        "architect-reviewer",
        "project_manager",
        "documentation-developer",
        "business-analyst",
    ]
    for name in candidates:
        try:
            _ = load_agent_text(name)
            return name
        except FileNotFoundError:
            continue
    # Last resort: list first available
    for base in AGENT_DIRS:
        for p in Path(base).glob("*.md"):
            return p.stem
    raise FileNotFoundError("No agents found in registry for consolidation")


def _build_consolidation_prompt(feature_desc: str, template_text: str, drafts: List[Dict[str, Any]]) -> str:
    # Package drafts as a compact JSON array: [{agent, content}] where content tries to pull obj["content"] or obj
    inputs: List[Dict[str, Any]] = []
    for d in drafts:
        agent = d.get("agent") or d.get("meta", {}).get("agent")
        payload = d.get("content", d)
        inputs.append({"agent": agent or "unknown", "content": payload})
    inputs_text = json.dumps(inputs, ensure_ascii=False)
    return (
        "Task: CONSOLIDATE multiple PRP draft inputs into a single PRP using the TARGET JSON TEMPLATE EXACTLY.\n\n"
        "Rules:\n"
        "- STRICT TEMPLATE COMPLIANCE: do not add/remove keys; preserve order and structure\n"
        "- Replace placeholder/example values only\n"
        "- Ensure atomicity: one clear objective; ≤2 affected components per task\n"
        "- Merge overlapping items; dedupe and tighten acceptance criteria (3–5 checks)\n"
        "- Keep risks brief; set effort as S|M|L per task\n\n"
        f"Feature Description:\n{feature_desc}\n\n"
        f"TARGET JSON TEMPLATE (copy structure exactly):\n{template_text}\n\n"
        f"INPUT DRAFTS (JSON array):\n{inputs_text}\n\n"
        "Output: Return JSON only with this shape:\n"
        "{\n"
        "  \"outputs\": { \"draft_file\": \"<suggested-path>.json\" },\n"
        "  \"content\": <the filled JSON object matching the target template>\n"
        "}\n"
        "Do not include commentary outside JSON. Do not wrap content as a string."
    )


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    cand = text[start : i + 1]
                    try:
                        return json.loads(cand)
                    except Exception:
                        break
        start = text.find("{", start + 1)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arg", dest="feature_description", required=True)
    ap.add_argument("--template", default="templates/prp/draft-prp-002.json")
    ap.add_argument("--agent", help="Consolidation agent to use; defaults to a suitable available agent")
    ap.add_argument("--timestamp", help="Timestamp (YYYYMMDD-HHMMSS) to collect drafts from; defaults to latest by slug or across drafts")
    ap.add_argument("--slug", help="Feature slug; defaults to slugified feature description")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--limit-drafts", type=int, default=0, help="Optional cap on number of drafts to include (0 = no cap)")
    ap.add_argument("--repair-attempts", type=int, default=1, help="If consolidation returns invalid JSON, attempt up to this many repair prompts (default 1)")
    args = ap.parse_args()

    try:
        load_dotenv(find_dotenv(usecwd=True), override=False)
    except Exception:
        pass
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in environment or .env")
        return 2

    feature = args.feature_description
    slug = args.slug or _slugify(feature)

    # Read template
    tpath = Path(args.template)
    if not tpath.exists():
        print(f"ERROR: template not found: {tpath}")
        return 2
    template_text = tpath.read_text(encoding="utf-8", errors="replace")

    # Determine timestamp and collect input drafts
    ts = args.timestamp or _find_latest_timestamp_for_slug(slug) or _find_latest_timestamp_any()
    if not ts:
        print("ERROR: Could not find any timestamp in prp/drafts; cannot consolidate")
        return 2
    files = _list_draft_files(slug, ts)
    if not files:
        # fallback by ts only
        files = _list_draft_files(None, ts)
    if not files:
        print(f"ERROR: No draft files found for ts={ts}")
        return 2
    items: List[Dict[str, Any]] = []
    for p in files:
        obj = _read_json(p)
        if not isinstance(obj, dict):
            continue
        # Try to attach agent name from filename heuristic
        agent = None
        m = re.search(r"create_list_draft_([A-Za-z0-9_\-]+)", p.stem)
        if m:
            agent = m.group(1)
        obj_with_meta = {**obj, "meta": {"source_file": str(p), "agent": agent}}
        items.append(obj_with_meta)
    if args.limit_drafts and len(items) > args.limit_drafts:
        items = items[: args.limit_drafts]
    if not items:
        print("ERROR: No readable draft JSONs to consolidate")
        return 2

    agent_name = _select_consolidator_agent(args.agent)
    system_text = load_agent_text(agent_name)
    user_text = _build_consolidation_prompt(feature, template_text, items)

    client = anthropic.Anthropic(api_key=api_key)
    batch_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    req = {
        "custom_id": f"consolidate-{slug}",
        "params": {
            "model": args.model,
            "max_tokens": int(args.max_tokens),
            "temperature": 0.2,
            "system": [
                {
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                }
            ],
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_text}]}
            ],
        },
    }

    # Submit a one-item batch
    from typing import cast
    batch = client.messages.batches.create(requests=cast(Any, [req]))
    print(f"batch_id={batch.id} status={batch.processing_status} count=1")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status in ("ended", "failed", "expired"):
            break
        print(f"poll: status={b.processing_status}")
        import time as _t
        _t.sleep(2)
    results = list(client.messages.batches.results(batch.id))
    if not results:
        print("ERROR: No results returned by batch")
        return 2

    # Extract text
    def _blocks(x) -> List[str]:
        try:
            result = getattr(x, "result", None)
            message = getattr(result, "message", None)
            content = getattr(message, "content", [])
            texts: List[str] = []
            for c in content:
                if hasattr(c, "type") and getattr(c, "type") == "text":
                    texts.append(getattr(c, "text", ""))
                elif isinstance(c, dict) and c.get("type") == "text":
                    texts.append(c.get("text", ""))
            return texts
        except Exception:
            return []

    combined = "\n\n".join(_blocks(results[0]))

    def _extract_fenced_json(s: str):
        import re as _re
        m = _re.search(r"```json\s*(.*?)```", s, _re.DOTALL | _re.IGNORECASE)
        if not m:
            return None
        block = m.group(1).strip()
        try:
            return json.loads(block)
        except Exception:
            return block

    payload = None
    if isinstance(combined, str):
        payload = _extract_first_json_object(combined) or _extract_fenced_json(combined)
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = None
    if not isinstance(payload, dict):
        raw_out = f"tmp/raw/{slug}-consolidate-{batch_ts}.txt"
        _ensure_parent_dir(raw_out)
        Path(raw_out).write_text(combined or "", encoding="utf-8")
        print(f"Saved raw output for inspection -> {raw_out}")
        return 1

    # Validate wrapper keys: require outputs.draft_file and content object
    def _valid(obj: dict) -> bool:
        outs = obj.get("outputs")
        content = obj.get("content")
        return isinstance(outs, dict) and isinstance(outs.get("draft_file"), str) and isinstance(content, dict)

    if not _valid(payload):
        diag_json = f"tmp/raw/{slug}-consolidate-{batch_ts}-invalid.json"
        diag_txt = f"tmp/raw/{slug}-consolidate-{batch_ts}-raw.txt"
        _ensure_parent_dir(diag_json)
        Path(diag_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        Path(diag_txt).write_text(combined or "", encoding="utf-8")
        print(f"WARN: Consolidation returned invalid JSON (missing outputs.draft_file and/or content). Saved diagnostics -> {diag_json} and {diag_txt}")

        # Attempt a single self-repair pass if allowed
        attempts = max(0, int(args.repair_attempts))
        if attempts <= 0:
            return 2

        def _build_repair_prompt(invalid_obj: Dict[str, Any], raw_text: str, template_text: str, feature_desc: str) -> str:
            suggested_name = f"{slug}-{{timestamp}}-consolidated.json"
            return (
                "Task: REPAIR the previous response to match the TARGET JSON WRAPPER exactly.\n\n"
                "You must return JSON only with this wrapper shape:\n"
                "{\n"
                "  \"outputs\": { \"draft_file\": \"<suggested-path>.json\" },\n"
                "  \"content\": <the filled JSON object matching the target template>\n"
                "}\n\n"
                "Rules:\n"
                "- Strictly include both 'outputs.draft_file' (string) and 'content' (object).\n"
                "- Do not include commentary. Do not wrap content as a string.\n"
                "- Use this suggested filename if unsure: " + suggested_name + "\n\n"
                f"Feature Description:\n{feature_desc}\n\n"
                f"TARGET JSON TEMPLATE (copy structure EXACTLY):\n{template_text}\n\n"
                f"YOUR PREVIOUS OUTPUT (invalid):\n{json.dumps(invalid_obj, indent=2)}\n\n"
                f"RAW TEXT (for reference):\n{raw_text[:4000]}\n\n"
                "Return only the corrected JSON wrapper."
            )

        repair_user_text = _build_repair_prompt(payload, combined or "", template_text, feature)
        # Reuse same agent
        client = anthropic.Anthropic(api_key=api_key)
        repair_req = {
            "custom_id": f"consolidate-repair-{slug}",
            "params": {
                "model": args.model,
                "max_tokens": int(args.max_tokens),
                "temperature": 0.2,
                "system": [
                    {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                ],
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": repair_user_text}]}
                ],
            },
        }

        from typing import cast
        rep_batch = client.messages.batches.create(requests=cast(Any, [repair_req]))
        print(f"repair_batch_id={rep_batch.id} status={rep_batch.processing_status} count=1")
        while True:
            b = client.messages.batches.retrieve(rep_batch.id)
            if b.processing_status in ("ended", "failed", "expired"):
                break
            print(f"repair poll: status={b.processing_status}")
            import time as _t
            _t.sleep(2)
        rep_results = list(client.messages.batches.results(rep_batch.id))
        if not rep_results:
            print("ERROR: No results returned by repair batch")
            return 2
        rep_combined = "\n\n".join(_blocks(rep_results[0]))
        rep_payload: Optional[Dict[str, Any]] = None
        if isinstance(rep_combined, str):
            tmp_val: Any = _extract_first_json_object(rep_combined) or _extract_fenced_json(rep_combined)
            if isinstance(tmp_val, str):
                try:
                    tmp_val = json.loads(tmp_val)
                except Exception:
                    tmp_val = None
            rep_payload = tmp_val if isinstance(tmp_val, dict) else None
        if rep_payload is None or not _valid(rep_payload):
            rep_diag = f"tmp/raw/{slug}-consolidate-{batch_ts}-repair-invalid.json"
            _ensure_parent_dir(rep_diag)
            Path(rep_diag).write_text(rep_combined or "", encoding="utf-8")
            print(f"ERROR: Repair attempt failed to produce valid wrapper. Saved diagnostics -> {rep_diag}")
            return 2
        # Use repaired payload onward
        payload = rep_payload

    # Choose destination path
    dest = None
    out = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else None
    if out and isinstance(out.get("draft_file"), str):
        dest = out.get("draft_file")
        dest = dest.replace("{slug}", slug).replace("{timestamp}", batch_ts).replace("{variant}", "final").replace("{prp_id}", "000")
    if not dest:
        dest = f"{slug}-{batch_ts}-consolidated.json"
    dest = _normalize_draft_path(dest, slug, "consolidated", batch_ts)
    _ensure_parent_dir(dest)
    Path(dest).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved consolidated JSON -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
