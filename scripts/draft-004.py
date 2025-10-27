#!/usr/bin/env python3
from __future__ import annotations
"""
draft-004.py — TASK004 consolidation runner

Purpose:
- Consolidates multiple wrapper-valid draft JSONs into a single PRP via a consolidator agent.
- Enforces strict JSON wrapper using the TASK004 template, with a targeted repair attempt if needed.

Inputs (CLI):
- --arg: Feature description.
- --template: Path to TASK004 JSON template.
- --agent: Optional preferred consolidator agent, else auto-selects from registry.
- --timestamp/--slug: Select which drafts to consolidate; auto-detects latest if omitted.
- --max-tokens, --limit-drafts, --repair-attempts: Execution controls.

Behavior:
- Finds relevant drafts in prp/drafts by slug/timestamp, reads their content, and builds a consolidation prompt.
- Submits one batch request; validates JSON wrapper; if invalid, attempts one repair batch if configured.
- Saves the consolidated wrapper-valid JSON to prp/drafts with timestamp and label.

Outputs:
- prp/drafts/*-<timestamp>-consolidated.json
"""
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from dotenv import load_dotenv, find_dotenv
import anthropic

# Standalone constants and helpers for agent registry
MODEL_ID = "claude-sonnet-4-5"
AGENT_DIRS = [Path(os.path.expanduser("~/.claude/agents"))]
# Optional extra agent directories via env var
_extra_dirs = os.getenv("CLAUDE_AGENT_DIRS", "").strip()
if _extra_dirs:
    for _d in _extra_dirs.split(":"):
        if _d.strip():
            AGENT_DIRS.append(Path(_d.strip()))


def load_agent_text(name: str) -> str:
    """Load agent system prompt text from registry directories.

    Search order is AGENT_DIRS; file is expected to be '<name>.md'.
    Raises FileNotFoundError if not found.
    """
    fname = f"{name}.md"
    for base in AGENT_DIRS:
        p = Path(base) / fname
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
    raise FileNotFoundError(
        f"Agent file not found for '{name}' in: {', '.join(str(d) for d in AGENT_DIRS)}"
    )


def _slugify(text: str) -> str:
    """Make a filesystem-friendly slug from free text."""
    import re as _re
    txt = text.lower().strip()
    txt = _re.sub(r"[^a-z0-9\-\s]", "", txt)
    txt = _re.sub(r"\s+", "-", txt)
    txt = _re.sub(r"-+", "-", txt)
    return txt or "draft"


def _ensure_parent_dir(path_str: str) -> None:
    """Ensure parent directory of the path exists."""
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)


def _normalize_draft_path(suggested: str, slug: str, label: str, ts: str) -> str:
    """Normalize suggested path into prp/drafts with timestamp and label."""
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
    """Find the latest timestamp in prp/drafts filenames matching a given slug."""
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
    """Find the latest timestamp in prp/drafts regardless of slug."""
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
    """List draft files filtered by slug (optional) and timestamp."""
    d = Path("prp/drafts")
    if not d.exists():
        return []
    pattern = f"*{ts}*.json" if not slug else f"*{slug}*{ts}*.json"
    return sorted(d.glob(pattern))


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Read a JSON file, returning None on parse error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _select_consolidator_agent(preferred: Optional[str]) -> str:
    """Select a consolidator agent, preferring the provided name, else first available registry agent."""
    if preferred:
        return preferred
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
    for base in AGENT_DIRS:
        for p in Path(base).glob("*.md"):
            return p.stem
    raise FileNotFoundError("No agents found in registry for consolidation")


def _build_consolidation_prompt(feature_desc: str, template_text: str, drafts: List[Dict[str, Any]]) -> str:
    """Build the consolidation user prompt embedding the target template and input drafts."""
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
    """Return the first parseable JSON object found in text, else None."""
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
    """CLI entrypoint for TASK004 consolidation.

    Returns non-zero on configuration or API errors; 0 on success.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--arg", dest="feature_description", required=True)
    ap.add_argument("--template", default="templates/prp/draft-prp-004.json")
    ap.add_argument("--prompt", default="prompts/prp/draft-prp-004.md", help="Optional prompt file to include verbatim in the consolidation instruction for TASK004")
    ap.add_argument("--agent")
    ap.add_argument("--timestamp")
    ap.add_argument("--slug")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--limit-drafts", type=int, default=0)
    ap.add_argument("--repair-attempts", type=int, default=1)
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
    tpath = Path(args.template)
    if not tpath.exists():
        print(f"ERROR: template not found: {tpath}")
        return 2
    template_text = tpath.read_text(encoding="utf-8", errors="replace")

    ts = args.timestamp or _find_latest_timestamp_for_slug(slug) or _find_latest_timestamp_any()
    if not ts:
        print("ERROR: Could not find any timestamp in prp/drafts; cannot consolidate")
        return 2
    files = _list_draft_files(slug, ts) or _list_draft_files(None, ts)
    if not files:
        print(f"ERROR: No draft files found for ts={ts}")
        return 2
    items: List[Dict[str, Any]] = []
    for p in files:
        obj = _read_json(p)
        if not isinstance(obj, dict):
            continue
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
    # Optional external prompt
    prefix = Path(args.prompt).read_text(encoding="utf-8", errors="replace") if Path(args.prompt).exists() else ""
    user_text = _build_consolidation_prompt(feature, template_text, items)
    if prefix:
        user_text = "Task Prompt (verbatim, read fully):\n" + prefix.strip() + "\n\n" + user_text

    client = anthropic.Anthropic(api_key=api_key)
    batch_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    req = {
        "custom_id": f"consolidate-{slug}",
        "params": {
            "model": args.model,
            "max_tokens": int(args.max_tokens),
            "temperature": 0.2,
            "system": [
                {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}},
            ],
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_text}]}
            ],
        },
    }

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

    def _valid(obj: dict) -> bool:
        outs = obj.get("outputs")
        content = obj.get("content")
        return isinstance(outs, dict) and isinstance(outs.get("draft_file"), str) and isinstance(content, dict)

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

    if not _valid(payload):
        diag_json = f"tmp/raw/{slug}-consolidate-{batch_ts}-invalid.json"
        diag_txt = f"tmp/raw/{slug}-consolidate-{batch_ts}-raw.txt"
        _ensure_parent_dir(diag_json)
        Path(diag_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        Path(diag_txt).write_text(combined or "", encoding="utf-8")
        print(f"WARN: Consolidation returned invalid JSON. Saved diagnostics -> {diag_json} and {diag_txt}")

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
        payload = rep_payload

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
