#!/usr/bin/env python3
from __future__ import annotations
"""
draft-002.py — TASK002 runner

Purpose:
- Primary mode (qa): Read TASK001 drafts, extract all questions, ask the architect, and produce a TASK002 answer per question using the strict template 002.
- Legacy mode (steps): Runs prp-steps from a markdown file for backwards compatibility.

Inputs (CLI):
- --mode: qa | steps (default: qa)
- In qa mode:
    - --architect-agent: Which agent answers (default: application-architect)
    - --template: Path to TASK002 JSON template (content shape only; wrapper is enforced by the script)
    - --include-repo-context/--no-include-repo-context
    - --context-schema, --context-max-files
    - --include-agent-catalog/--no-include-agent-catalog, --agent-catalog-lines
    - --model, --max-tokens
- In steps mode:
    - --md: Path to markdown file containing prp-steps.
    - --arg: Feature description used for $ARGUMENTS.
    - --template: Path to TASK002 JSON template (enforced for generate_from_template).

Behavior:
- qa: Builds a deterministic batch to the architect with identical cached system blocks for all requests. Embeds repo context (from docs/schema.json) and aggregated TASK001 responses into system extras. Each question yields one response.
- steps: Parses prp-steps and runs as before.

Outputs:
- qa: prp/drafts/P-###-T-002-Q-###.json using shared PRP sequence counters (P first, then T, then Q).
- steps: prp/drafts/*-<timestamp>-<step_id>.json for wrapper-valid drafts (normalized path); tmp/panel/* and tmp/raw/* as before.
"""
import argparse
import json
import os
import time
from pathlib import Path
from datetime import datetime
import re
import glob
import fnmatch
from typing import Any, Dict, List, Tuple

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


# --- PRP Sequence Register (shared with TASK001) ---
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


def _next_Q(task: str = "002") -> int:
    data = _read_seq()
    q = data.get("Q") or {}
    curr = int((q.get(task) or 0)) + 1
    q[task] = curr
    data["Q"] = q
    _write_seq(data)
    return curr


def _load_repo_context_from_schema(
    schema_path: Path,
    workspace_root: Path,
    *,
    max_files: int | None = None,
) -> Tuple[str, str] | None:
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


