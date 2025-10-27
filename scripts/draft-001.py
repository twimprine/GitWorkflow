#!/usr/bin/env python3
from __future__ import annotations
"""
draft-001.py — TASK001 panel decomposition runner

Purpose:
- Queries a fixed core panel of agents to decompose a feature into atomic PRP tasks.
- Enforces strict JSON wrapper output and saves results per agent without overwriting.

Inputs (CLI):
- --arg: Feature description text or path to a file (defaults to /prp/idea.md with relative fallback prp/idea.md).
- --agents: Comma-separated agent ids (defaults to the core panel).
- --model: Anthropic model id (default: claude-sonnet-4-5).
- --template: Path to TASK001 JSON template. The user prompt always loads templates/prp/draft-prp-001.json.

Behavior:
- Uses Anthropic Messages Batch API to issue one request per agent.
- Extracts text blocks and parses the first JSON object or fenced JSON.
- If the wrapper is valid ({ outputs.draft_file, content }), saves under prp/drafts with timestamp, task id, and agent suffix.
- Otherwise saves the JSON payload to tmp/panel/<slug>/<agent>.json.
- Collects delegation_suggestions across agents for later passes.

Outputs:
- prp/drafts/*-task001-<agent>.json for wrapper-valid responses.
- tmp/panel/<slug>/<agent>.json for non-wrapper panel outputs.
"""
import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv, find_dotenv
import anthropic

# Standalone agent registry
AGENT_DIRS = [Path(os.path.expanduser("~/.claude/agents"))]
# Optional: allow additional agent directories via env var (colon-separated)
_extra_dirs = os.getenv("CLAUDE_AGENT_DIRS", "").strip()
if _extra_dirs:
    for _d in _extra_dirs.split(":"):
        if _d.strip():
            AGENT_DIRS.append(Path(_d.strip()))
MODEL_ID = "claude-sonnet-4-5"


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


CORE_PANEL = [
    "project-manager",
    "application-architect",
    "security-reviewer",
    "ux-designer",
    "test-runner",
    "devops-engineer",
]


def _slugify(text: str) -> str:
    """Make a filesystem-friendly slug from free text."""
    import re
    txt = text.lower().strip()
    txt = re.sub(r"[^a-z0-9\-\s]", "", txt)
    txt = re.sub(r"\s+", "-", txt)
    txt = re.sub(r"-+", "-", txt)
    return txt or "draft"


def _ensure_parent_dir(path_str: str) -> None:
    """Ensure parent directory of the path exists."""
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)


def _extract_suggested_agents(payload: dict) -> set[str]:
    """Return a set of agent names from various suggestion shapes.

    Supports both top-level and content-nested fields:
    - delegation_suggestions: ["agent: reason", {"agent-name": "reason"}, {"agent": "name", ...}]
    - delegation_recommendations / recommended_agents as aliases
    """
    names: set[str] = set()
    def _add(name: str | None):
        if isinstance(name, str):
            n = name.strip()
            if n:
                names.add(n)
    def _process_list(lst: list[Any]):
        for entry in lst:
            if isinstance(entry, str):
                _add(entry.split(":", 1)[0])
            elif isinstance(entry, dict):
                # mapping style {"ux-designer": "reason"}
                for k, v in entry.items():
                    if k == "agent" and isinstance(v, str):
                        _add(v)
                    elif isinstance(k, str) and k not in ("reason",):
                        _add(k)
    if isinstance(payload, dict):
        for key in ("delegation_suggestions", "delegation_recommendations", "recommended_agents"):
            val = payload.get(key)
            if isinstance(val, list):
                _process_list(val)
        content = payload.get("content")
        if isinstance(content, dict):
            for key in ("delegation_suggestions", "delegation_recommendations", "recommended_agents"):
                val = content.get(key)
                if isinstance(val, list):
                    _process_list(val)
    return names


