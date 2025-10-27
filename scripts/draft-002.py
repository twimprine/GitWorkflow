#!/usr/bin/env python3
from __future__ import annotations
"""
draft-002.py — TASK002 steps runner

Purpose:
- Runs one or more PRP steps defined in a markdown file (prp-steps YAML in a fenced block).
- Enforces strict JSON wrapper for generate_from_template using the TASK002 template.

Inputs (CLI):
- --md: Path to markdown file containing prp-steps.
- --arg: Feature description used for $ARGUMENTS.
- --step/--steps/--all-steps: Which steps to run.
- --draft-ext: Output extension mode (json/md/mdx/preserve), defaults to json.
- --template: Path to TASK002 JSON template (enforced for generate_from_template).

Behavior:
- Parses prp-steps from markdown, builds Anthropic batch requests per selected step.
- Extracts and validates JSON wrapper for drafts; saves normalized outputs to prp/drafts.
- Non-wrapper but step-like outputs (e.g., atomicity) go to tmp/panel; invalid JSON to tmp/raw.

Outputs:
- prp/drafts/*-<timestamp>-<step_id>.json for wrapper-valid drafts (normalized path).
- tmp/panel/* for panel-style payloads; tmp/raw/* for diagnostics.
"""
import argparse
import json
import os
import time
from pathlib import Path
from datetime import datetime
import re
from typing import Any, Dict

from dotenv import load_dotenv, find_dotenv
import anthropic

# Standalone constants and helpers
MODEL_ID = "claude-sonnet-4-5"
AGENT_DIRS = [Path(os.path.expanduser("~/.claude/agents"))]
# Optional: support extra agent directories via env var
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


def _ensure_parent_dir(path_str: str) -> None:
    """Ensure parent directory of the path exists."""
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    """Make a filesystem-friendly slug from free text."""
    txt = text.lower().strip()
    txt = re.sub(r"[^a-z0-9\-\s]", "", txt)
    txt = re.sub(r"\s+", "-", txt)
    txt = re.sub(r"-+", "-", txt)
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
    """Minimal parser to extract steps from a markdown file containing a fenced yaml block.

    Expects a block like:
    ```yaml
    prp-steps:
      command: run
      args: { feature_description: "..." }
      agents: [a,b]
      steps:
        - id: create_draft
          agent: project-manager
          action: generate_from_template
          inputs: { template: templates/prp/draft-prp-001.json, feature: $ARGUMENTS }
          outputs: { draft_file: "{slug}-{timestamp}-{id}.json" }
    ```
    """
    import yaml
    text = Path(path).read_text(encoding="utf-8")
    # find first fenced yaml block
    import re as _re
    m = _re.search(r"```yaml\s*(.*?)```", text, _re.DOTALL | _re.IGNORECASE)
    if not m:
        raise SpecError("No yaml block found in markdown")
    data = yaml.safe_load(m.group(1))
    root = data.get("prp-steps") if isinstance(data, dict) else None
    if not isinstance(root, dict):
        raise SpecError("Missing prp-steps root")
    steps = root.get("steps") or []
    out = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        out.append(Step(
            id=str(s.get("id")),
            agent=str(s.get("agent")),
            action=str(s.get("action")),
            inputs=s.get("inputs") or {},
            outputs=s.get("outputs") or {},
        ))
    class Spec:
        def __init__(self, steps):
            self.steps = steps
    return Spec(out)


def _resolve_value(val: Any, runtime_args: Dict[str, str]) -> Any:
    """Resolve special placeholders from runtime arguments."""
    if not isinstance(val, str):
        return val
    if val == "$ARGUMENTS" or val == "$ARGUMENTS/feature_description":
        return runtime_args.get("feature_description")
    return val


def _resolve_mapping(d: Dict[str, Any], runtime_args: Dict[str, str]) -> Dict[str, Any]:
    """Apply _resolve_value across a mapping."""
    return {k: _resolve_value(v, runtime_args) for k, v in d.items()}


