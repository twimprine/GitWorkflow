#!/usr/bin/env python3
from __future__ import annotations
"""
draft-003.py — TASK003 recommended-agents runner (deterministic, cache-friendly)

Purpose:
- Gathers delegation_suggestions from prior drafts and submits feature+template 003 to those agents.
- Sends identical, cached system extras for every request containing:
    - Architect/agent system text (per-agent)
    - Optional KNOWN AGENTS CATALOG (JSON) — deterministic, sorted
    - Optional REPO CONTEXT INDEX (JSON) — full file contents per docs/schema.json
    - TASK RESPONSES (JSON) — aggregated prp/drafts/*.json (root objects), sorted by path
- Enforces strict JSON wrapper using the TASK003 template for each recommended agent.

Inputs (CLI):
- --md: Compatibility only (not used for template).
- --arg: Feature description.
- --timestamp: Timestamp to locate prior drafts (auto-detects if omitted when needed by legacy flows).
- --iterations: Number of identical passes (batch submits each once per run).
- --template: Path to TASK003 JSON template used for all submissions.
- --include-repo-context/--no-include-repo-context
- --context-schema, --context-max-files
- --include-agent-catalog/--no-include-agent-catalog, --agent-catalog-lines

Behavior:
- Scans prp/drafts to collect recommended agents; filters against registry.
- Builds one request per agent with identical cached system blocks (extras) for cache determinism.
- Extracts JSON and saves wrapper-valid responses under P–T naming with PRP sequence register.
- Non-wrapper/invalid outputs are saved to tmp/raw for diagnostics.

Outputs:
- prp/drafts/P-###-T-003-<agent>.json for wrapper-valid responses.
"""
import argparse
import json
import os
import re
import glob
import fnmatch
import hashlib
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


def _fp8(s: str) -> str:
    """Generate a stable 6-character hash from a string."""
    try:
        return hashlib.sha1(s.encode("utf-8")).hexdigest()[:6]
    except Exception:
        return "000000"


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


def _collect_recommended_agents_no_ts() -> Set[str]:
    """Collect recommended agents from P-*-T-001.json drafts when no timestamped drafts exist."""
    draft_dir = Path("prp/drafts")
    found: Set[str] = set()
    if not draft_dir.exists():
        return found
    for p in sorted(draft_dir.glob("P-*-T-001.json"), key=lambda q: str(q)):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        found |= _extract_recommended_agents_from_content(data)
    return found


# --- PRP Sequence Register (P counter) ---
def _seq_path() -> Path:
    return Path("prp/prp_seq.json")


def _read_seq() -> dict:
    p = _seq_path()
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {"P": 0, "Q": {"002": 0}}
        p.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        return data
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"P": 0, "Q": {"002": 0}}


def _write_seq(data: dict) -> None:
    p = _seq_path()
    tmp = p.with_suffix(".tmp")
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    tmp.replace(p)


def _next_P() -> int:
    data = _read_seq()
    data["P"] = int(data.get("P", 0)) + 1
    _write_seq(data)
    return data["P"]


