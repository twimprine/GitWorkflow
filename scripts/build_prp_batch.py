#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from parse_prp_steps import parse_prp_steps, SpecError, CommandSpec, StepSpec

AGENT_DIRS = [
    Path(os.path.expanduser("~/.claude/agents")),  # primary location
    Path("tmp/agents"),  # optional repo fallback if you add any later
]

MODEL_ID = "claude-sonnet-4-5"

# Match: $steps.<stepId>.outputs.<key>
VAR_REF_RE = re.compile(r"^\$steps\.(?P<sid>[A-Za-z0-9_\-]+)\.outputs\.(?P<key>[A-Za-z0-9_\-]+)$")

def load_agent_text(name: str) -> str:
    fname = f"{name}.md"
    for base in AGENT_DIRS:
        p = base / fname
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
    raise FileNotFoundError(f"Agent file not found for '{name}' in: {', '.join(str(d) for d in AGENT_DIRS)}")

def resolve_value(val: Any, runtime_args: Dict[str, str], prior_outputs: Dict[str, Dict[str, str]]) -> Any:
    # Scalars only for now; extend to lists/dicts if needed
    if not isinstance(val, str):
        return val
    if val == "$ARGUMENTS":
        # If only one arg name, use that
        if len(runtime_args) == 1:
            return list(runtime_args.values())[0]
        # Or pass as JSON string
        return json.dumps(runtime_args)

    m = VAR_REF_RE.match(val)
    if m:
        sid = m.group("sid")
        key = m.group("key")
        if sid not in prior_outputs or key not in prior_outputs[sid]:
            # Leave unresolved reference as-is; orchestrator will fill after execution
            return val
        return prior_outputs[sid][key]
    return val

def resolve_mapping(d: Dict[str, Any], runtime_args: Dict[str, str], prior_outputs: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        out[k] = resolve_value(v, runtime_args, prior_outputs)
    return out

def read_text_if_exists(path_str: str) -> Optional[str]:
    p = Path(path_str)
    if p.exists():
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None
    return None

def build_user_instruction_for_step(step: StepSpec, resolved_inputs: Dict[str, Any]) -> str:
    if step.action == "generate_from_template":
        template_path = str(resolved_inputs.get("template", ""))
        feature_desc = str(resolved_inputs.get("feature", ""))
        template_text = read_text_if_exists(template_path) 
        # Behavior depends on template extension
        if template_path.lower().endswith(".json"):
            return (
                "Task: STRICT TEMPLATE COMPLIANCE — Fill the provided JSON template EXACTLY.\n\n"
                "Rules:\n"
                "- Do not add or remove keys\n"
                "- Preserve key order and nested structure\n"
                "- Replace only placeholder/example values with content derived from the feature description\n"
                "- Keep the PRP atomic (single objective, ≤2 affected components)\n\n"
                f"Feature Description:\n{feature_desc}\n\n"
                f"JSON Template (copy structure exactly, replacing placeholder values only):\n{template_text}\n\n"
                "Output: Return JSON only with this shape:\n"
                "{\n"
                "  \"outputs\": { \"draft_file\": \"<suggested-path>.json\" },\n"
                "  \"content\": <the filled JSON object>\n"
                "}\n"
                "Do not wrap the content object as a string. Do not include commentary outside JSON."
            )
        else:
            return (
                "Task: STRICT TEMPLATE COMPLIANCE — Generate a DRAFT PRP by COPYING the provided template’s headings and section order EXACTLY. Do not add/remove sections. Fill placeholders and bullet items only.\n\n"
                "Rules:\n"
                "\n"
                "Preserve every heading verbatim and in the same order\n"
                "Do not add “intros” or commentary\n"
                "Replace bracketed placeholders and fill bullets concisely\n"
                "Keep the PRP atomic (single objective, ≤2 affected components)\n"
                f"Feature Description: \n{feature_desc}\n\n"
                f"Template Content (copy structure exactly):\n{template_text}\n\n"
                "Validation:\n"
                "\n"
                "The output content MUST begin with the same first 5 heading lines from the template\n"
                "If you cannot follow these rules, return an error with reason and do not proceed\n"
                "Output: Return JSON only:\n"
                "{\n"
                "  \"outputs\": { \"draft_file\": \"<suggested-path>.md\" },\n"
                "  \"content\": \"<the generated markdown content>\"\n"
                "}\n"
                "Do not include commentary outside JSON."
            )

    if step.action == "run_script":
        # Batch-only: simulate the analysis by reading the file and reporting counts and suggestions.
        file_path = str(resolved_inputs.get("file", ""))
        file_text = read_text_if_exists(file_path) or ""
        return (
            "Task: Analyze the provided markdown draft for size and splitting recommendations.\n\n"
            f"Draft Path: {file_path}\n"
            f"Draft Content:\n{file_text}\n\n"
            "Compute:\n- Total character count (include markdown, code, whitespace)\n"
            "- If <= 5000: status = under_limit\n"
            "- If > 5000: status = over_limit, estimate number of atomic PRPs and propose split points\n\n"
            "Output: Return JSON only with keys:\n"
            "{\n"
            '  \"report\": {\n'
            '    \"total_chars\": <int>,\n'
            '    \"status\": \"under_limit\" | \"over_limit\",\n'
            '    \"estimated_prps\": <int>,\n'
            '    \"suggested_splits\": [\"<section or boundary>\"],\n'
            '    \"notes\": \"<brief>\"\n'
            "  }\n"
            "}\n"
            "Do not include commentary outside JSON."
        )

    # Unknown action guard (should be validated earlier)
    return f"Unsupported action '{step.action}'. Provide no output."

def build_requests(spec: CommandSpec, runtime_args: Dict[str, str], model: str = MODEL_ID) -> List[Dict[str, Any]]:
    requests: List[Dict[str, Any]] = []
    prior_outputs: Dict[str, Dict[str, str]] = {}

    for step in spec.steps:
        # Load agent system text (cached system content)
        agent_text = load_agent_text(step.agent)

        # Resolve inputs using runtime args and prior step outputs
        resolved_inputs = resolve_mapping(step.inputs, runtime_args, prior_outputs)

        # Build user instruction content based on action
        user_text = build_user_instruction_for_step(step, resolved_inputs)

        req = {
            "custom_id": f"{spec.command}-{step.id}",
            "params": {
                "model": model,
                "max_tokens": 2048,
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
        requests.append(req)

        # We don't compute outputs here—those come from model JSON; this just builds requests.
        # Orchestrator will parse outputs and populate prior_outputs when we run the batch.
    return requests

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="tmp/draft.md", help="Markdown file with prp-steps")
    ap.add_argument("--arg", dest="feature_description", default="Add user profile management with avatar upload")
    ap.add_argument("--model", default=MODEL_ID)
    args = ap.parse_args()

    try:
        spec = parse_prp_steps(args.md)
    except SpecError as e:
        print(f"SpecError: {e}")
        return 1

    runtime_args = {"feature_description": args.feature_description}
    reqs = build_requests(spec, runtime_args, model=args.model)
    print(json.dumps({"requests": reqs}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())