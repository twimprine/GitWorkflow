#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

from dotenv import load_dotenv, find_dotenv
import anthropic

from parse_prp_steps import parse_prp_steps, SpecError
from build_prp_batch import MODEL_ID, load_agent_text, build_user_instruction_for_step, AGENT_DIRS
from parse_prp_steps import StepSpec


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


def _normalize_draft_path(suggested: str, slug: str, step_id: str, ts: str) -> str:
    base = Path(str(suggested)).name.strip()
    if not base:
        base = slug
    if base.lower().endswith(".json"):
        stem = base[:-5]
        ext = ".json"
    else:
        stem = base
        ext = ".json"
    # avoid duplicating ts/step
    has_ts = ts in stem or bool(re.search(r"\b\d{8}-\d{6}\b", stem))
    has_step = step_id in stem
    if not has_ts:
        stem = f"{stem}-{ts}"
    if not has_step:
        stem = f"{stem}-{step_id}"
    return str(Path("prp/drafts") / f"{stem}{ext}")


def _extract_recommended_agents_from_content(obj: Any) -> Set[str]:
    # Content may be directly the JSON template object or nested under { content: {...} }
    content = obj.get("content", obj) if isinstance(obj, dict) else {}
    agents: Set[str] = set()
    if isinstance(content, dict):
        suggestions = content.get("delegation_suggestions", [])
        if isinstance(suggestions, list):
            for entry in suggestions:
                if isinstance(entry, dict):
                    for k in entry.keys():
                        if isinstance(k, str) and k.strip():
                            agents.add(k.strip())
    return agents


def _find_latest_timestamp(slug: str) -> str | None:
    draft_dir = Path("prp/drafts")
    if not draft_dir.exists():
        return None
    ts_re = re.compile(rf"{re.escape(slug)}-(?P<ts>\d{{8}}-\d{{6}})")
    candidates: List[Tuple[str, Path]] = []
    for p in draft_dir.glob("*.json"):
        m = ts_re.search(p.name)
        if m:
            candidates.append((m.group("ts"), p))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][0]


def _find_latest_timestamp_any() -> str | None:
    """Find the latest YYYYMMDD-HHMMSS in any prp/drafts filename."""
    draft_dir = Path("prp/drafts")
    if not draft_dir.exists():
        return None
    ts_re = re.compile(r"(?P<ts>\d{8}-\d{6})")
    candidates: List[str] = []
    for p in draft_dir.glob("*.json"):
        m = ts_re.search(p.name)
        if m:
            candidates.append(m.group("ts"))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0]


def _collect_recommended_agents(slug: str | None, ts: str) -> Set[str]:
    draft_dir = Path("prp/drafts")
    found: Set[str] = set()
    pattern = f"*{ts}*.json" if not slug else f"*{slug}*{ts}*.json"
    for p in draft_dir.glob(pattern):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        found |= _extract_recommended_agents_from_content(data)
    return found


def _list_registered_agents() -> Set[str]:
    names: Set[str] = set()
    for base in AGENT_DIRS:
        try:
            for p in Path(base).glob("*.md"):
                names.add(p.stem)
        except Exception:
            continue
    return names


def _build_request_for_agent(agent: str, template_path: str, feature_desc: str, model: str, max_tokens: int) -> Dict[str, Any]:
    # Use real StepSpec to satisfy typing of instruction builder
    step = StepSpec(
        id=f"reco_{agent}",
        agent=agent,
        action="generate_from_template",
        inputs={"template": template_path, "feature": feature_desc},
        outputs={},
    )
    agent_text = load_agent_text(step.agent)
    user_text = build_user_instruction_for_step(step, step.inputs)
    return {
        "custom_id": f"reco-{agent}",
        "params": {
            "model": model,
            "max_tokens": int(max_tokens),
            "temperature": 0.9,
            "system": [
                {
                    "type": "text",
                    "text": agent_text,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                }
            ],
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_text}]}
            ],
        },
    }