def _load_repo_context_from_schema(
    schema_path: Path,
    workspace_root: Path,
    *,
    max_files: int | None = None,
) -> tuple[str, str] | None:
    """Build a deterministic repo context JSON with FULL FILE CONTENTS per schema.

    Returns (context_json, ttl_str) or None if schema missing/invalid.
    The JSON shape is { "repo_context": [{"path": str, "size": int, "content": str}], "schema_source": str }.
    All files matching schema include/exclude/extensions are included, sorted by path, and truncated ONLY by schema.maxFileKB.
    If max_files is provided and > 0, at most that many files are included (in sorted order). If None or <=0, include all.
    """
    try:
        if not schema_path.exists():
            return None
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    include: list[str] = schema.get("include", []) or []
    exclude: list[str] = schema.get("exclude", []) or []
    extensions: list[str] = schema.get("extensions", []) or []
    max_kb: int = int(schema.get("maxFileKB", 256) or 256)
    follow_symlinks: bool = bool(schema.get("followSymlinks", False))
    ttl_hours: int = int(schema.get("cacheTTLHours", 24) or 24)

    candidates: set[Path] = set()
    for pat in include:
        abs_pat = str(workspace_root / pat)
        for m in glob.glob(abs_pat, recursive=True):
            p = Path(m)
            if p.is_dir():
                continue
            if not follow_symlinks and p.is_symlink():
                continue
            candidates.add(p)

    def _is_excluded(p: Path) -> bool:
        rel = str(p.relative_to(workspace_root)) if p.is_absolute() else str(p)
        for pat in exclude:
            if fnmatch.fnmatch(rel, pat):
                return True
        return False

    allowed_ext = set(e.lower() for e in extensions if isinstance(e, str))
    items: list[dict[str, Any]] = []
    max_bytes = max(1, max_kb) * 1024

    for p in sorted(candidates, key=lambda q: str(q)):
        try:
            rel = str(p.relative_to(workspace_root))
        except Exception:
            continue
        if _is_excluded(p):
            continue
        if allowed_ext:
            if p.suffix.lower() not in allowed_ext:
                continue
        try:
            sz = p.stat().st_size
        except Exception:
            continue
        if sz > max_bytes:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            try:
                text = p.read_bytes().decode("utf-8", errors="replace")
            except Exception:
                continue
        items.append({"path": rel, "size": sz, "content": text})
        if isinstance(max_files, int) and max_files > 0 and len(items) >= max_files:
            break

    payload = {
        "repo_context": items,
        "schema_source": str(schema_path.relative_to(workspace_root)) if schema_path.is_relative_to(workspace_root) else str(schema_path),
    }
    context_json = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    ttl = f"{max(1, ttl_hours)}h"
    return context_json, ttl


def _aggregate_prp_drafts(drafts_dir: Path = Path("prp/drafts")) -> str:
    """Return JSON string of all prp/drafts/*.json aggregated with file and root.

    Shape: { "prp_drafts": [ {"file": str, "root": <json>} ] }
    Sorted by file path deterministically.
    """
    items: list[dict[str, Any]] = []
    if not drafts_dir.exists():
        return json.dumps({"prp_drafts": []}, indent=2, sort_keys=True, ensure_ascii=False)
    files = sorted(drafts_dir.glob("*.json"), key=lambda p: str(p))
    for p in files:
        try:
            root = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        items.append({"file": p.name, "root": root})
    return json.dumps({"prp_drafts": items}, indent=2, sort_keys=True, ensure_ascii=False)


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


def _build_request_for_agent(agent: str, template_path: str, feature_desc: str, model: str, max_tokens: int, prompt_prefix: str = "", system_extras: list[dict] | None = None) -> Dict[str, Any]:
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
    system_blocks = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}}]
    if system_extras:
        system_blocks += list(system_extras)
    return {
        "custom_id": f"reco-{agent}",
        "params": {
            "model": model,
            "max_tokens": int(max_tokens),
            "temperature": 0.2,
            "system": system_blocks,
            "messages": [{"role": "user", "content": [{"type": "text", "text": user_text}]}],
        },
    }


def _normalize_agent_id(name: str) -> str:
    txt = name.lower().strip()
    txt = re.sub(r"[^a-z0-9\-\s]", "", txt)
    txt = re.sub(r"\s+", "-", txt)
    txt = re.sub(r"-+", "-", txt)
    return txt or "agent"


def _extract_fenced_json(s: str):
    """Return JSON parsed from a ```json fenced block, or the raw block on parse failure."""
    import re as _re
    m = _re.search(r"```json\s*(.*?)```", s, _re.DOTALL | _re.IGNORECASE)
    if not m:
        return None
    block = m.group(1).strip()
    try:
        return json.loads(block)
    except Exception:
        return block


def _looks_like_task003_content(obj: Any) -> bool:
    """Heuristic to detect TASK003 content objects returned without wrapper."""
    if not isinstance(obj, dict):
        return False
    keys = set(obj.keys())
    indicators = {"task", "objective", "delegated_to", "success_criteria", "validation_tests", "affected_components"}
    return bool(keys & indicators)


