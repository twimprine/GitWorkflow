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
import hashlib

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


def _shorten_for_filename(name: str, max_len: int = 120) -> str:
    """Shorten a potentially long name for use in a filename by keeping a prefix and adding a 6-char hash.

    Guarantees length <= max_len and minimally 1 char of original name retained.
    """
    if len(name) <= max_len:
        return name
    try:
        h = hashlib.sha1(name.encode("utf-8")).hexdigest()[:6]
    except Exception:
        h = "000000"
    keep = max_len - 1 - len(h)
    base = name[: max(1, keep)].rstrip("-")
    return f"{base}-{h}"


def _list_agents_catalog() -> List[Dict[str, str]]:
    """Return a deterministic catalog of known agents from registry.

    Each entry: {"id": <stem>, "path": <absolute_path>} sorted by id.
    """
    entries: List[Dict[str, str]] = []
    seen: set[str] = set()
    for base in AGENT_DIRS:
        try:
            for p in Path(base).glob("*.md"):
                agent_id = p.stem
                if agent_id in seen:
                    continue
                seen.add(agent_id)
                entries.append({"id": agent_id, "path": str(p)})
        except Exception:
            continue
    entries.sort(key=lambda x: x["id"])  # deterministic ordering
    return entries


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def _fp8(s: str) -> str:
    try:
        return hashlib.sha1(s.encode("utf-8")).hexdigest()[:6]
    except Exception:
        return "000000"


def _short_custom_id(prefix: str, slug: str, max_len: int = 64) -> str:
    """Build a custom_id <= max_len using prefix and slug, shortening with a hash if needed."""
    cid = f"{prefix}-{slug}"
    if len(cid) <= max_len:
        return cid
    h = _fp8(slug)
    # We will format as: <prefix>-<short>-<hash>
    # total length = len(prefix) + 1 + len(short) + 1 + 6 <= max_len
    allow_short = max_len - len(prefix) - 1 - 1 - 6
    short = slug[: max(1, allow_short)]
    return f"{prefix}-{short}-{h}"