def _find_latest_timestamp_for_slug(slug: str) -> str | None:
    """Find the most recent timestamp found in prp/drafts filenames for this slug."""
    import re
    draft_dir = Path("prp/drafts")
    if not draft_dir.exists():
        return None
    ts_re = re.compile(r"(?P<ts>\d{8}-\d{6})")
    candidates: list[str] = []
    for p in draft_dir.glob(f"*{_slugify(slug)}*.json"):
        m = ts_re.search(p.name)
        if m:
            candidates.append(m.group("ts"))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0]


def _dry_run_print_suggestions(slug: str, ts: str | None, scan_tmp_panel: bool) -> int:
    """Scan drafts (and optionally tmp/panel) for suggestions, resolve against registry, and print a report."""
    draft_dir = Path("prp/drafts")
    if not ts:
        ts = _find_latest_timestamp_for_slug(slug)
    if not ts:
        print("No timestamp detected; provide --timestamp or generate an initial draft first.")
        return 2
    # Collect suggestions
    suggested: set[str] = set()
    pattern = f"*{slug}*{ts}*.json"
    for p in draft_dir.glob(pattern):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            suggested |= _extract_suggested_agents(data)
    if scan_tmp_panel:
        panel_dir = Path(f"tmp/panel/{slug}")
        for p in panel_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, dict):
                suggested |= _extract_suggested_agents(data)
    # Resolve against registry
    registry_map = _list_registered_agents()
    resolved: set[str] = set()
    unknown: set[str] = set()
    for n in suggested:
        norm = _normalize_agent_id(n)
        real = registry_map.get(norm) or registry_map.get(norm.replace("-", ""))
        if real:
            resolved.add(real)
        else:
            unknown.add(n)
    print(f"timestamp={ts}")
    print("SUGGESTIONS RAW:", ", ".join(sorted(suggested)) if suggested else "<none>")
    print("RESOLVED:", ", ".join(sorted(resolved)) if resolved else "<none>")
    if unknown:
        print("UNKNOWN (not in registry):", ", ".join(sorted(unknown)))
    return 0


def _extract_text_blocks_from_result(item) -> List[str]:
    """Normalize Anthropic batch result item into a list of text blocks."""
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


def _normalize_agent_id(name: str) -> str:
    """Normalize free-form agent names to registry-style ids.

    Lowercase, remove punctuation, collapse whitespace to hyphens.
    """
    return _slugify(str(name))


def _list_registered_agents() -> Dict[str, str]:
    """Return a mapping of multiple normalized keys -> actual file stem for all registry agents.

    For each agent file stem, we add:
    - slug form (hyphens preserved)
    - hyphen-less form (for matching 'frontend' vs 'front-end')
    """
    mapping: Dict[str, str] = {}
    for base in AGENT_DIRS:
        try:
            for p in Path(base).glob("*.md"):
                stem = p.stem
                norm = _normalize_agent_id(stem)
                mapping.setdefault(norm, stem)
                # also index a hyphen-less variant for robust matching
                nohyphen = norm.replace("-", "")
                mapping.setdefault(nohyphen, stem)
        except Exception:
            continue
    return mapping