def _save_json_result(item, slug: str, batch_ts: str) -> str | None:
    # Extract text blocks or object payload
    def _extract_text_blocks_from_result(x) -> List[str]:
        if isinstance(x, str):
            try:
                obj = json.loads(x)
            except Exception:
                return [x]
            result = obj.get("result") if isinstance(obj, dict) else None
            message = (result or {}).get("message") if isinstance(result, dict) else None
            content = (message or {}).get("content", []) if isinstance(message, dict) else []
            blocks: List[str] = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    blocks.append(c.get("text", ""))
            return blocks
        try:
            result = getattr(x, "result", None)
            message = getattr(result, "message", None)
            content = getattr(message, "content", [])
            blocks: List[str] = []
            for c in content:
                if hasattr(c, "type") and getattr(c, "type") == "text":
                    blocks.append(getattr(c, "text", ""))
                elif isinstance(c, dict) and c.get("type") == "text":
                    blocks.append(c.get("text", ""))
            return blocks
        except Exception:
            return []

    def _get_custom_id(x) -> str | None:
        try:
            cid = getattr(x, "custom_id", None)
            if cid:
                return cid
        except Exception:
            pass
        if isinstance(x, str):
            try:
                obj = json.loads(x)
                return obj.get("custom_id")
            except Exception:
                return None
        return None

    def _first_json(s: str):
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
                        candidate = s[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except Exception:
                            break
            start = s.find("{", start + 1)
        return None

    blocks = _extract_text_blocks_from_result(item)
    cid = _get_custom_id(item) or "reco-unknown"
    step_id = cid.replace("reco-", "")
    combined = "\n\n".join(blocks)
    payload = _first_json(combined)
    if not isinstance(payload, dict):
        # Save raw for debugging
        raw_out = f"tmp/raw/{slug}-{cid}-{batch_ts}.txt"
        _ensure_parent_dir(raw_out)
        Path(raw_out).write_text(combined or "", encoding="utf-8")
        return None

    # Validate wrapper keys: require outputs.draft_file (str) and content (dict)
    def _valid(obj: dict) -> bool:
        outs = obj.get("outputs")
        content = obj.get("content")
        return isinstance(outs, dict) and isinstance(outs.get("draft_file"), str) and isinstance(content, dict)

    if not _valid(payload):
        diag = f"tmp/raw/{slug}-{cid}-{batch_ts}-invalid.json"
        _ensure_parent_dir(diag)
        Path(diag).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"WARN: invalid payload for {cid}: missing outputs.draft_file and/or content. Saved diagnostics -> {diag}")
        return None

    # Derive dest from outputs.draft_file if present
    dest = None
    if isinstance(payload.get("outputs"), dict):
        out = payload["outputs"]
        draft = out.get("draft_file")
        if isinstance(draft, str):
            dest = draft.replace("{slug}", slug).replace("{timestamp}", batch_ts).replace("{variant}", "a").replace("{prp_id}", "000")
    if not dest:
        dest = f"{slug}-{batch_ts}-{step_id}.json"
    dest = _normalize_draft_path(dest, slug, step_id, batch_ts)
    _ensure_parent_dir(dest)
    Path(dest).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="tmp/draft-prp-001.md", help="Base markdown with prp-steps for initial agents and template path")
    ap.add_argument("--arg", dest="feature_description", required=True)
    ap.add_argument("--timestamp", help="Timestamp (YYYYMMDD-HHMMSS) of the batch to read recommendations from; defaults to latest for this feature")
    ap.add_argument("--iterations", type=int, default=1, help="How many recommendation passes to run (1 or 2)")
    ap.add_argument("--max-tokens", type=int, default=8192)
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

    # Resolve md path (support passing just the filename; try tmp/<file> fallback)
    md_path = Path(args.md)
    if not md_path.exists():
        alt = Path("tmp") / args.md
        if alt.exists():
            md_path = alt
    # Parse base spec to get initial agents and template path
    try:
        spec = parse_prp_steps(str(md_path))
    except SpecError as e:
        print(f"SpecError: {e}")
        return 1
    used_agents: Set[str] = {s.agent for s in spec.steps}
    # Assume all steps share the same template path
    template_path = None
    for s in spec.steps:
        tp = s.inputs.get("template")
        if tp:
            template_path = tp
            break
    if not template_path:
        print("ERROR: No template path found in spec steps")
        return 2

    feature = args.feature_description
    slug = _slugify(feature)
    ts = args.timestamp or _find_latest_timestamp(slug)
    if not ts:
        # Fallback: find the latest timestamp across all drafts
        ts = _find_latest_timestamp_any()
    if not ts:
        print("ERROR: Could not detect timestamp for this feature; specify --timestamp")
        return 2

    client = anthropic.Anthropic(api_key=api_key)
    all_new_agents: Set[str] = set()
    pass_num = 1
    to_exclude = set(used_agents)
    while pass_num <= max(1, args.iterations):
        rec_agents = _collect_recommended_agents(slug, ts)
        if not rec_agents:
            # Fallback: collect by timestamp only
            rec_agents = _collect_recommended_agents(None, ts)
        rec_agents = {a for a in rec_agents if a and a not in to_exclude}
        # Filter against agent registry
        registry = _list_registered_agents()
        available = sorted(rec_agents & registry)
        missing = sorted(rec_agents - registry)
        if missing:
            print(f"pass {pass_num}: skipping {len(missing)} unregistered agents: {missing}")
        rec_agents = set(available)
        if not rec_agents:
            print(f"pass {pass_num}: no new recommended agents found (after excluding: {sorted(to_exclude)})")
            break
        print(f"pass {pass_num}: submitting to recommended agents -> {sorted(rec_agents)}")
        batch_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        reqs: List[Any] = []
        for a in sorted(rec_agents):
            try:
                reqs.append(_build_request_for_agent(a, template_path, feature, args.model, args.max_tokens))
            except FileNotFoundError:
                print(f"WARN: recommended agent '{a}' not found in agent catalog; skipping")
        if not reqs:
            print(f"pass {pass_num}: no valid agents to submit after filtering; stopping")
            break
        from typing import cast
        batch = client.messages.batches.create(requests=cast(Any, reqs))
        print(f"batch_id={batch.id} status={batch.processing_status} count={len(reqs)}")
        # poll
        while True:
            b = client.messages.batches.retrieve(batch.id)
            if b.processing_status in ("ended", "failed", "expired"):
                break
            print(f"poll: status={b.processing_status}")
            import time as _t
            _t.sleep(2)
        items = list(client.messages.batches.results(batch.id))
        saved: List[str] = []
        for it in items:
            dest = _save_json_result(it, slug, batch_ts)
            if dest:
                saved.append(dest)
        print(f"pass {pass_num}: saved {len(saved)} files")
        # Prepare next pass exclusions
        to_exclude |= rec_agents
        all_new_agents |= rec_agents
        pass_num += 1
    if all_new_agents:
        print(f"completed recommendation passes. total new agents run: {sorted(all_new_agents)}")
    else:
        print("no new agents were run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
