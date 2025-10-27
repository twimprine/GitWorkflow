#!/usr/bin/env python3
from __future__ import annotations
"""
draft-003.py — TASK003 recommended-agents runner

Purpose:
- Gathers delegation_suggestions from prior drafts and submits the feature+template to those agents.
- Enforces strict JSON wrapper using the TASK003 template for each recommended agent.

Inputs (CLI):
- --md: Not used for template in this script; kept for compatibility.
- --arg: Feature description.
- --timestamp: Timestamp to locate prior drafts (auto-detects if omitted).
- --iterations: Number of identical passes (batch submits each once per run).
- --template: Path to TASK003 JSON template used for all submissions.

Behavior:
- Scans prp/drafts for the given timestamp to collect recommended agents; filters against registry.
- Issues a batch request per agent; extracts JSON and saves wrapper-valid responses to prp/drafts.
- Non-wrapper/invalid outputs are saved to tmp/raw for diagnostics.

Outputs:
- prp/drafts/*-<timestamp>-reco.json for wrapper-valid responses.
"""
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any

from dotenv import load_dotenv, find_dotenv
import anthropic

# Standalone constants and helpers
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
        p = base / fname
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
    raise FileNotFoundError(f"Agent file not found for '{name}' in: {', '.join(str(d) for d in AGENT_DIRS)}")


def _slugify(text: str) -> str:
    """Make a filesystem-friendly slug from free text."""
    import re as _re
    txt = text.lower().strip()
    txt = _re.sub(r"[^a-z0-9\-\s]", "", txt)
    txt = _re.sub(r"\s+", "-", txt)
    txt = _re.sub(r"-+", "-", txt)
    return txt or "draft"


class SpecError(Exception):
    pass


class Step:
    def __init__(self, id: str, agent: str, action: str, inputs: Dict[str, Any], outputs: Dict[str, Any]):
        self.id = id
        self.agent = agent
        self.action = action
        self.inputs = inputs
        self.outputs = outputs


def parse_prp_steps(path: str):
    """Parse steps YAML from markdown; provided for compatibility with prior flows."""
    import yaml
    text = Path(path).read_text(encoding="utf-8")
    import re as _re
    m = _re.search(r"```yaml\s*(.*?)```", text, _re.DOTALL | _re.IGNORECASE)
    if not m:
        raise SpecError("No yaml block found in markdown")
    data = yaml.safe_load(m.group(1))
    root = data.get("prp-steps") if isinstance(data, dict) else None
    if not isinstance(root, dict):
        raise SpecError("Missing prp-steps root")
    steps = root.get("steps") or []
    class Spec:
        def __init__(self, steps):
            self.steps = steps
    return Spec(steps)


def _extract_recommended_agents_from_content(obj: Any) -> Set[str]:
    """Extract agent names from content.delegation_suggestions objects."""
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


def _find_latest_timestamp_any() -> str | None:
    """Find latest timestamp fragment from prp/drafts filenames."""
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
    """Collect recommended agent names across drafts matching slug/timestamp."""
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
    """List available agent names from registry directories."""
    names: Set[str] = set()
    for base in AGENT_DIRS:
        try:
            for p in Path(base).glob("*.md"):
                names.add(p.stem)
        except Exception:
            continue
    return names