def build_user_instruction_for_step(step: Step, resolved_inputs: Dict[str, Any]) -> str:
    """Construct the user prompt for the given step and resolved inputs.

    - For generate_from_template: embeds the TASK002 JSON template text.
    - For run_script: includes the file content for analysis.
    """
    if step.action == "generate_from_template":
        template_path = str(resolved_inputs.get("template", ""))
        feature_desc = str(resolved_inputs.get("feature", ""))
        prefix = str(resolved_inputs.get("_prompt_text", "")).strip()
        t = Path(template_path).read_text(encoding="utf-8") if Path(template_path).exists() else ""
        if template_path.lower().endswith(".json"):
            core = (
                "Task: STRICT TEMPLATE COMPLIANCE — Fill the provided JSON template EXACTLY.\n\n"
                "Rules:\n"
                "- Do not add or remove keys\n"
                "- Preserve key order and nested structure\n"
                "- Replace only placeholder/example values\n"
                "- Keep the PRP atomic (single objective, ≤2 affected components)\n\n"
                f"Feature Description:\n{feature_desc}\n\n"
                f"JSON Template (copy structure exactly):\n{t}\n\n"
                "Output: Return JSON only with this shape:\n"
                "{\n"
                "  \"outputs\": { \"draft_file\": \"<suggested-path>.json\" },\n"
                "  \"content\": <the filled JSON object>\n"
                "}\n"
                "Do not wrap the content object as a string. Do not include commentary outside JSON."
            )
            return (("Task Prompt (verbatim, read fully):\n" + prefix + "\n\n") if prefix else "") + core
        else:
            core = (
                "Task: STRICT TEMPLATE COMPLIANCE — Generate a DRAFT PRP by COPYING the provided template’s headings and section order EXACTLY.\n\n"
                f"Feature Description: \n{feature_desc}\n\n"
                f"Template Content (copy structure exactly):\n{t}\n\n"
                "Output: Return JSON only:\n"
                "{\n"
                "  \"outputs\": { \"draft_file\": \"<suggested-path>.md\" },\n"
                "  \"content\": \"<the generated markdown content>\"\n"
                "}\n"
            )
            return (("Task Prompt (verbatim, read fully):\n" + prefix + "\n\n") if prefix else "") + core
    if step.action == "run_script":
        file_path = str(resolved_inputs.get("file", ""))
        file_text = Path(file_path).read_text(encoding="utf-8") if Path(file_path).exists() else ""
        return (
            "Task: Analyze the provided markdown draft for size and splitting recommendations.\n\n"
            f"Draft Path: {file_path}\n"
            f"Draft Content:\n{file_text}\n\n"
            "Compute:\n- Total character count (include markdown, code, whitespace)\n"
            "- If <= 5000: status = under_limit\n"
            "- If > 5000: status = over_limit, estimate number of atomic PRPs and propose split points\n\n"
            "Output: Return JSON only with keys:\n"
            "{\n"
            '  "report": {\n'
            '    "total_chars": <int>,\n'
            '    "status": "under_limit" | "over_limit",\n'
            '    "estimated_prps": <int>,\n'
            '    "suggested_splits": ["<section or boundary>"],\n'
            '    "notes": "<brief>"\n'
            "  }\n"
            "}\n"
        )
    return f"Unsupported action '{step.action}'. Provide no output."


def _extract_text_blocks_from_result(item) -> list[str]:
    """Normalize Anthropic batch result item into a list of text blocks."""
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
    try:
        result = getattr(item, "result", None)
        message = getattr(result, "message", None)
        content = getattr(message, "content", [])
        blocks: list[str] = []
        for c in content:
            if hasattr(c, "type") and getattr(c, "type") == "text":
                blocks.append(getattr(c, "text", ""))
            elif isinstance(c, dict) and c.get("type") == "text":
                blocks.append(c.get("text", ""))
        return blocks
    except Exception:
        return []


def _get_custom_id(item) -> str | None:
    """Extract custom_id from batch item, if present."""
    try:
        cid = getattr(item, "custom_id", None)
        if cid:
            return cid
    except Exception:
        pass
    if isinstance(item, str):
        try:
            obj = json.loads(item)
            return obj.get("custom_id")
        except Exception:
            return None
    return None


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
    """Normalize suggested draft path into prp/drafts with timestamp and step id.

    ext_mode controls extension behavior; when json, ensures .json extension and removes any .json in stem.
    """
    base = Path(str(suggested)).name.strip()
    if not base:
        base = slug
    if base.startswith(".") and base.count(".") == 1:
        stem, right_ext = base, ""
    else:
        stem = base.rsplit(".", 1)[0] if "." in base else base
        right_ext = "." + base.rsplit(".", 1)[1] if "." in base else ""
    if ext_mode == "preserve" and right_ext:
        final_ext = right_ext
    elif ext_mode == "mdx":
        final_ext = ".mdx"
    elif ext_mode == "json":
        final_ext = ".json"
    else:
        final_ext = ".md"
    if ext_mode not in ("preserve", "json"):
        try:
            stem = re.sub(r"\.json\b", "", stem, flags=re.IGNORECASE)
        except Exception:
            stem = stem.replace(".json", "")
    has_ts = ts in stem or bool(re.search(r"\b\d{8}-\d{6}\b", stem))
    has_step = step_id in stem
    new_stem = stem
    if not has_ts:
        new_stem = f"{new_stem}-{ts}"
    if not has_step:
        new_stem = f"{new_stem}-{step_id}"
    final_name = f"{new_stem}{final_ext}"
    return str(Path("prp/drafts") / final_name)