def main() -> int:
    """CLI entrypoint for TASK003 recommended agents pass.

    Returns non-zero on configuration or API errors; 0 on success.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="prompts/prp/draft-prp-001.yaml")
    ap.add_argument("--arg", dest="feature_description", required=False, default="prp/idea.md")
    ap.add_argument("--timestamp")
    ap.add_argument("--iterations", type=int, default=1)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--template", default="templates/prp/draft-prp-003.json", help="Template for TASK003 drafts submitted to recommended agents")
    ap.add_argument("--prompt", default="prompts/prp/draft-prp-003.md", help="Optional prompt file to include verbatim in the user instruction for TASK003")
    # Deterministic system extras
    ap.add_argument("--include-repo-context", dest="include_repo_context", action="store_true", default=True)
    ap.add_argument("--no-include-repo-context", dest="include_repo_context", action="store_false")
    ap.add_argument("--context-schema", default="docs/schema.json")
    ap.add_argument("--context-max-files", type=int, default=0)
    ap.add_argument("--include-agent-catalog", dest="include_agent_catalog", action="store_true", default=True)
    ap.add_argument("--no-include-agent-catalog", dest="include_agent_catalog", action="store_false")
    ap.add_argument("--agent-catalog-lines", type=int, default=7)
    ap.add_argument("--override-agent", default="project-manager", help="Ignore recommendations and send to this single agent (default: project-manager)")
    ap.add_argument("--system-prompt-file", default="", help="Optional file whose contents are added as a cached system block for deterministic runs")
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
    # If --arg points to a file, read its contents (compat with step 001 UX)
    try:
        p_arg = Path(feature)
        if p_arg.exists() and p_arg.is_file():
            feature = p_arg.read_text(encoding="utf-8", errors="replace").strip() or feature
    except Exception:
        pass
    slug = _fp8(feature)

    # Determine target agents: prefer override, else timestamped recommendations, else P-based fallback
    registry = _list_registered_agents()
    rec_agents: List[str] = []
    oa = (args.override_agent or "").strip()
    if oa:
        if oa in registry:
            rec_agents = [oa]
            print(f"[task003] override_agent active; targeting only: {oa}")
        else:
            print(f"ERROR: override_agent '{oa}' not found in registry; available sample: {sorted(list(registry))[:10]} ...")
            return 2
    else:
        # Timestamp selection only when not overriding
        ts = args.timestamp or _find_latest_timestamp_any()
        if ts:
            print(f"[task003] using timestamp={ts}")
            raw_recs = _collect_recommended_agents(slug, ts) or _collect_recommended_agents(None, ts)
        else:
            print("[task003] no timestamped drafts found; falling back to P-*-T-001.json for recommendations")
            raw_recs = _collect_recommended_agents_no_ts()
        unknown = sorted(raw_recs - registry)
        rec_agents = sorted(raw_recs & registry)
        print(f"[task003] suggested_agents_raw={sorted(raw_recs)}")
        print(f"[task003] registry_count={len(registry)} matched={len(rec_agents)} unknown={len(unknown)}")
        if unknown:
            print(f"[task003] unknown_agents_not_in_registry={unknown}")
        if not rec_agents:
            print("No recommended agents available (after registry filter).")
            return 0



    client = anthropic.Anthropic(api_key=api_key)
    batch_ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Build deterministic system extras (identical across requests)
    system_extras: list[dict] = []
    # Optional agent catalog
    if args.include_agent_catalog:
        catalog = []
        for base in AGENT_DIRS:
            try:
                files = sorted(Path(base).glob("*.md"), key=lambda q: q.stem)
                for p in files:
                    head = p.read_text(encoding="utf-8", errors="replace").splitlines()[: max(0, int(args.agent_catalog_lines))]
                    catalog.append({"id": p.stem, "summary": "\n".join(head).strip()})
            except Exception:
                continue
        catalog = sorted(catalog, key=lambda x: x["id"]) 
        catalog_json = json.dumps({"available_agents": catalog}, indent=2, sort_keys=True, ensure_ascii=False)
        system_extras.append({"type": "text", "text": "KNOWN AGENTS CATALOG (JSON):\n" + catalog_json, "cache_control": {"type": "ephemeral", "ttl": "1h"}})
    # Optional repo context
    if args.include_repo_context:
        ctx = _load_repo_context_from_schema(
            schema_path=Path(args.context_schema),
            workspace_root=Path.cwd(),
            max_files=(args.context_max_files if args.context_max_files > 0 else None),
        )
        if ctx:
            context_json, _ttl = ctx
            system_extras.append({"type": "text", "text": "REPO CONTEXT INDEX (JSON):\n" + context_json, "cache_control": {"type": "ephemeral", "ttl": "1h"}})
    # Aggregate all PRP drafts as context
    prp_json = _aggregate_prp_drafts(Path("prp/drafts"))
    system_extras.append({"type": "text", "text": "TASK RESPONSES (JSON):\n" + prp_json, "cache_control": {"type": "ephemeral", "ttl": "1h"}})
    # Optional system prompt file
    if isinstance(args.system_prompt_file, str) and args.system_prompt_file.strip():
        sp = Path(args.system_prompt_file.strip())
        if sp.exists() and sp.is_file():
            sp_text = sp.read_text(encoding="utf-8", errors="replace")
            system_extras.append({"type": "text", "text": sp_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}})
            print(f"[task003] added system prompt file: {sp}")
        else:
            print(f"WARN: system prompt file not found: {sp}")
    reqs: List[Any] = []
    for a in rec_agents:
        try:
            reqs.append(_build_request_for_agent(a, template_path, feature, args.model, args.max_tokens, prompt_prefix, system_extras=system_extras))
        except FileNotFoundError:
            print(f"WARN: recommended agent '{a}' not found in catalog; skipping")
    if not reqs:
        print("No valid requests after filtering agents.")
        return 0
    print(f"[task003] building batch for {len(reqs)} agent(s): {rec_agents}")

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
    print(f"results_count={len(items)}")
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
        obj: Any = _first_json(combined) if isinstance(combined, str) else None
        if obj is None:
            alt = _extract_fenced_json(combined)
            if isinstance(alt, str):
                try:
                    obj = json.loads(alt)
                except Exception:
                    obj = None
            elif isinstance(alt, (dict, list)):
                obj = alt
        if not isinstance(obj, (dict, list)):
            raw_out = f"tmp/raw/t003-{slug}-{batch_ts}.txt"
            Path(raw_out).parent.mkdir(parents=True, exist_ok=True)
            Path(raw_out).write_text(combined or "", encoding="utf-8")
            print(f"saved raw -> {raw_out}")
            continue
        # Normalize into a wrapper dict
        if isinstance(obj, list):
            payload_dict: Dict[str, Any] = {"content": obj, "outputs": {}}
        else:
            content = obj.get("content")
            if isinstance(content, (dict, list)):
                payload_dict = {"content": content, "outputs": obj.get("outputs") if isinstance(obj.get("outputs"), dict) else {}}
            elif _looks_like_task003_content(obj):
                payload_dict = {"content": obj, "outputs": {}}
            else:
                diag = f"tmp/raw/t003-{slug}-{batch_ts}-invalid.json"
                Path(diag).parent.mkdir(parents=True, exist_ok=True)
                Path(diag).write_text(json.dumps(obj, indent=2), encoding="utf-8")
                print(f"saved invalid -> {diag}")
                continue
        # Adopt P–T naming; set outputs.draft_file deterministically
        outs: Dict[str, Any] = dict(payload_dict.get("outputs") or {})
        P = _next_P()
        # Derive agent tag from outputs or custom_id
        agent_tag: str | None = None
        try:
            if isinstance(outs.get("draft_file"), str):
                agent_tag = _normalize_agent_id(Path(str(outs.get("draft_file"))).stem)
        except Exception:
            agent_tag = None
        if not agent_tag:
            try:
                cid = getattr(it, "custom_id", None)
                if isinstance(cid, str) and cid.startswith("reco-"):
                    agent_tag = _normalize_agent_id(cid.replace("reco-", "", 1))
            except Exception:
                agent_tag = None
        if not agent_tag:
            agent_tag = "agent"
        final = Path("prp/drafts") / f"P-{P:03d}-T-003-{agent_tag}.json"
        outs["draft_file"] = str(final)
        payload_dict["outputs"] = outs
        final.parent.mkdir(parents=True, exist_ok=True)
        Path(final).write_text(json.dumps(payload_dict, indent=2), encoding="utf-8")
        print(f"Saved draft -> {final}")
        saved += 1
    print(f"saved {saved} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