def _extract_first_json_object(s: str):
    """Return the first parseable JSON object found in the string, else None."""
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
    """Return JSON parsed from a ```json fenced block, or the raw block on parse failure."""
    import re
    m = re.search(r"```json\s*(.*?)```", s, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    block = m.group(1).strip()
    try:
        return json.loads(block)
    except Exception:
        return block


def _panel_user_instruction(feature: str, template_text: str | None) -> str:
    """Builds the user instruction for TASK001, embedding the fixed template.

    The function ignores template_text and reads templates/prp/draft-prp-001.json
    to comply with the mapping: draft-001 -> template 001.
    """
    # Always read the fixed TASK001 template from disk (do not modify the file)
    try:
        tpath = Path("templates/prp/draft-prp-001.json")
        tpl = tpath.read_text(encoding="utf-8") if tpath.exists() else None
    except Exception:
        tpl = None

    if tpl:
        return (
            "Task: Produce TASK001 (panel decomposition) strictly following the TARGET JSON TEMPLATE.\n\n"
            f"Feature Description:\n{feature}\n\n"
            "Rules:\n"
            "- STRICT TEMPLATE COMPLIANCE: do not add/remove keys; preserve order and structure\n"
            "- Single objective per task; ≤2 affected_components; ≤1 dependency (prefer 0)\n"
            "- Testable acceptance criteria (3–5); minimize cross-service coupling\n\n"
            "TARGET JSON TEMPLATE (copy structure exactly):\n"
            f"{tpl}\n\n"
            "Output: Return JSON only with this wrapper shape:\n"
            "{\n"
            "  \"outputs\": { \"draft_file\": \"<suggested-path>.json\" },\n"
            "  \"content\": <the filled JSON object matching the target template>\n"
            "}\n"
            "Do not include commentary outside JSON."
        )

    # Fallback if the template file is missing: keep prior schema to avoid breaking runs
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


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    # --arg is optional; if omitted we'll try to read from /prp/idea.md by default
    ap.add_argument("--arg", dest="feature_description", required=False, help="Feature description or a path to a file containing it", default="/prp/idea.md")
    ap.add_argument("--agents", default=",".join(CORE_PANEL), help="Comma-separated agent ids; defaults to core panel")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--template", default="templates/prp/draft-prp-001.json", help="Template for TASK001 (panel) output; used to guide exact JSON shape")
    ap.add_argument("--prompt", default="prompts/prp/draft-prp-001.md", help="Optional prompt file to include verbatim in the user instruction for TASK001")
    ap.add_argument("--max-passes", type=int, default=3, help="Maximum additional passes using newly suggested agents (default: 3; 0 to disable)")
    # Enabled by default; provide an explicit opt-out flag for convenience
    ap.add_argument("--include-agent-catalog", dest="include_agent_catalog", action="store_true", default=True, help="Include a JSON catalog of available agents (first N lines) in the system context (default: on)")
    ap.add_argument("--no-include-agent-catalog", dest="include_agent_catalog", action="store_false", help="Disable inclusion of the agent catalog in the system context")
    ap.add_argument("--agent-catalog-lines", type=int, default=7, help="Number of lines from each agent file to include in the catalog (default: 7)")
    # Testing utilities
    ap.add_argument("--dry-run-suggestions", action="store_true", help="Scan existing prp/drafts for delegation_suggestions and print a resolved/unknown summary without calling the API")
    ap.add_argument("--timestamp", help="Optional timestamp (YYYYMMDD-HHMMSS) to select drafts when using --dry-run-suggestions; if omitted, latest for slug is used")
    ap.add_argument("--scan-tmp-panel", action="store_true", help="Also scan tmp/panel/<slug> for panel JSON when using --dry-run-suggestions")
    return ap.parse_args()


def _load_feature_text(feature_arg: str) -> str:
    """Return feature text; if feature_arg points to a file, read it."""
    feature_path_candidates = [Path(feature_arg)] if feature_arg else []
    if feature_arg == "/prp/idea.md":
        feature_path_candidates.append(Path("prp/idea.md"))
    feature = feature_arg or ""
    for cand in feature_path_candidates:
        try:
            if cand.exists() and cand.is_file():
                feature = cand.read_text(encoding="utf-8", errors="replace").strip()
                break
        except Exception:
            pass
    return feature


def _build_requests(agent_ids: list[str], model: str, user_text: str, system_extras: list[str] | None = None) -> list[dict[str, Any]]:
    reqs: list[dict[str, Any]] = []
    extras = []
    if system_extras:
        # Convert extra texts into cached system blocks deterministically
        for txt in system_extras:
            if isinstance(txt, str) and txt.strip():
                extras.append({
                    "type": "text",
                    "text": txt,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                })
    for aid in sorted(agent_ids):
        try:
            system_text = load_agent_text(aid)
        except FileNotFoundError as e:
            print(f"WARN: skipping unknown agent '{aid}': {e}")
            continue
        system_blocks = [
            {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}}
        ] + extras
        reqs.append(
            {
                "custom_id": f"panel-{aid}",
                "params": {
                    "model": model,
                    "max_tokens": 2048,
                    "temperature": 0.2,
                    "system": system_blocks,
                    "messages": [
                        {"role": "user", "content": [{"type": "text", "text": user_text}]}
                    ],
                },
            }
        )
    return reqs


