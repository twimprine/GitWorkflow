---
allowed-tools: Task, Read, Grep, Glob, WebSearch, FileRead
argument-hint: [feature description]
description: Review task list and questions for agent consensus
model: claude-opus-4-1-20250805
---

Purpose: Consolidate and validate outstanding questions from TASK001 drafts and produce a single, clean, deterministic list with answers where possible, strictly using the TASK002 template provided by the runner.

Inputs and scope:
- Read all relevant draft files under `prp/drafts/` for the current feature slug/timestamp.
- Prefer local sources: prior draft content, prompt files under `prompts/`, and project docs in the repo.
- Only use WebSearch if the answer cannot be found locally; if used, cite the URL succinctly.

What to do:
- Extract all questions and clarifications raised across drafts; deduplicate semantically identical questions.
- Attempt to answer each question using available local context. If an answer is not confidently available, mark it as needs-input.
- Note the evidence path(s) used for each answer (e.g., `prp/drafts/<file>.json`, `README.md#line`, or URL if WebSearch was essential).
- Identify conflicts between drafts (same question, different proposed answers); keep the most strongly supported answer and record the alternative(s) under conflicts.
- Maintain atomicity: do not expand scope; do not introduce new features or tasks.

Determinism and formatting:
- Follow the TARGET JSON TEMPLATE for TASK002 exactly (key names, order, and nesting). Do not add/remove keys.
- JSON only; no commentary outside of JSON.
- Produce stable ordering: sort lists by question text (case-insensitive) and sort nested arrays/objects by their primary key where applicable.
- Keep language concise and unambiguous; avoid speculative phrasing.

Answering policy:
- Local-first: Use content from drafts and repo files before considering WebSearch.
- If partial information exists, provide the partial answer and explicitly mark remaining gaps as needs-input.
- If no answer can be supported, set status to needs-input and add a brief, concrete request describing the minimal info required to resolve it.

Output contract (enforced by the runner):
- You will be given the TASK002 JSON template; populate its fields exactly.
- The runner wraps your content in a strict JSON envelope; do not alter the wrapper structure.

Edge cases:
- If no drafts are found, return an empty, valid structure with a notes field explaining the absence.
- If all questions are duplicates, return one canonical entry and list de-duplicated variants under duplicates.

Note: Only reference agents or roles by their exact IDs if needed for attribution; do not invent or suggest new agents here. That happens in subsequent steps.

