#!/usr/bin/env python3
"""
Parse a prp-steps fenced YAML block from a markdown file into a structured CommandSpec.

Contract summary:
- Fenced code block with language tag: prp-steps
- YAML keys: version, command, args, agents, steps
- steps[*]: { id, agent, action, inputs, outputs }

Outputs a dict suitable for downstream batch construction.
"""
from __future__ import annotations
import re
import sys
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

PRP_BLOCK_PATTERN = re.compile(r"```prp-steps\n(.*?)\n```", re.DOTALL)


class SpecError(ValueError):
    pass


@dataclass
class StepSpec:
    id: str
    agent: str
    action: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandSpec:
    version: int
    command: str
    args: List[str]
    agents: List[str]
    steps: List[StepSpec]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "command": self.command,
            "args": list(self.args),
            "agents": list(self.agents),
            "steps": [
                {
                    "id": s.id,
                    "agent": s.agent,
                    "action": s.action,
                    "inputs": s.inputs,
                    "outputs": s.outputs,
                }
                for s in self.steps
            ],
        }


def _extract_prp_block(md_text: str) -> str:
    m = PRP_BLOCK_PATTERN.search(md_text)
    if not m:
        raise SpecError("No prp-steps fenced block found in markdown.")
    return m.group(1)


def _validate_and_build(spec: Dict[str, Any]) -> CommandSpec:
    # Basic presence
    for k in ("version", "command", "args", "agents", "steps"):
        if k not in spec:
            raise SpecError(f"Missing required key: {k}")

    # Types
    if not isinstance(spec["version"], int):
        raise SpecError("version must be an integer")
    if spec["version"] != 0:
        raise SpecError(f"Unsupported version: {spec['version']}")

    if not isinstance(spec["command"], str):
        raise SpecError("command must be a string")
    if not isinstance(spec["args"], list) or not all(isinstance(a, str) for a in spec["args"]):
        raise SpecError("args must be a list of strings")
    if not isinstance(spec["agents"], list) or not all(isinstance(a, str) for a in spec["agents"]):
        raise SpecError("agents must be a list of strings")
    if not isinstance(spec["steps"], list):
        raise SpecError("steps must be a list")

    # Steps validation
    seen_ids = set()
    step_specs: List[StepSpec] = []
    for i, raw in enumerate(spec["steps"], 1):
        if not isinstance(raw, dict):
            raise SpecError(f"step #{i} must be a mapping")
        for rk in ("id", "agent", "action"):
            if rk not in raw:
                raise SpecError(f"step #{i} missing required key: {rk}")
        sid = raw["id"]
        if not isinstance(sid, str) or not sid:
            raise SpecError(f"step #{i} id must be a non-empty string")
        if sid in seen_ids:
            raise SpecError(f"duplicate step id: {sid}")
        seen_ids.add(sid)

        agent = raw["agent"]
        if agent not in spec["agents"]:
            raise SpecError(f"step '{sid}' agent '{agent}' is not listed in agents[]")

        action = raw["action"]
        if not isinstance(action, str) or not action:
            raise SpecError(f"step '{sid}' action must be a non-empty string")
        _validate_action(action, sid)

        inputs = raw.get("inputs", {})
        outputs = raw.get("outputs", {})
        if not isinstance(inputs, dict) or not isinstance(outputs, dict):
            raise SpecError(f"step '{sid}' inputs/outputs must be mappings")

        step_specs.append(StepSpec(id=sid, agent=agent, action=action, inputs=inputs, outputs=outputs))

    return CommandSpec(
        version=spec["version"],
        command=spec["command"],
        args=spec["args"],
        agents=spec["agents"],
        steps=step_specs,
    )


_ALLOWED_ACTIONS = {
    "generate_from_template",
    "run_script",
}


def _validate_action(action: str, sid: str) -> None:
    if action not in _ALLOWED_ACTIONS:
        raise SpecError(f"step '{sid}' has unknown action '{action}'. Allowed: {sorted(_ALLOWED_ACTIONS)}")


def parse_prp_steps(md_path: str | Path) -> CommandSpec:
    md_text = Path(md_path).read_text(encoding="utf-8")
    yaml_str = _extract_prp_block(md_text)
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        raise SpecError(f"Invalid YAML in prp-steps block: {e}") from e
    if not isinstance(data, dict):
        raise SpecError("Top-level prp-steps YAML must be a mapping")
    return _validate_and_build(data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: parse_prp_steps.py <markdown-file>", file=sys.stderr)
        sys.exit(2)
    try:
        spec = parse_prp_steps(sys.argv[1])
    except SpecError as e:
        print(f"SpecError: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(spec.to_dict(), indent=2))