def _build_request_for_agent(agent: str, template_path: str, feature_desc: str, model: str, max_tokens: int, prompt_prefix: str = "") -> Dict[str, Any]:
    """Build Anthropic batch request for a single agent using TASK003 template.

    If prompt_prefix is provided, it is prepended verbatim before the core instruction.
    """
    system_text = load_agent_text(agent)
    t = Path(template_path).read_text(encoding="utf-8") if Path(template_path).exists() else ""
    user_text = (
        "Task: STRICT TEMPLATE COMPLIANCE — Fill the provided JSON template EXACTLY.\n\n"
        f"Feature Description:\n{feature_desc}\n\n"
        f"JSON Template (copy structure exactly):\n{t}\n\n"
        "Output: Return JSON only with this shape:\n"
        "{\n"
        "  \"outputs\": { \"draft_file\": \"<suggested-path>.json\" },\n"
        "  \"content\": <the filled JSON object>\n"
        "}\n"
        "Do not include commentary outside JSON."
    )
    if isinstance(prompt_prefix, str) and prompt_prefix.strip():
        user_text = "Task Prompt (verbatim, read fully):\n" + prompt_prefix.strip() + "\n\n" + user_text
    return {
        "custom_id": f"reco-{agent}",
        "params": {
            "model": model,
            "max_tokens": int(max_tokens),
            "temperature": 0.9,
            "system": [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
            "messages": [{"role": "user", "content": [{"type": "text", "text": user_text}]}],
        },
    }


def _normalize_draft_path(suggested: str, slug: str, step_id: str, ts: str) -> str:
    """Normalize suggested draft path into prp/drafts with timestamp and step label."""
    base = Path(str(suggested)).name.strip() or slug
    if base.lower().endswith(".json"):
        stem = base[:-5]
        ext = ".json"
    else:
        stem = base
        ext = ".json"
    has_ts = ts in stem or bool(re.search(r"\b\d{8}-\d{6}\b", stem))
    has_step = step_id in stem
    if not has_ts:
        stem = f"{stem}-{ts}"
    if not has_step:
        stem = f"{stem}-{step_id}"
    return str(Path("prp/drafts") / f"{stem}{ext}")


def main() -> int:
    """CLI entrypoint for TASK003 recommended agents pass.

    Returns non-zero on configuration or API errors; 0 on success.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="prompts/prp/draft-prp-001.md")
    ap.add_argument("--arg", dest="feature_description", required=True)
    ap.add_argument("--timestamp")
    ap.add_argument("--iterations", type=int, default=1)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--template", default="templates/prp/draft-prp-003.json", help="Template for TASK003 drafts submitted to recommended agents")
    ap.add_argument("--prompt", default="prompts/prp/draft-prp-003.md", help="Optional prompt file to include verbatim in the user instruction for TASK003")
    args = ap.parse_args()

    try:
        load_dotenv(find_dotenv(usecwd=True), override=False)
    except Exception:
        pass
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in environment or .env")
        return 2

    # Use explicit TASK003 template, ignoring any template in md
    template_path = args.template
    prompt_prefix = Path(args.prompt).read_text(encoding="utf-8", errors="replace") if Path(args.prompt).exists() else ""

    feature = args.feature_description
    slug = _slugify(feature)

    # Timestamp selection
    ts = args.timestamp or _find_latest_timestamp_any()
    if not ts:
        print("ERROR: Could not detect timestamp from prp/drafts; specify --timestamp")
        return 2

    # Collect recommended agents from existing drafts
    rec_agents = _collect_recommended_agents(slug, ts) or _collect_recommended_agents(None, ts)
    # Filter against registry
    registry = _list_registered_agents()
    rec_agents = sorted(rec_agents & registry)
    if not rec_agents:
        print("No recommended agents available (after registry filter).")
        return 0

    client = anthropic.Anthropic(api_key=api_key)
    batch_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    reqs: List[Any] = []
    for a in rec_agents:
        try:
            reqs.append(_build_request_for_agent(a, template_path, feature, args.model, args.max_tokens, prompt_prefix))
        except FileNotFoundError:
            print(f"WARN: recommended agent '{a}' not found in catalog; skipping")
    if not reqs:
        print("No valid requests after filtering agents.")
        return 0

    batch = client.messages.batches.create(requests=reqs)
    print(f"batch_id={batch.id} status={batch.processing_status} count={len(reqs)}")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status in ("ended", "failed", "expired"):
            break
        print(f"poll: status={b.processing_status}")
        import time as _t
        _t.sleep(2)
    items = list(client.messages.batches.results(batch.id))
    saved = 0

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
                        cand = s[start:i+1]
                        try:
                            return json.loads(cand)
                        except Exception:
                            break
            start = s.find("{", start + 1)
        return None

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

    for it in items:
        blocks = _extract_text_blocks_from_result(it)
        combined = "\n\n".join(blocks)
        payload = _first_json(combined) if isinstance(combined, str) else None
        if not isinstance(payload, dict):
            raw_out = f"tmp/raw/{slug}-reco-{batch_ts}.txt"
            Path(raw_out).parent.mkdir(parents=True, exist_ok=True)
            Path(raw_out).write_text(combined or "", encoding="utf-8")
            continue
        outs = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else {}
        draft = outs.get("draft_file") if isinstance(outs, dict) else None
        content = payload.get("content")
        if not (isinstance(draft, str) and isinstance(content, dict)):
            diag = f"tmp/raw/{slug}-reco-{batch_ts}-invalid.json"
            Path(diag).parent.mkdir(parents=True, exist_ok=True)
            Path(diag).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            continue
        step_id = "reco"
        dest = draft.replace("{slug}", slug).replace("{timestamp}", batch_ts).replace("{variant}", "a").replace("{prp_id}", "000")
        dest = _normalize_draft_path(dest, slug, step_id, batch_ts)
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        saved += 1
    print(f"saved {saved} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