def main() -> int:
    """CLI entrypoint for TASK002 steps executor.

    Returns non-zero on configuration or API errors; 0 on success.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="tmp/draft.md", help="Markdown file with prp-steps")
    ap.add_argument("--arg", dest="feature_description", required=True)
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--step", default="create_draft")
    ap.add_argument("--steps", nargs="+")
    ap.add_argument("--all-steps", action="store_true")
    ap.add_argument("--draft-ext", choices=["md", "mdx", "json", "preserve"], default="json")
    ap.add_argument("--template", default="templates/prp/draft-prp-002.json", help="Template for TASK002 output; enforced for generate_from_template")
    ap.add_argument("--prompt", default="prompts/prp/draft-prp-002.md", help="Optional prompt file to include verbatim in the user instruction for TASK002")
    args = ap.parse_args()

    try:
        load_dotenv(find_dotenv(usecwd=True), override=False)
    except Exception:
        pass

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in environment or .env")
        return 2

    # Parse spec
    try:
        spec = parse_prp_steps(args.md)
    except SpecError as e:
        print(f"SpecError: {e}")
        return 1

    # Determine steps
    available_ids = [s.id for s in spec.steps]
    if args.all_steps:
        selected_ids = available_ids
    elif args.steps:
        selected_ids = args.steps
    else:
        selected_ids = [args.step]
    missing = [sid for sid in selected_ids if sid not in available_ids]
    if missing:
        print(f"Unknown step ids: {missing}. Available: {available_ids}")
        return 2

    runtime_args = {"feature_description": args.feature_description}
    # Optional external prompt to prepend
    _prompt_text = Path(args.prompt).read_text(encoding="utf-8", errors="replace") if Path(args.prompt).exists() else ""
    requests = []
    batch_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    for sid in selected_ids:
        step = next(s for s in spec.steps if s.id == sid)
        agent_text = load_agent_text(step.agent)
        resolved_inputs = _resolve_mapping(step.inputs, runtime_args)
        if _prompt_text:
            resolved_inputs["_prompt_text"] = _prompt_text
        # Enforce TASK002 template mapping regardless of spec
        if step.action == "generate_from_template":
            resolved_inputs["template"] = args.template
        user_text = build_user_instruction_for_step(step, resolved_inputs)
        req = {
            "custom_id": f"step-{sid}",
            "params": {
                "model": args.model,
                "max_tokens": int(args.max_tokens),
                "temperature": 0.2,
                "system": [
                    {"type": "text", "text": agent_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}}
                ],
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": user_text}]}
                ],
            },
        }
        requests.append(req)

    client = anthropic.Anthropic(api_key=api_key)
    batch = client.messages.batches.create(requests=requests)
    print(f"batch_id={batch.id} status={batch.processing_status} count={len(requests)}")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        print(f"poll: status={b.processing_status}")
        if b.processing_status in ("ended", "failed", "expired"):
            break
        time.sleep(2)
    items = list(client.messages.batches.results(batch.id))
    print(f"results_count={len(items)}")
    if not items:
        print("No results returned.")
        return 3

    seen = set()
    for it in items:
        blocks = _extract_text_blocks_from_result(it)
        cid = _get_custom_id(it)
        step_id = cid.replace("step-", "") if cid else "unknown-step"
        seen.add(step_id)
        if not blocks:
            print(f"WARN: no text blocks for {cid or 'unknown'}; raw=\n{it}")
            continue
        combined = "\n\n".join(blocks)
        payload = _extract_first_json_object(combined) or _extract_fenced_json(combined)
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                pass
        feature = args.feature_description
        slug = _slugify(feature)
        if not isinstance(payload, dict):
            raw_out = f"tmp/raw/{slug}-{step_id}-{batch_ts}.txt"
            _ensure_parent_dir(raw_out)
            Path(raw_out).write_text(combined, encoding="utf-8")
            print(f"Saved raw -> {raw_out}")
            continue

        def _is_valid(obj: dict) -> bool:
            outs = obj.get("outputs")
            content = obj.get("content")
            return isinstance(outs, dict) and isinstance(outs.get("draft_file"), str) and isinstance(content, dict)

        if _is_valid(payload) and args.draft_ext == "json":
            outputs = payload.get("outputs", {})
            dest = None
            if isinstance(outputs, dict) and isinstance(outputs.get("draft_file"), str):
                dest = outputs["draft_file"].replace("{slug}", slug).replace("{timestamp}", batch_ts).replace("{variant}", "a").replace("{prp_id}", "000")
            if not dest:
                dest = f"{slug}-{step_id}-{batch_ts}.json"
            dest = _normalize_draft_path(dest, slug, step_id, batch_ts, args.draft_ext)
            _ensure_parent_dir(dest)
            Path(dest).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"Saved draft -> {dest}")
            continue

        if isinstance(payload, dict) and ("proposed_tasks" in payload or "atomicity" in payload):
            out_path = f"tmp/panel/{slug}-{step_id}-{batch_ts}.json"
            _ensure_parent_dir(out_path)
            Path(out_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"Saved panel tasks -> {out_path}")
            continue

        if isinstance(payload, dict):
            raw_out = f"tmp/raw/{slug}-{step_id}-{batch_ts}-invalid.json"
            _ensure_parent_dir(raw_out)
            Path(raw_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"WARN: invalid JSON payload for {step_id}. Saved diagnostics -> {raw_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