def _collect_task001_data() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (responses, questions) from TASK001 drafts in prp/drafts.

    Supports both new naming (P-*-T-001.json) and legacy timestamped names (*task001*.json).

    responses: [{"file": str, "content": dict}]
    questions: [{"question": str, "agent": str, "source_file": str}]
    """
    draft_dir = Path("prp/drafts")
    seen_paths: set[str] = set()
    drafts: List[Path] = []
    # New naming (supports both P-###-T-001.json and P-###-T-001-{agent}.json)
    for p in sorted(draft_dir.glob("P-*-T-001*.json"), key=lambda q: str(q)):
        sp = str(p)
        if sp not in seen_paths:
            seen_paths.add(sp)
            drafts.append(p)
    # Legacy naming that includes task001 in the filename
    for p in sorted(draft_dir.glob("*task001*.json"), key=lambda q: str(q)):
        sp = str(p)
        if sp not in seen_paths:
            seen_paths.add(sp)
            drafts.append(p)
    responses: List[Dict[str, Any]] = []
    questions: List[Dict[str, Any]] = []
    for p in drafts:
        try:
            root = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(root, dict):
            continue
        content = root.get("content") if isinstance(root.get("content"), dict) else None
        if not isinstance(content, dict):
            continue
        # Heuristic: consider only TASK001-like content shapes
        is_task001_shape = (
            ("atomicity" in content or "proposed_tasks" in content) and
            (isinstance(content.get("Questions"), list) or isinstance(content.get("questions"), list))
        )
        if not is_task001_shape:
            continue
        responses.append({"file": p.name, "content": content})
        qlist = None
        # Support both canonical and lowercase field names
        if isinstance(content.get("Questions"), list):
            qlist = content.get("Questions")
        elif isinstance(content.get("questions"), list):
            qlist = content.get("questions")
        if isinstance(qlist, list):
            for q in qlist:
                if isinstance(q, dict) and isinstance(q.get("question"), str):
                    questions.append({
                        "question": q.get("question"),
                        "agent": (q.get("agent") if isinstance(q.get("agent"), str) else ""),
                        "source_file": p.name,
                    })
    # Deterministic order across runs
    questions.sort(key=lambda d: (d.get("agent") or "", d.get("question") or "", d.get("source_file") or ""))
    responses.sort(key=lambda d: d.get("file") or "")
    return responses, questions


def _dedup_questions_via_model(client: Any, model: str, max_tokens: int, questions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Ask the model to deduplicate questions. Returns (dedup_list, raw_payload).

    Input questions are a list of {question, agent, source_file}. The model should group semantic duplicates and
    return JSON with the following shape:
    {
      "questions": [
        {"question": str, "agents": [str], "source_files": [str]}
      ]
    }
    """
    # Build deterministic user instruction with input JSON
    src = sorted([
        {
            "question": (q.get("question") or "").strip(),
            "agent": (q.get("agent") or "").strip(),
            "source_file": (q.get("source_file") or "").strip(),
        }
    for q in questions
    if isinstance(q, dict) and isinstance(q.get("question"), str) and (q.get("question") or "").strip()
    ], key=lambda d: (d["question"], d["agent"], d["source_file"]))

    input_json = json.dumps({"questions": src}, indent=2, sort_keys=True, ensure_ascii=False)
    user_text = (
        "Task: Deduplicate semantically equivalent questions.\n\n"
        "Instructions:\n"
        "- Normalize whitespace and punctuation; treat questions with the same meaning as duplicates.\n"
        "- Produce a canonical phrasing for each group.\n"
        "- Aggregate all agents and source_files that raised the duplicate question.\n\n"
        "Input JSON:\n" + input_json + "\n\n"
        "Output JSON schema (return JSON only):\n"
        "{\n"
        "  \"questions\": [\n"
        "    { \"question\": \"...\", \"agents\": [\"...\"], \"source_files\": [\"...\"] }\n"
        "  ]\n"
        "}\n"
    )

    # Use default system (standard model behavior)
    req = {
        "custom_id": "dedup-questions",
        "params": {
            "model": model,
            "max_tokens": int(max_tokens),
            "temperature": 0.2,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_text}]}
            ],
        },
    }

    batch = client.messages.batches.create(requests=[req])
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status in ("ended", "failed", "expired"):
            break
        time.sleep(1)
    items = list(client.messages.batches.results(batch.id))
    if not items:
        return [], {}
    blocks = _extract_text_blocks_from_result(items[0])
    combined = "\n\n".join(blocks) if blocks else ""
    # Save raw for diagnostics
    try:
        raw_path = Path("tmp/raw/dedup-questions.txt")
        _ensure_parent_dir(str(raw_path))
        raw_path.write_text(combined or "", encoding="utf-8")
    except Exception:
        pass
    payload = _extract_first_json_object(combined) or _extract_fenced_json(combined)
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    # Normalize various shapes into a list of entries
    def _normalize_list(lst: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not isinstance(lst, list):
            return out
        for e in lst:
            if isinstance(e, str):
                q = e.strip()
                if q:
                    out.append({"question": q, "agents": [], "source_files": []})
            elif isinstance(e, dict):
                q = (e.get("question") or "").strip()
                if not q:
                    # Some models may use a different key like 'q'
                    q = (e.get("q") or "").strip()
                if q:
                    agents = [a.strip() for a in (e.get("agents") or []) if isinstance(a, str) and a.strip()]
                    srcs = [s.strip() for s in (e.get("source_files") or []) if isinstance(s, str) and s.strip()]
                    out.append({"question": q, "agents": sorted(set(agents)), "source_files": sorted(set(srcs))})
        return out

    dedup: List[Dict[str, Any]] = []
    if isinstance(payload, dict):
        out_list = payload.get("questions")
        dedup = _normalize_list(out_list)
    elif isinstance(payload, list):
        dedup = _normalize_list(payload)
    else:
        dedup = []
    diag: Dict[str, Any] = {}
    if isinstance(payload, dict):
        diag = payload
    elif isinstance(payload, list):
        diag = {"list_payload": payload}
    return dedup, diag


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


def _build_task002_user_instruction(template_path: str, architect: str, question_text: str, q_id: int) -> str:
        """Build the user prompt for TASK002 QA per question, embedding the template JSON.

        Enforces a strict wrapper:
        {
            "outputs": { "draft_file": "<suggested>.json" },
            "content": { ...filled template 002... }
        }
        """
        t = Path(template_path).read_text(encoding="utf-8") if Path(template_path).exists() else ""
        qid_str = f"T-002-Q-{q_id:03d}"
        example = (
            '{\n'
            '  "outputs": { "draft_file": "P-XXX-T-002-Q-YYY.json" },\n'
            '  "content": {\n'
            f'    "agent_name": "{architect}",\n'
            f'    "id": "{qid_str}",\n'
            f'    "question": {json.dumps(question_text)},\n'
            '    "answer": "...",\n'
            '    "citation": ["..."]\n'
            '  }\n'
            '}'
        )
        return (
            "Task: STRICT TEMPLATE COMPLIANCE — Answer the question using TASK002 template EXACTLY.\n\n"
            "Rules:\n"
            "- Return JSON only, no prose\n"
            "- Do not add or remove keys\n"
            "- Preserve key order and structure\n"
            "- Replace only placeholder/example values\n"
            "- Copy the question text exactly into content.question\n"
            "- Include citations to repo_context paths or entries in TASK001 RESPONSES\n\n"
            f"Question:\n{question_text}\n\n"
            f"Constraints:\n- agent_name MUST be '{architect}'\n- id MUST be '{qid_str}'\n\n"
            f"JSON Template (copy structure exactly):\n{t}\n\n"
            "Output wrapper (start your response with '{\"outputs\"'):\n"
            f"{example}\n"
        )


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
    """CLI entrypoint for TASK002.

    Returns non-zero on configuration or API errors; 0 on success.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["qa", "steps"], default="qa")
    # qa mode
    ap.add_argument("--architect-agent", default="application-architect")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--template", default="templates/prp/draft-prp-002.json", help="Template for TASK002 content shape (wrapper enforced by script)")
    ap.add_argument("--include-repo-context", dest="include_repo_context", action="store_true", default=True)
    ap.add_argument("--no-include-repo-context", dest="include_repo_context", action="store_false")
    ap.add_argument("--context-schema", default="docs/schema.json")
    ap.add_argument("--context-max-files", type=int, default=0)
    ap.add_argument("--include-agent-catalog", dest="include_agent_catalog", action="store_true", default=True)
    ap.add_argument("--no-include-agent-catalog", dest="include_agent_catalog", action="store_false")
    ap.add_argument("--agent-catalog-lines", type=int, default=7)
    ap.add_argument("--limit-questions", type=int, default=0, help="If >0, process at most this many questions (deterministic order)")
    ap.add_argument("--filter-agent", default="", help="If set, include only questions where agent equals this (case-insensitive match)")
    ap.add_argument("--filter-contains", default="", help="If set, include only questions whose text contains this substring (case-insensitive)")
    ap.add_argument("--dedup-max-tokens", type=int, default=2048, help="Max tokens for the dedup model pass (default 2048)")
    # steps mode
    ap.add_argument("--md", default="prompts/prp/draft-prp-002.md", help="Markdown file with prp-steps (steps mode)")
    ap.add_argument("--arg", dest="feature_description", required=False, help="$ARGUMENTS value for steps mode")
    ap.add_argument("--prompt", default="prompts/prp/draft-prp-002.md", help="Optional prompt file (steps mode)")
    args = ap.parse_args()

    try:
        load_dotenv(find_dotenv(usecwd=True), override=False)
    except Exception:
        pass

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in environment or .env")
        return 2

    client = anthropic.Anthropic(api_key=api_key)

    if args.mode == "qa":
        # Build shared system extras once for caching determinism
        system_extras: List[dict] = []
        # Architect system prompt
        try:
            architect_text = load_agent_text(args.architect_agent)
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            return 2
        system_extras.append({"type": "text", "text": architect_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}})

        # Optional agent catalog (deterministic)
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
            system_extras.append({"type": "text", "text": "KNOWN AGENTS CATALOG (JSON):\n" + catalog_json, "cache_control": {"type": "ephemeral", "ttl": "1h"}})

        # Repo context
        if args.include_repo_context:
            ctx = _load_repo_context_from_schema(
                schema_path=Path(args.context_schema),
                workspace_root=Path.cwd(),
                max_files=(args.context_max_files if args.context_max_files > 0 else None),
            )
            if ctx:
                context_json, _ttl = ctx
                system_extras.append({"type": "text", "text": "REPO CONTEXT INDEX (JSON):\n" + context_json, "cache_control": {"type": "ephemeral", "ttl": "1h"}})

        # Aggregate TASK001 responses and questions
        responses, questions = _collect_task001_data()
        # Optional filtering
        filt_agent = (args.filter_agent or "").strip().lower()
        filt_sub = (args.filter_contains or "").strip().lower()
        if filt_agent or filt_sub:
            qf = []
            for q in questions:
                agent = (q.get("agent") or "").strip().lower()
                text = (q.get("question") or "").strip().lower()
                if filt_agent and agent != filt_agent:
                    continue
                if filt_sub and filt_sub not in text:
                    continue
                qf.append(q)
            questions = qf
        # Optional limit
        if isinstance(args.limit_questions, int) and args.limit_questions > 0:
            questions = questions[: args.limit_questions]

        if not questions:
            print("No questions found from TASK001 drafts.")
            return 0
        print(f"Selected questions before dedup: {len(questions)}")

        # Dedup questions via a simple model pass (no special system context)
        dedup_list, dedup_payload = _dedup_questions_via_model(
            client=client, model=args.model, max_tokens=args.dedup_max_tokens, questions=questions
        )
        # Local fallback dedup if model returns empty
        if not dedup_list:
            seen = {}
            import re as _re
            def _norm(s: str) -> str:
                s = (s or "").strip().lower()
                s = _re.sub(r"\s+", " ", s)
                s = _re.sub(r"[\.?!,;:]+$", "", s)
                return s
            for q in questions:
                qt = _norm(q.get("question") or "")
                if not qt:
                    continue
                entry = seen.setdefault(qt, {"question": q.get("question") or "", "agents": set(), "source_files": set()})
                a = (q.get("agent") or "").strip()
                if a:
                    entry["agents"].add(a)
                s = (q.get("source_file") or "").strip()
                if s:
                    entry["source_files"].add(s)
            dedup_list = [
                {"question": v["question"], "agents": sorted(v["agents"]), "source_files": sorted(v["source_files"]) }
                for v in seen.values()
            ]
        # Save single dedup file under prp/drafts with next P and marker T-002-DEDUPE
        P_d = _next_P()
        dedup_path = Path("prp/drafts") / f"P-{P_d:03d}-T-002-DEDUPE.json"
        dedup_path.parent.mkdir(parents=True, exist_ok=True)
        to_save = {"outputs": {"draft_file": str(dedup_path)}, "content": {"questions": dedup_list}, "diagnostics": dedup_payload if isinstance(dedup_payload, dict) else {}}
        dedup_path.write_text(json.dumps(to_save, indent=2), encoding="utf-8")
        print(f"Saved dedup questions -> {dedup_path}")
        # Use dedupbed list for QA
        questions = [{"question": e.get("question"), "agent": ",".join(e.get("agents", [])), "source_file": ",".join(e.get("source_files", []))} for e in dedup_list]
        print(f"Questions after dedup: {len(questions)}")
        prp_json = json.dumps({"task001_responses": responses}, indent=2, sort_keys=True, ensure_ascii=False)
        system_extras.append({"type": "text", "text": "TASK001 RESPONSES (JSON):\n" + prp_json, "cache_control": {"type": "ephemeral", "ttl": "1h"}})

        # Build requests, one per question, with identical system blocks across all
        tpl_path = args.template
        requests = []
        cid_to_q: Dict[str, int] = {}
        for q_item in questions:
            qn = str(q_item.get("question") or "").strip()
            if not qn:
                continue
            Qnum = _next_Q("002")
            qid_str = f"T-002-Q-{Qnum:03d}"
            user_text = _build_task002_user_instruction(tpl_path, args.architect_agent, qn, Qnum)
            req = {
                "custom_id": f"qa-Q-{Qnum:03d}",
                "params": {
                    "model": args.model,
                    "max_tokens": int(args.max_tokens),
                    "temperature": 0.2,
                    "system": system_extras,
                    "messages": [
                        {"role": "user", "content": [{"type": "text", "text": user_text}]}
                    ],
                },
            }
            cid_to_q[req["custom_id"]] = Qnum
            requests.append(req)

        if not requests:
            print("No valid questions to process.")
            return 0

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

        for it in items:
            blocks = _extract_text_blocks_from_result(it)
            cid = _get_custom_id(it) or ""
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
            qnum = cid_to_q.get(cid)
            if not isinstance(payload, dict):
                # save raw
                label = f"Q-{qnum:03d}" if isinstance(qnum, int) else "unknown"
                raw_out = f"tmp/raw/task002-{label}.txt"
                _ensure_parent_dir(raw_out)
                Path(raw_out).write_text(combined, encoding="utf-8")
                print(f"Saved raw -> {raw_out}")
                continue

            # Coerce content-only responses into wrapper if possible
            outs = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else None
            content = payload.get("content") if isinstance(payload.get("content"), dict) else None
            if content is None:
                looks_like_content = (
                    isinstance(payload.get("answer"), str)
                    or isinstance(payload.get("agent_name"), str)
                    or isinstance(payload.get("id"), str)
                )
                if looks_like_content:
                    content = payload
                    payload = {"content": content}
            if not isinstance(outs, dict):
                outs = {}
                payload["outputs"] = outs
            if not isinstance(qnum, int):
                print(f"WARN: missing Q mapping for {cid}")
                continue
            # Enforce content fields
            try:
                if isinstance(content, dict):
                    content.setdefault("agent_name", args.architect_agent)
                    content["agent_name"] = args.architect_agent
                    content.setdefault("id", f"T-002-Q-{qnum:03d}")
                    content["id"] = f"T-002-Q-{qnum:03d}"
                    # Ensure question is present and matches qn when possible
                    qv = content.get("question")
                    if not isinstance(qv, str) or not qv.strip():
                        # Try to recover from the user prompt context
                        # We cannot access the original text here, so leave as-is; architect is instructed to copy it
                        pass
            except Exception:
                pass
            # Compute final path and update outputs.draft_file deterministically
            P = _next_P()
            final = Path("prp/drafts") / f"P-{P:03d}-T-002-Q-{qnum:03d}.json"
            try:
                outs["draft_file"] = str(final)
            except Exception:
                payload["outputs"] = {"draft_file": str(final)}

            if isinstance(content, dict):
                final.parent.mkdir(parents=True, exist_ok=True)
                Path(final).write_text(json.dumps(payload, indent=2), encoding="utf-8")
                print(f"Saved draft -> {final}")
            else:
                # invalid content; save diagnostics
                out = Path("tmp/raw") / f"task002-Q-{qnum:03d}-invalid.json"
                _ensure_parent_dir(str(out))
                out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                print(f"WARN: invalid JSON wrapper for Q-{qnum:03d}. Saved -> {out}")

        return 0

    # Legacy steps mode
    # Parse spec
    try:
        spec = parse_prp_steps(args.md)
    except SpecError as e:
        print(f"SpecError: {e}")
        return 1

    # Determine steps
    # For backward compatibility, allow a single default step if not provided
    available_ids = [s.id for s in spec.steps]
    selected_ids = available_ids
    runtime_args = {"feature_description": args.feature_description or ""}
    _prompt_text = Path(args.prompt).read_text(encoding="utf-8", errors="replace") if Path(args.prompt).exists() else ""
    requests = []
    batch_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    for sid in selected_ids:
        step = next(s for s in spec.steps if s.id == sid)
        agent_text = load_agent_text(step.agent)
        resolved_inputs = _resolve_mapping(step.inputs, runtime_args)
        if _prompt_text:
            resolved_inputs["_prompt_text"] = _prompt_text
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

    for it in items:
        blocks = _extract_text_blocks_from_result(it)
        cid = _get_custom_id(it)
        step_id = cid.replace("step-", "") if cid else "unknown-step"
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
        feature = args.feature_description or ""
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

        if _is_valid(payload):
            outputs = payload.get("outputs", {})
            dest = None
            if isinstance(outputs, dict) and isinstance(outputs.get("draft_file"), str):
                dest = outputs["draft_file"].replace("{slug}", slug).replace("{timestamp}", batch_ts).replace("{variant}", "a").replace("{prp_id}", "000")
            if not dest:
                dest = f"{slug}-{step_id}-{batch_ts}.json"
            dest = _normalize_draft_path(dest, slug, step_id, batch_ts, "json")
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