def _alloc_prp_id(seq_path: Path) -> int:
    """Allocate the next P id from prp/prp_seq.json and persist it.

    If file doesn't exist, start at 1. Preserves other keys (e.g., Q).
    """
    data: Dict[str, Any] = {}
    if seq_path.exists():
        try:
            data = json.loads(seq_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    current = int(data.get("P", 0))
    next_id = current + 1 if current >= 0 else 1
    data["P"] = next_id
    # Preserve compact but stable JSON formatting
    _ensure_parent_dir(str(seq_path))
    seq_path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return next_id


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


def _looks_like_content(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    keys = set(obj.keys())
    required = {"version", "metadata"}
    return bool(required.issubset(keys))


def _list_latest_archived_drafts() -> List[Path]:
    """Return draft JSON files from the most recent archive timestamp, if any.

    Looks under archive/{ts}/P-###/drafts/*.json and returns all files for the latest {ts}.
    """
    arch_root = Path("archive")
    if not arch_root.exists():
        return []
    # Find timestamp dirs
    ts_dirs = [p for p in arch_root.iterdir() if p.is_dir()]
    if not ts_dirs:
        return []
    # Sort lexicographically; our ts format supports this ordering
    ts_dirs.sort(key=lambda p: p.name, reverse=True)
    for tsd in ts_dirs:
        drafts: List[Path] = []
        for pdir in sorted((tsd.glob("P-*/drafts")), key=lambda x: x.name):
            drafts.extend(sorted(pdir.glob("*.json"), key=lambda x: x.name))
        if drafts:
            return drafts
    return []


def _load_latest_archived_active_content() -> Optional[Dict[str, Any]]:
    arch_root = Path("archive")
    if not arch_root.exists():
        return None
    ts_dirs = [p for p in arch_root.iterdir() if p.is_dir()]
    ts_dirs.sort(key=lambda p: p.name, reverse=True)
    for tsd in ts_dirs:
        # search deepest P-*/active/PRP-004.json
        for act_dir in sorted(tsd.glob("P-*/active"), key=lambda x: x.name, reverse=True):
            cand = act_dir / "PRP-004.json"
            if cand.exists():
                obj = _read_json(cand)
                if isinstance(obj, dict):
                    return obj
    return None


def _render_markdown_from_content(content: Dict[str, Any], prompt_path: str) -> str:
    template_md = Path(prompt_path)
    raw_md_template = template_md.read_text(encoding="utf-8", errors="replace").rstrip() if template_md.exists() else "# PRP-004"

    def _safe_join(val: Any, sep: str = ", ") -> str:
        if isinstance(val, list):
            return sep.join(str(x) for x in val)
        if isinstance(val, (str, int, float)) or val is None:
            return "" if val is None else str(val)
        return json.dumps(val)

    def _unique_ordered(seq: List[Any], key=lambda x: x) -> List[Any]:
        seen = set()
        out = []
        for item in seq:
            k = key(item)
            if k in seen:
                continue
            seen.add(k)
            out.append(item)
        return out

    md_ctx: Dict[str, Any] = {}
    meta = content.get("metadata", {}) if isinstance(content, dict) else {}
    md_ctx["purpose"] = meta.get("feature", "")
    md_ctx["scope"] = meta.get("scope", "")
    md_ctx["components"] = _safe_join(meta.get("components", []))
    md_ctx["out_of_scope"] = _safe_join(meta.get("out_of_scope", []))

    affected: List[str] = []
    for t in content.get("tasks", []) if isinstance(content, dict) else []:
        comps = t.get("affected_components", []) if isinstance(t, dict) else []
        for c in comps:
            if isinstance(c, str):
                affected.append(c)
    md_ctx["source_files"] = _safe_join(_unique_ordered(sorted(affected)))

    stories: List[Dict[str, Any]] = []
    for t in content.get("tasks", []) if isinstance(content, dict) else []:
        us = t.get("supporting_user_stories", []) if isinstance(t, dict) else []
        for s in us:
            if isinstance(s, dict):
                stories.append({"id": s.get("id", ""), "description": s.get("description", "")})
    stories = _unique_ordered(sorted(stories, key=lambda x: (str(x.get("id", "")), str(x.get("description", "")))), key=lambda x: (x.get("id"), x.get("description")))
    md_ctx["user_stories"] = stories

    interfaces = content.get("interfaces", {}) if isinstance(content, dict) else {}
    # HTTP and env
    http_eps = interfaces.get("http", []) if isinstance(interfaces, dict) else []
    if isinstance(http_eps, list):
        http_eps = sorted(http_eps, key=lambda e: (str(e.get("method", "")), str(e.get("path", ""))))
    env_vars = interfaces.get("env", []) if isinstance(interfaces, dict) else []
    if isinstance(env_vars, list):
        env_vars = sorted(env_vars, key=lambda e: str(e.get("name", "")))
    md_ctx["http"] = {"endpoints": http_eps}
    md_ctx["env"] = env_vars
    base_port = ""
    try:
        for e in env_vars:
            if isinstance(e, dict) and e.get("name") == "PORT":
                base_port = str(e.get("default", ""))
                break
    except Exception:
        base_port = ""
    md_ctx["base_port"] = base_port
    md_ctx["runtime"] = meta.get("runtime", "")
    md_ctx["env_port_summary"] = f"PORT={base_port}" if base_port else ""
    md_ctx["process_model"] = meta.get("process_model", "")

    # Contracts mapping
    contracts_in = content.get("contracts", []) if isinstance(content, dict) else []
    mapped_contracts: List[Dict[str, Any]] = []
    for c in contracts_in:
        if not isinstance(c, dict):
            continue
        mapped_contracts.append({
            "id": c.get("id", ""),
            "title": c.get("title", ""),
            "pre": _safe_join(c.get("preconditions", [])),
            "post": _safe_join(c.get("postconditions", [])),
            "invariants": _safe_join(c.get("invariants", [])),
            "rollback": _safe_join(c.get("rollback", [])),
            "security": _safe_join(c.get("security", [])),
            "validation": _safe_join(c.get("validation", [])),
        })
    mapped_contracts = sorted(mapped_contracts, key=lambda x: str(x.get("id", "")))
    md_ctx["contracts"] = mapped_contracts

    # Schemas
    schemas = content.get("schemas", {}) if isinstance(content, dict) else {}
    md_ctx["openapi"] = schemas.get("openapi", "") if isinstance(schemas, dict) else ""

    # Application/Class interfaces (code-level)
    code_if = []
    if isinstance(interfaces, dict):
        code_if = interfaces.get("code", []) or []
    norm_code_if = []
    for ci in code_if if isinstance(code_if, list) else []:
        if not isinstance(ci, dict):
            continue
        methods = ci.get("methods", []) if isinstance(ci.get("methods"), list) else []
        norm_methods = []
        for m in methods:
            if not isinstance(m, dict):
                continue
            params = m.get("params", [])
            if isinstance(params, list):
                params_str = ", ".join(str(p) for p in params)
            else:
                params_str = str(params) if params is not None else ""
            norm_methods.append({
                "name": m.get("name", ""),
                "params": params_str,
                "returns": m.get("returns", "void"),
                "summary": m.get("summary", ""),
                "preconditions": ", ".join(m.get("preconditions", [])) if isinstance(m.get("preconditions"), list) else (m.get("preconditions", "")),
                "postconditions": ", ".join(m.get("postconditions", [])) if isinstance(m.get("postconditions"), list) else (m.get("postconditions", "")),
            })
        norm_code_if.append({
            "name": ci.get("name", ""),
            "package": ci.get("package", ""),
            "description": ci.get("description", ""),
            "responsibilities": ", ".join(ci.get("responsibilities", [])) if isinstance(ci.get("responsibilities"), list) else (ci.get("responsibilities", "")),
            "invariants": ", ".join(ci.get("invariants", [])) if isinstance(ci.get("invariants"), list) else (ci.get("invariants", "")),
            "methods": norm_methods,
        })
    md_ctx["code_interfaces"] = norm_code_if

    # Implementation steps
    impl_steps = []
    for t in content.get("tasks", []) if isinstance(content, dict) else []:
        if isinstance(t, dict):
            impl_steps.append({"task": t.get("task", ""), "objective": t.get("objective", "")})
    md_ctx["implementation_steps"] = impl_steps

    # Renderer utilities
    def _get_by_path(ctx: Dict[str, Any], path: str) -> Any:
        cur: Any = ctx
        for part in path.split('.'):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return None
        return cur

    def _render_vars(text: str, scope: Dict[str, Any]) -> str:
        import re as _re
        def repl(m):
            k = m.group(1).strip()
            v = _get_by_path(scope, k) if '.' in k else scope.get(k)
            if v is None:
                return ""
            if isinstance(v, list):
                return ", ".join(str(x) for x in v)
            if isinstance(v, (dict)):
                try:
                    return json.dumps(v, indent=2)
                except Exception:
                    return str(v)
            return str(v)
        return _re.sub(r"{{\s*([^#/{][^}]*)\s*}}", repl, text)

    def _render_each(text: str, ctx: Dict[str, Any]) -> str:
        import re as _re
        pattern = _re.compile(r"{{#each\s+([a-zA-Z0-9_\.]+)}}(.*?){{/each}}", _re.DOTALL)
        while True:
            m = pattern.search(text)
            if not m:
                break
            path = m.group(1)
            block = m.group(2)
            items = _get_by_path(ctx, path)
            rendered = ""
            if isinstance(items, list) and len(items) > 0:
                for it in items:
                    if isinstance(it, dict):
                        inner = _render_each(block, {**ctx, **it})
                        rendered += _render_vars(inner, {**ctx, **it})
                    else:
                        inner = _render_each(block, {**ctx, "this": it})
                        rendered += _render_vars(inner, {**ctx, "this": it})
            # Replace entire block with rendered (empty string if no items or not a list)
            text = text[: m.start()] + rendered + text[m.end():]
        return text

    rendered_md = _render_vars(_render_each(raw_md_template, md_ctx), md_ctx)
    # Clean up any stray closing tags that may remain after nested-each processing
    rendered_md = re.sub(r"^\s*{{/each}}\s*$", "", rendered_md, flags=re.MULTILINE)

    # Orphan each for implementation_steps
    orphan_tag = "{{#each implementation_steps}}"
    if orphan_tag in rendered_md:
        impl_steps_lines = []
        for s in md_ctx.get("implementation_steps", []) or []:
            if isinstance(s, dict):
                t = str(s.get("task", "")).strip()
                obj = str(s.get("objective", "")).strip()
                if t or obj:
                    impl_steps_lines.append(f"- {t}: {obj}" if t and obj else f"- {t}{obj}")
        replacement = ("\n" + "\n".join(impl_steps_lines) + "\n") if impl_steps_lines else "\n"
        rendered_md = rendered_md.replace(orphan_tag, replacement)

    appendix = (
        "\n\n---\n\n## Appendix A — Consolidated PRP JSON (authoritative machine content)\n\n" +
        "```json\n" + json.dumps(content, indent=2) + "\n```\n"
    )
    return rendered_md + appendix


def _select_consolidator_agent(preferred: Optional[str]) -> str:
    """Select a consolidator agent, preferring the provided name, else first available registry agent."""
    if preferred:
        return preferred
    candidates = [
        "project-manager",  # default to project-manager for consolidation
        "architect-reviewer",
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
            f"TARGET JSON SCHEMA (conform exactly; your 'content' must validate against this schema):\n{template_text}\n\n"
        f"INPUT DRAFTS (JSON array):\n{inputs_text}\n\n"
        "Output: Return JSON only with this shape:\n"
        "{\n"
        "  \"outputs\": { \"draft_file\": \"<suggested-path>.json\" },\n"
        "  \"content\": <the filled JSON object matching the target template>\n"
        "}\n"
        "Do not include commentary outside JSON. Do not wrap content as a string."
    )


def _wrap_content_only(obj: Dict[str, Any], dest_hint: str) -> Dict[str, Any]:
    """If the payload lacks standard wrapper but looks like content, wrap it.

    Ensures it matches { outputs: { draft_file }, content: {...} }.
    """
    if "outputs" in obj and "content" in obj and isinstance(obj.get("outputs"), dict) and isinstance(obj.get("content"), dict):
        return obj
    # Heuristics: consider it "content-like" only if it contains expected top-level keys
    looks_like_content = any(k in obj for k in ("version", "metadata", "tasks", "contracts", "interfaces", "schemas"))
    content_obj: Dict[str, Any] = obj if looks_like_content else {}
    return {"outputs": {"draft_file": dest_hint}, "content": content_obj}


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
    ap.add_argument("--arg", dest="feature_description", required=False, default="prp/idea.md", help="Feature description text or path to a file. Defaults to /prp/idea.md with fallback prp/idea.md.")
    ap.add_argument("--template", default="templates/prp/draft-prp-004.json")
    ap.add_argument("--prompt", default="templates/prp/draft-prp-004.md", help="Optional prompt file to include verbatim in the consolidation instruction for TASK004")
    ap.add_argument("--system-prompt-file", default=None, help="Optional system context file to append to the agent system text (cache-friendly, used for determinism)")
    ap.add_argument("--agent")
    ap.add_argument("--override-agent", dest="override_agent", default=None, help="Alias of --agent for compatibility with prior steps")
    ap.add_argument("--consolidated-path", dest="consolidated_path", default=None, help="Path to consolidated tasks JSON (preferred for TASK004)")
    ap.add_argument("--consolidated-json", dest="consolidated_json", default=None, help="Inline JSON string for consolidated tasks (overrides --consolidated-path if provided)")
    ap.add_argument("--timestamp")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--max-tokens", type=int, default=64000)
    ap.add_argument("--validate-schema", action="store_true", help="Validate content against the JSON Schema before writing active outputs")
    ap.add_argument("--limit-drafts", type=int, default=0)
    ap.add_argument("--repair-attempts", type=int, default=1)
    # Long-running batch controls
    ap.add_argument("--no-poll", action="store_true", help="Create the batch and exit immediately; use --resume-batch later to finalize")
    ap.add_argument("--resume-batch", dest="resume_batch", default=None, help="Resume by retrieving results for an existing batch ID and finalizing outputs")
    ap.add_argument("--max-polls", dest="cli_max_polls", type=int, default=None, help="Override max polls before timing out (else env TASK004_MAX_POLLS, default 180)")
    ap.add_argument("--poll-interval", dest="cli_poll_interval", type=float, default=None, help="Override seconds between polls (else env TASK004_POLL_INTERVAL, default 2.0)")
    args = ap.parse_args()

    try:
        load_dotenv(find_dotenv(usecwd=True), override=False)
    except Exception:
        pass
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in environment or .env")
        return 2

    # Resolve feature description with file support and fallbacks (aligns with other steps)
    feature = args.feature_description
    potential_path = None
    if feature is None or str(feature).strip() == "":
        # Defaults: absolute then relative
        defaults = [
            Path("prp/idea.md")
        ]
        for candidate in defaults:
            if candidate.exists():
                potential_path = str(candidate)
                break
    else:
        if feature.startswith("@"):
            potential_path = feature[1:]
        elif Path(feature).exists():
            potential_path = feature
    if potential_path:
        try:
            feature = Path(potential_path).read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            feature = feature or ""
    if not feature:
        feature = "auto-generated prp-004 run"
    tpath = Path(args.template)
    if not tpath.exists():
        print(f"ERROR: template not found: {tpath}")
        return 2
    template_text = tpath.read_text(encoding="utf-8", errors="replace")

    # Prefer consolidated tasks JSON input for TASK004
    consolidated_obj: Optional[Dict[str, Any]] = None
    if args.consolidated_json:
        try:
            consolidated_obj = json.loads(args.consolidated_json)
            if not isinstance(consolidated_obj, dict):
                consolidated_obj = None
        except Exception as e:
            print(f"ERROR: Failed to parse --consolidated-json: {e}")
            return 2
    elif args.consolidated_path:
        pth = Path(args.consolidated_path)
        if not pth.exists():
            print(f"ERROR: --consolidated-path not found: {pth}")
            return 2
        obj = _read_json(pth)
        if not isinstance(obj, dict):
            print(f"ERROR: --consolidated-path is not a JSON object: {pth}")
            return 2
        consolidated_obj = obj

    items: List[Dict[str, Any]] = []
    if consolidated_obj is None:
        # Fallback: consolidate latest timestamp drafts (no slug filtering)
        ts = args.timestamp or _find_latest_timestamp_any()
        if not ts:
            # Auto-create a minimal consolidated object so the step can run unattended
            consolidated_obj = {
                "content": [],
                "outputs": {"draft_file": "prp/drafts/P-000-T-004.json"},
                "meta": {"feature": feature, "note": "auto-generated consolidated stub (no prior drafts)"}
            }
        files = _list_draft_files(None, ts) if ts else []
        # If no drafts in prp/drafts, attempt to pull latest from archive
        if not files:
            archived = _list_latest_archived_drafts()
            files = archived
        if not files and consolidated_obj is None:
            # If still no inputs and we didn't set consolidated_obj, fail explicitly
            print("ERROR: No inputs available for TASK004 and no fallback created; provide --consolidated-path or --consolidated-json")
            return 2
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
        if not items and consolidated_obj is None:
            print("ERROR: No readable draft JSONs to consolidate and no fallback consolidated object available")
            return 2

    agent_name = _select_consolidator_agent(args.override_agent or args.agent)
    system_text = load_agent_text(agent_name)
    if args.system_prompt_file and Path(args.system_prompt_file).exists():
        # Append deterministic system context file verbatim (e.g., YAML system_context summary)
        extra = Path(args.system_prompt_file).read_text(encoding="utf-8", errors="replace")
        system_text = system_text.rstrip() + "\n\n" + extra.strip() + "\n"
    # Optional external prompt
    prefix = Path(args.prompt).read_text(encoding="utf-8", errors="replace") if Path(args.prompt).exists() else ""
    if consolidated_obj is not None:
        # Build a simpler prompt targeting the schema with the consolidated tasks object
        consolidated_text = json.dumps(consolidated_obj, ensure_ascii=False)
        user_text = (
            "Task: Transform CONSOLIDATED TASKS JSON into a single PRP that VALIDATES against the TARGET JSON SCHEMA.\n\n"
            "Rules:\n"
            "- STRICT SCHEMA CONFORMANCE for 'content'\n"
            "- Derive contracts, interfaces, schemas, security, testing, deployment, and traceability from tasks\n"
            "- Keep ordering deterministic; generate stable IDs per conventions if needed\n\n"
            f"Feature Description:\n{feature}\n\n"
            f"TARGET JSON SCHEMA (your 'content' must validate against this schema):\n{template_text}\n\n"
            f"CONSOLIDATED TASKS (JSON object):\n{consolidated_text}\n\n"
            "Output: JSON only with wrapper shape { 'outputs': { 'draft_file': string }, 'content': object }\n"
        )
    else:
        user_text = _build_consolidation_prompt(feature, template_text, items)
    if prefix:
        user_text = "Task Prompt (verbatim, read fully):\n" + prefix.strip() + "\n\n" + user_text

    # Offline short-circuit: if consolidated_obj is already a PRP-shaped content, bypass AI and write outputs
    if consolidated_obj is not None and _looks_like_content(consolidated_obj):
        seq_path = Path("prp/prp_seq.json")
        prp_id = _alloc_prp_id(seq_path)
        draft_file_path = f"prp/drafts/P-{prp_id:03d}-T-004.json"
        payload = {"outputs": {"draft_file": draft_file_path}, "content": consolidated_obj}
        # Write wrapper draft
        _ensure_parent_dir(draft_file_path)
        Path(draft_file_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Saved wrapper draft -> {draft_file_path}")
        # Proceed to schema validation + active/markdown writing below
        content = consolidated_obj
        # Optionally validate
        if args.validate_schema and _looks_like_content(content):
            try:
                import jsonschema  # type: ignore
                schema_obj = json.loads(Path(args.template).read_text(encoding="utf-8", errors="replace"))
                jsonschema.validate(instance=content, schema=schema_obj)
                print("Schema validation: PASS")
            except Exception as e:
                print(f"Schema validation: FAIL -> {e}")
        # Write active JSON and Markdown (offline path)
        active_json = Path("prp/active/PRP-004.json")
        _ensure_parent_dir(str(active_json))
        active_json.write_text(json.dumps(content, indent=2), encoding="utf-8")
        md_path = Path("prp/active/PRP-004.md")
        md_text = _render_markdown_from_content(content, args.prompt)
        _ensure_parent_dir(str(md_path))
        md_path.write_text(md_text, encoding="utf-8")
        print(f"Wrote active outputs -> {active_json} and {md_path}")
        return 0

    # Online path
    client = anthropic.Anthropic(api_key=api_key)
    # Helper to persist batch metadata for later resume
    def _persist_batch(kind: str, batch_id: str, req_obj: Dict[str, Any], timestamp: str) -> None:
        meta_path = Path(f"tmp/batches/t004/{batch_id}.json")
        _ensure_parent_dir(str(meta_path))
        meta = {"kind": kind, "batch_id": batch_id, "created_at": timestamp, "request": req_obj}
        try:
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            print(f"Saved batch metadata -> {meta_path}")
        except Exception as e:
            print(f"WARN: Failed to persist batch metadata: {e}")
    batch_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Build cache-friendly, deterministic system blocks
    agents_catalog = json.dumps(_list_agents_catalog(), ensure_ascii=False)
    schema_text = _read_text(Path("docs/schema.json")) or "{}"
    # Only include roots of task responses to avoid loading giant content redundantly
    task_roots: List[Dict[str, str]] = []
    for p in sorted(Path("prp/drafts").glob("*.json"), key=lambda x: x.name):
        task_roots.append({"file": str(p)})

    req = {
        "custom_id": _short_custom_id("t004", batch_ts),
        "params": {
            "model": args.model,
            "max_tokens": int(args.max_tokens),
            "temperature": 0.2,
            "system": [
                {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                {"type": "text", "text": "KNOWN AGENTS CATALOG (JSON)\n" + agents_catalog, "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                {"type": "text", "text": "REPO CONTEXT INDEX (JSON)\n" + schema_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                {"type": "text", "text": "TASK RESPONSES (JSON)\n" + json.dumps(task_roots, ensure_ascii=False), "cache_control": {"type": "ephemeral", "ttl": "1h"}},
            ],
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_text}]}
            ],
        },
    }

    # Resume mode: fetch results for an existing batch id
    if args.resume_batch:
        batch_id = args.resume_batch
        print(f"Resuming existing batch -> {batch_id}")
        # Poll once or up to limits depending on provided flags
        polls = 0
        max_polls = args.cli_max_polls if args.cli_max_polls is not None else int(os.getenv("TASK004_MAX_POLLS", "1"))
        poll_interval = args.cli_poll_interval if args.cli_poll_interval is not None else float(os.getenv("TASK004_POLL_INTERVAL", "2.0"))
        while True:
            b = client.messages.batches.retrieve(batch_id)
            if b.processing_status in ("ended", "failed", "expired"):
                break
            if max_polls > 0 and polls >= max_polls:
                print(f"INFO: Resume poll limit reached ({polls}); status={b.processing_status}. Try again later.")
                return 3
            print(f"resume poll: status={b.processing_status}")
            import time as _t
            _t.sleep(poll_interval)
            polls += 1
        results = list(client.messages.batches.results(batch_id))
    else:
        batch = client.messages.batches.create(requests=cast(Any, [req]))
        print(f"batch_id={batch.id} status={batch.processing_status} count=1")
        _persist_batch("create", batch.id, req, batch_ts)
        if args.no_poll:
            print("--no-poll set: exiting after creation. Use --resume-batch <id> to finalize.")
            return 0
        # Poll with timeout to avoid indefinite waits; configurable via CLI/env
        polls = 0
        max_polls = args.cli_max_polls if args.cli_max_polls is not None else int(os.getenv("TASK004_MAX_POLLS", "180"))
        poll_interval = args.cli_poll_interval if args.cli_poll_interval is not None else float(os.getenv("TASK004_POLL_INTERVAL", "2.0"))
        while True:
            b = client.messages.batches.retrieve(batch.id)
            if b.processing_status in ("ended", "failed", "expired"):
                break
            if max_polls > 0 and polls >= max_polls:
                print(f"ERROR: Batch polling timed out after {polls} polls (status={b.processing_status})")
                timeout_path = f"tmp/raw/t004-timeout-{batch_ts}.txt"
                _ensure_parent_dir(timeout_path)
                Path(timeout_path).write_text(f"status={b.processing_status}\n", encoding="utf-8")
                return 3
            print(f"poll: status={b.processing_status}")
            import time as _t
            _t.sleep(poll_interval)
            polls += 1
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
        raw_out = f"tmp/raw/t004-consolidate-{batch_ts}.txt"
        _ensure_parent_dir(raw_out)
        Path(raw_out).write_text(combined or "", encoding="utf-8")
        print(f"Saved raw output for inspection -> {raw_out}")
        return 1

    # If the model returned content-only JSON, wrap it into the standard wrapper
    if not _valid(payload):
        coerced = _wrap_content_only(payload if isinstance(payload, dict) else {}, "prp/drafts/P-{prp_id}-T-004.json")
        if _valid(coerced):
            payload = coerced

    if not _valid(payload):
        diag_json = f"tmp/raw/t004-consolidate-{batch_ts}-invalid.json"
        diag_txt = f"tmp/raw/t004-consolidate-{batch_ts}-raw.txt"
        _ensure_parent_dir(diag_json)
        Path(diag_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        Path(diag_txt).write_text(combined or "", encoding="utf-8")
        print(f"WARN: Consolidation returned invalid JSON. Saved diagnostics -> {diag_json} and {diag_txt}")

        attempts = max(0, int(args.repair_attempts))
        if attempts <= 0:
            return 2

        def _build_repair_prompt(invalid_obj: Dict[str, Any], raw_text: str, template_text: str, feature_desc: str) -> str:
            suggested_name = f"t004-{{timestamp}}-consolidated.json"
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
            "custom_id": _short_custom_id("t004-repair", batch_ts),
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
        _persist_batch("repair", rep_batch.id, repair_req, batch_ts)
        rep_polls = 0
        rep_max_polls = args.cli_max_polls if args.cli_max_polls is not None else int(os.getenv("TASK004_MAX_POLLS", "180"))
        rep_poll_interval = args.cli_poll_interval if args.cli_poll_interval is not None else float(os.getenv("TASK004_POLL_INTERVAL", "2.0"))
        while True:
            b = client.messages.batches.retrieve(rep_batch.id)
            if b.processing_status in ("ended", "failed", "expired"):
                break
            if rep_max_polls > 0 and rep_polls >= rep_max_polls:
                print(f"ERROR: Repair batch polling timed out after {rep_polls} polls (status={b.processing_status})")
                rep_timeout_path = f"tmp/raw/t004-repair-timeout-{batch_ts}.txt"
                _ensure_parent_dir(rep_timeout_path)
                Path(rep_timeout_path).write_text(f"status={b.processing_status}\n", encoding="utf-8")
                return 3
            print(f"repair poll: status={b.processing_status}")
            import time as _t
            _t.sleep(rep_poll_interval)
            rep_polls += 1
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
            rep_diag = f"tmp/raw/t004-consolidate-{batch_ts}-repair-invalid.json"
            _ensure_parent_dir(rep_diag)
            Path(rep_diag).write_text(rep_combined or "", encoding="utf-8")
            print(f"ERROR: Repair attempt failed to produce valid wrapper. Saved diagnostics -> {rep_diag}")
            return 2
        payload = rep_payload

    # Enforce output path pattern and write wrapper + active outputs
    seq_path = Path("prp/prp_seq.json")
    prp_id = _alloc_prp_id(seq_path)
    draft_file_path = f"prp/drafts/P-{prp_id:03d}-T-004.json"
    # Overwrite/ensure draft_file matches expected pattern
    if not isinstance(payload.get("outputs"), dict):
        payload["outputs"] = {}
    payload["outputs"]["draft_file"] = draft_file_path

    # Write wrapper draft
    _ensure_parent_dir(draft_file_path)
    Path(draft_file_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved wrapper draft -> {draft_file_path}")

    # Optionally validate content against schema (only if it looks like PRP content)
    content = payload.get("content", {}) if isinstance(payload.get("content"), dict) else {}
    if args.validate_schema and _looks_like_content(content):
        try:
            import jsonschema  # type: ignore
            schema_obj = json.loads(Path(args.template).read_text(encoding="utf-8", errors="replace"))
            jsonschema.validate(instance=content, schema=schema_obj)
            print("Schema validation: PASS")
        except Exception as e:
            print(f"Schema validation: FAIL -> {e}")
            # Non-fatal by default; YAML can enforce fail-if-invalid
    elif args.validate_schema:
        print("Schema validation: SKIP (content is empty or not PRP-shaped)")
    active_json = Path("prp/active/PRP-004.json")
    _ensure_parent_dir(str(active_json))
    # Only write active content if it looks like a valid PRP content object; otherwise preserve existing
    if _looks_like_content(content):
        active_json.write_text(json.dumps(content, indent=2), encoding="utf-8")
    else:
        print("WARN: Content is empty/non-PRP; preserving existing prp/active/PRP-004.json")

    # Write active Markdown by rendering the template with a minimal Handlebars-like engine
    md_path = Path("prp/active/PRP-004.md")
    template_md = Path(args.prompt)
    raw_md_template = template_md.read_text(encoding="utf-8", errors="replace").rstrip() if template_md.exists() else "# PRP-004"

    # Build a rendering context derived from content
    def _safe_join(val: Any, sep: str = ", ") -> str:
        if isinstance(val, list):
            return sep.join(str(x) for x in val)
        if isinstance(val, (str, int, float)) or val is None:
            return "" if val is None else str(val)
        return json.dumps(val)

    def _unique_ordered(seq: List[Any], key=lambda x: x) -> List[Any]:
        seen = set()
        out = []
        for item in seq:
            k = key(item)
            if k in seen:
                continue
            seen.add(k)
            out.append(item)
        return out

    md_ctx: Dict[str, Any] = {}
    meta = content.get("metadata", {}) if isinstance(content, dict) else {}
    md_ctx["purpose"] = meta.get("feature", "")
    md_ctx["scope"] = meta.get("scope", "")
    md_ctx["components"] = _safe_join(meta.get("components", []))
    md_ctx["out_of_scope"] = _safe_join(meta.get("out_of_scope", []))

    # Source files: aggregate from tasks[].affected_components
    affected: List[str] = []
    for t in content.get("tasks", []) if isinstance(content, dict) else []:
        comps = t.get("affected_components", []) if isinstance(t, dict) else []
        for c in comps:
            if isinstance(c, str):
                affected.append(c)
    md_ctx["source_files"] = _safe_join(_unique_ordered(sorted(affected)))

    # User stories: aggregate unique by id from tasks[].supporting_user_stories
    stories: List[Dict[str, Any]] = []
    for t in content.get("tasks", []) if isinstance(content, dict) else []:
        us = t.get("supporting_user_stories", []) if isinstance(t, dict) else []
        for s in us:
            if isinstance(s, dict):
                stories.append({"id": s.get("id", ""), "description": s.get("description", "")})
    stories = _unique_ordered(sorted(stories, key=lambda x: (str(x.get("id", "")), str(x.get("description", "")))), key=lambda x: (x.get("id"), x.get("description")))
    md_ctx["user_stories"] = stories

    # Interfaces: http endpoints and env
    interfaces = content.get("interfaces", {}) if isinstance(content, dict) else {}
    http_eps = interfaces.get("http", []) if isinstance(interfaces, dict) else []
    if isinstance(http_eps, list):
        http_eps = sorted(http_eps, key=lambda e: (str(e.get("method", "")), str(e.get("path", ""))))
    env_vars = interfaces.get("env", []) if isinstance(interfaces, dict) else []
    if isinstance(env_vars, list):
        env_vars = sorted(env_vars, key=lambda e: str(e.get("name", "")))
    md_ctx["http"] = {"endpoints": http_eps}
    md_ctx["env"] = env_vars
    # Base port summary if available
    base_port = ""
    try:
        for e in env_vars:
            if isinstance(e, dict) and e.get("name") == "PORT":
                base_port = str(e.get("default", ""))
                break
    except Exception:
        base_port = ""
    md_ctx["base_port"] = base_port
    md_ctx["runtime"] = meta.get("runtime", "")
    md_ctx["env_port_summary"] = f"PORT={base_port}" if base_port else ""
    md_ctx["process_model"] = meta.get("process_model", "")

    # Contracts mapping to simplified fields
    contracts_in = content.get("contracts", []) if isinstance(content, dict) else []
    mapped_contracts: List[Dict[str, Any]] = []
    for c in contracts_in:
        if not isinstance(c, dict):
            continue
        mapped_contracts.append({
            "id": c.get("id", ""),
            "title": c.get("title", ""),
            "pre": _safe_join(c.get("preconditions", [])),
            "post": _safe_join(c.get("postconditions", [])),
            "invariants": _safe_join(c.get("invariants", [])),
            "rollback": _safe_join(c.get("rollback", [])),
            "security": _safe_join(c.get("security", [])),
            "validation": _safe_join(c.get("validation", [])),
        })
    mapped_contracts = sorted(mapped_contracts, key=lambda x: str(x.get("id", "")))
    md_ctx["contracts"] = mapped_contracts

    # Schemas
    schemas = content.get("schemas", {}) if isinstance(content, dict) else {}
    # Full OpenAPI string (not an excerpt)
    md_ctx["openapi"] = schemas.get("openapi", "") if isinstance(schemas, dict) else ""
    # Application/Class interfaces (code-level)
    code_if = []
    if isinstance(interfaces, dict):
        code_if = interfaces.get("code", []) or []
    # Normalize methods for rendering
    norm_code_if = []
    for ci in code_if if isinstance(code_if, list) else []:
        if not isinstance(ci, dict):
            continue
        methods = ci.get("methods", []) if isinstance(ci.get("methods"), list) else []
        norm_methods = []
        for m in methods:
            if not isinstance(m, dict):
                continue
            params = m.get("params", [])
            if isinstance(params, list):
                params_str = ", ".join(str(p) for p in params)
            else:
                params_str = str(params) if params is not None else ""
            norm_methods.append({
                "name": m.get("name", ""),
                "params": params_str,
                "returns": m.get("returns", "void"),
                "summary": m.get("summary", ""),
                "preconditions": ", ".join(m.get("preconditions", [])) if isinstance(m.get("preconditions"), list) else (m.get("preconditions", "")),
                "postconditions": ", ".join(m.get("postconditions", [])) if isinstance(m.get("postconditions"), list) else (m.get("postconditions", "")),
            })
        norm_code_if.append({
            "name": ci.get("name", ""),
            "package": ci.get("package", ""),
            "description": ci.get("description", ""),
            "responsibilities": ", ".join(ci.get("responsibilities", [])) if isinstance(ci.get("responsibilities"), list) else (ci.get("responsibilities", "")),
            "invariants": ", ".join(ci.get("invariants", [])) if isinstance(ci.get("invariants"), list) else (ci.get("invariants", "")),
            "methods": norm_methods,
        })
    md_ctx["code_interfaces"] = norm_code_if
    # Implementation steps: derive simple list from tasks
    impl_steps = []
    for t in content.get("tasks", []) if isinstance(content, dict) else []:
        if isinstance(t, dict):
            impl_steps.append({"task": t.get("task", ""), "objective": t.get("objective", "")})
    md_ctx["implementation_steps"] = impl_steps

    # Simple renderer supporting {{key}} and {{#each path}}...{{/each}}
    def _get_by_path(ctx: Dict[str, Any], path: str) -> Any:
        cur: Any = ctx
        for part in path.split('.'):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return None
        return cur

    def _render_vars(text: str, scope: Dict[str, Any]) -> str:
        import re as _re
        def repl(m):
            k = m.group(1).strip()
            v = _get_by_path(scope, k) if '.' in k else scope.get(k)
            if v is None:
                return ""
            if isinstance(v, list):
                return ", ".join(str(x) for x in v)
            if isinstance(v, (dict)):
                try:
                    return json.dumps(v, indent=2)
                except Exception:
                    return str(v)
            return str(v)
        return _re.sub(r"{{\s*([^#/{][^}]*)\s*}}", repl, text)

    def _render_each(text: str, ctx: Dict[str, Any]) -> str:
        import re as _re
        pattern = _re.compile(r"{{#each\s+([a-zA-Z0-9_\.]+)}}(.*?){{/each}}", _re.DOTALL)
        while True:
            m = pattern.search(text)
            if not m:
                break
            path = m.group(1)
            block = m.group(2)
            items = _get_by_path(ctx, path)
            rendered = ""
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict):
                        # Recursively render nested each blocks with the item scope, then substitute vars
                        inner = _render_each(block, {**ctx, **it})
                        rendered += _render_vars(inner, {**ctx, **it})
                    else:
                        inner = _render_each(block, {**ctx, "this": it})
                        rendered += _render_vars(inner, {**ctx, "this": it})
            text = text[: m.start()] + rendered + text[m.end():]
        return text

    rendered_md = _render_vars(_render_each(raw_md_template, md_ctx), md_ctx)
    # Clean up any stray closing tags that may remain after nested-each processing
    import re as _re_cleanup
    rendered_md = _re_cleanup.sub(r"^\s*{{/each}}\s*$", "", rendered_md, flags=_re_cleanup.MULTILINE)

    # Fallback: handle orphan "{{#each implementation_steps}}" without closing tag by expanding it inline
    orphan_tag = "{{#each implementation_steps}}"
    if orphan_tag in rendered_md:
        impl_steps_lines = []
        for s in md_ctx.get("implementation_steps", []) or []:
            if isinstance(s, dict):
                t = str(s.get("task", "")).strip()
                obj = str(s.get("objective", "")).strip()
                if t or obj:
                    impl_steps_lines.append(f"- {t}: {obj}" if t and obj else f"- {t}{obj}")
        replacement = ("\n" + "\n".join(impl_steps_lines) + "\n") if impl_steps_lines else "\n"
        rendered_md = rendered_md.replace(orphan_tag, replacement)

    appendix = (
        "\n\n---\n\n## Appendix A — Consolidated PRP JSON (authoritative machine content)\n\n" +
        "```json\n" + json.dumps(content, indent=2) + "\n```\n"
    )
    final_md = rendered_md + appendix
    _ensure_parent_dir(str(md_path))
    md_path.write_text(final_md, encoding="utf-8")
    print(f"Wrote active outputs -> {active_json} and {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