def _run_batch(client: Any, requests: list[dict[str, Any]], label: str = "batch") -> list[Any]:
    batch = client.messages.batches.create(requests=requests)
    print(f"{label}_id={batch.id} status={batch.processing_status}")
    while True:
        res = client.messages.batches.retrieve(batch.id)
        print(f"{label} poll: status={res.processing_status}")
        if res.processing_status in ("ended", "failed", "expired"):
            break
        time.sleep(2)
    items = list(client.messages.batches.results(batch.id))
    print(f"{label}_results_count={len(items)}")
    return items


def _process_batch_results(items: list[Any], slug: str, out_dir: Path) -> tuple[set[str], set[str]]:
    """Save results; return (suggested_agents, seen_agents)."""
    suggested: set[str] = set()
    seen_agents: set[str] = set()

    for item in items:
        blocks = _extract_text_blocks_from_result(item)
        if not blocks:
            print(item)
            continue
        text = "\n\n".join(blocks)
        data: Any = _extract_first_json_object(text) or _extract_fenced_json(text)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                pass
        if not isinstance(data, dict):
            print("WARN: non-JSON output, skipping save for one item")
            continue

        try:
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
        if agent_tag:
            seen_agents.add(agent_tag)

        outs = data.get("outputs") if isinstance(data.get("outputs"), dict) else None
        content = data.get("content") if isinstance(data.get("content"), dict) else None
        if outs and isinstance(outs.get("draft_file"), str) and content:
            suggested_path = outs.get("draft_file")
            batch_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            dest = (
                suggested_path.replace("{slug}", slug)
                .replace("{timestamp}", batch_ts)
                .replace("{variant}", "a")
                .replace("{prp_id}", "000")
            )
            base = Path(str(dest)).name or f"{slug}-task001.json"
            stem = base[:-5] if base.lower().endswith(".json") else base
            if batch_ts not in stem:
                stem = f"{stem}-{batch_ts}"
            if "task001" not in stem:
                stem = f"{stem}-task001"
            safe_agent = _slugify(agent_tag)
            if safe_agent and safe_agent not in stem:
                stem = f"{stem}-{safe_agent}"
            final = Path("prp/drafts") / f"{stem}.json"
            final.parent.mkdir(parents=True, exist_ok=True)
            Path(final).write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"saved -> {final}")
        else:
            path = out_dir / f"{agent_tag}.json"
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"saved -> {path}")

        # Robust extraction of delegation suggestions from multiple shapes
        suggested |= _extract_suggested_agents(data)
    return suggested, seen_agents


def _run_suggested_passes(
    client: Any,
    initial_suggested: set[str],
    seen_agents: set[str],
    base_agents: set[str],
    user_text: str,
    slug: str,
    out_dir: Path,
    model: str,
    max_passes: int,
    system_extras: list[str] | None = None,
) -> None:
    if max_passes <= 0:
        return
    print("\nSuggested agents (union):")
    print(", ".join(sorted(initial_suggested)))
    # Build registry of available agents and a normalizer map
    registry_map = _list_registered_agents()  # normalized -> actual
    already_run: set[str] = set(a.strip() for a in base_agents) | set(seen_agents)

    # Resolve initial suggestions against registry
    unknown: set[str] = set()
    def _resolve(names: set[str]) -> set[str]:
        resolved: set[str] = set()
        for n in names:
            norm = _normalize_agent_id(n)
            real = registry_map.get(norm)
            if not real:
                # try hyphen-less variant (e.g., frontend vs front-end)
                real = registry_map.get(norm.replace("-", ""))
            if real:
                resolved.add(real)
            else:
                unknown.add(n)
        return resolved

    to_query: set[str] = {a for a in _resolve(initial_suggested) if a not in already_run}
    if unknown:
        print(f"Ignoring unknown agents (not in registry): {', '.join(sorted(unknown))}")
    pass_num = 0
    while to_query and pass_num < max_passes:
        pass_num += 1
        print(f"\n=== Suggested agents pass {pass_num}/{max_passes}: {', '.join(sorted(to_query))} ===")
        reqs = _build_requests(sorted(to_query), model, user_text, system_extras=system_extras)
        if not reqs:
            print("No valid suggested agents to query in this pass.")
            break
        items = _run_batch(client, reqs, label=f"follow_batch_{pass_num}")
        newly_suggested, newly_seen = _process_batch_results(items, slug, out_dir)
        already_run |= newly_seen
        # Resolve new suggestions, accumulate unknowns, then filter by not already run
        new_resolved = _resolve(newly_suggested)
        if unknown:
            print(f"Ignoring unknown agents (not in registry): {', '.join(sorted(unknown))}")
        to_query = {a for a in new_resolved if a not in already_run}
    if pass_num:
        print(f"Completed {pass_num} suggested-agent pass(es).")


def main() -> int:
    """CLI entrypoint for TASK001 panel decomposition.

    Returns non-zero on configuration or API errors; 0 on success.
    """
    args = _parse_args()

    try:
        load_dotenv(find_dotenv(usecwd=True), override=False)
    except Exception:
        pass

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in environment or .env")
        return 2

    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    feature = _load_feature_text(args.feature_description)
    slug = _slugify(feature)

    # Test-first: optional dry-run mode to scan and resolve suggestions without hitting the API
    if args.dry_run_suggestions:
        return _dry_run_print_suggestions(slug=slug, ts=args.timestamp, scan_tmp_panel=bool(args.scan_tmp_panel))

    client = anthropic.Anthropic(api_key=api_key)

    # Read template (do not modify; only use to guide the model)
    tpath = Path(args.template)
    template_text = tpath.read_text(encoding="utf-8") if tpath.exists() else None
    # Read optional external prompt (verbatim)
    ppath = Path(args.prompt)
    prompt_text = ppath.read_text(encoding="utf-8", errors="replace") if ppath.exists() else None

    # Build one request per agent
    user_text = _panel_user_instruction(feature, template_text)
    if prompt_text:
        user_text = (
            "Task Prompt (verbatim, read fully):\n" + prompt_text.strip() + "\n\n" + user_text
        )
    # Optionally build a JSON agent catalog and attach as a separate cached system block
    system_extras: list[str] = []
    if args.include_agent_catalog:
        catalog = []
        for base in AGENT_DIRS:
            try:
                files = sorted(Path(base).glob("*.md"), key=lambda q: q.stem)
                for p in files:
                    stem = p.stem
                    text = p.read_text(encoding="utf-8", errors="replace").splitlines()
                    head = text[: max(0, int(args.agent_catalog_lines))]
                    catalog.append({"id": stem, "summary": "\n".join(head).strip()})
            except Exception:
                continue
        catalog = sorted(catalog, key=lambda x: x["id"]) 
        catalog_json = json.dumps({"available_agents": catalog}, indent=2, sort_keys=True, ensure_ascii=False)
        system_extras.append("KNOWN AGENTS CATALOG (JSON):\n" + catalog_json)
        # Add a concise reference note to the user instruction
        user_text += "\n\nIMPORTANT: A KNOWN AGENTS CATALOG is provided in system context. Choose suggestions ONLY from available_agents[].id"
    requests = _build_requests(agents, args.model, user_text, system_extras=system_extras)
    if not requests:
        print("No valid agents to query.")
        return 1

    results = _run_batch(client, requests, label="batch")

    out_dir = Path(f"tmp/panel/{slug}")
    out_dir.mkdir(parents=True, exist_ok=True)

    suggested, seen_agents = _process_batch_results(results, slug, out_dir)

    if suggested:
        _run_suggested_passes(
            client=client,
            initial_suggested=suggested,
            seen_agents=seen_agents,
            base_agents=set(agents),
            user_text=user_text,
            # carry through the same cached system extras for deterministic caching
            # Note: _run_suggested_passes will pass these when building requests
            slug=slug,
            out_dir=out_dir,
            model=args.model,
            max_passes=max(0, int(args.max_passes)),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

