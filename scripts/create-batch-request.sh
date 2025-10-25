#!/usr/bin/env bash
set -euo pipefail

# create-batch-request.sh
# Creates Anthropic Batch API request from collected context
# Takes context JSON and creates batch API request for PRP planning phase

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
Usage: $0 --context <path> --phase <draft|generate> --output <path>

Create Anthropic Batch API request from collected context.

Required:
  --context PATH     Path to context JSON (from collect-prp-context.sh)
  --phase PHASE      PRP phase: draft or generate
  --output PATH      Output JSONL file for batch API

Optional:
  --model MODEL      Model to use (default: claude-sonnet-4-5-20250929)
  --max-tokens NUM   Max tokens (default: 16000)
  --temperature NUM  Temperature (default: 1.0)

Examples:
  $0 --context batch/context.json --phase draft --output batch/request.jsonl
  $0 --context batch/001-a-context.json --phase generate --output batch/001-a-req.jsonl
EOF
    exit 1
}

# Parse arguments
CONTEXT_FILE=""
PHASE=""
OUTPUT_FILE=""
MODEL="claude-sonnet-4-5-20250929"
MAX_TOKENS=16000
TEMPERATURE=1.0

while [[ $# -gt 0 ]]; do
    case $1 in
        --context) CONTEXT_FILE="$2"; shift 2 ;;
        --phase) PHASE="$2"; shift 2 ;;
        --output) OUTPUT_FILE="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --max-tokens) MAX_TOKENS="$2"; shift 2 ;;
        --temperature) TEMPERATURE="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

[[ -z "$CONTEXT_FILE" ]] && { echo "Error: --context required"; usage; }
[[ -z "$PHASE" ]] && { echo "Error: --phase required"; usage; }
[[ -z "$OUTPUT_FILE" ]] && { echo "Error: --output required"; usage; }
[[ ! -f "$CONTEXT_FILE" ]] && { echo "Error: Context file not found: $CONTEXT_FILE"; exit 1; }
[[ ! "$PHASE" =~ ^(draft|generate)$ ]] && { echo "Error: Phase must be 'draft' or 'generate'"; exit 1; }

# Validate context JSON
if ! jq empty "$CONTEXT_FILE" 2>/dev/null; then
    echo "Error: Invalid context JSON file" >&2
    exit 1
fi

# Create output directory
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Extract PRP content from context
PRP_CONTENT=$(jq -r '.prp.content' "$CONTEXT_FILE")
PRP_FILE=$(jq -r '.prp.file' "$CONTEXT_FILE")

# Build system prompt based on phase
build_system_prompt() {
    cat <<'SYSTEM_PROMPT'
You are an expert software architect and product manager creating Product Requirements Proposals (PRPs) for complex software projects.

Your task is to create comprehensive, implementation-ready PRPs that will be executed by specialized AI agents in a multi-agent workflow.

Context Provided:
- Complete project standards and conventions
- Current codebase structure and patterns
- Existing tests and quality gates
- Recent successful PRPs for reference
- Git state and active work

Quality Requirements:
- 100% test coverage mandatory (TDD approach)
- Security-first design
- Complete error handling
- Comprehensive documentation
- Production-ready code only

Output must be markdown-formatted PRP following the provided template exactly.
SYSTEM_PROMPT
}

# Build user prompt based on phase
build_user_prompt() {
    local phase="$1"
    local context_file="$2"

    if [[ "$phase" == "draft" ]]; then
        cat <<PROMPT
# Task: Create Draft PRP

Using the provided context, create a draft Product Requirements Proposal following the draft-prp template.

## Input Definition
$(jq -r '.prp.content' "$context_file")

## Available Context

### Project Standards
$(jq -r '.standards | to_entries | .[] | "- \(.key): \(.value[:200])..."' "$context_file" 2>/dev/null || echo "None available")

### Project Structure
\`\`\`
$(jq -r '.structure.tree' "$context_file" 2>/dev/null || echo "Not available")
\`\`\`

### Technology Stack
$(jq -r '.packages.root' "$context_file" 2>/dev/null | jq -r '.dependencies // {} | keys | .[]' 2>/dev/null || echo "Not available")

### Recent PRPs (for reference)
$(jq -r '.recent_prps[0].content[:500]' "$context_file" 2>/dev/null || echo "None available")

### Current Git State
- Branch: $(jq -r '.git_state.branch' "$context_file")
- Active PRs: $(jq -r '.git_state.pull_requests | length' "$context_file")

## Instructions

1. Analyze the definition and extract core requirements
2. Review project standards for conventions and patterns
3. Identify technology stack and appropriate agents
4. Check recent PRPs for scope sizing and structure
5. Create draft PRP following template exactly
6. Include all required sections
7. Focus on clarity and completeness
8. Add questions that need clarification

## Output Format

Return ONLY the markdown-formatted draft PRP. No additional commentary.
Follow the template structure exactly as defined in the draft-prp command documentation.
PROMPT
    else
        cat <<PROMPT
# Task: Generate Complete PRP from Draft

Using the provided context, generate a comprehensive, implementation-ready Product Requirements Proposal from the draft.

## Draft PRP
$(jq -r '.prp.content' "$context_file")

## Available Context

### Global Standards (CLAUDE.md)
$(jq -r '.claude_md.global[:1000]' "$context_file" 2>/dev/null || echo "Not available")

### Project Standards
$(jq -r '.standards | to_entries | .[] | "#### \(.key)\n\(.value[:500])...\n"' "$context_file" 2>/dev/null || echo "None available")

### Codebase Structure
\`\`\`
$(jq -r '.structure.tree' "$context_file" 2>/dev/null || echo "Not available")
\`\`\`

### Existing Patterns (sample files)
$(jq -r '.source_files[:3] | .[] | "- \(.path)"' "$context_file" 2>/dev/null || echo "None available")

### Test Patterns (sample files)
$(jq -r '.test_files[:3] | .[] | "- \(.path)"' "$context_file" 2>/dev/null || echo "None available")

### Configuration
- Jest: $(jq -r '.configs.jest[:200]' "$context_file" 2>/dev/null || echo "Not configured")
- TypeScript: $(jq -r '.configs.tsconfig[:200]' "$context_file" 2>/dev/null || echo "Not configured")
- TDD Pipeline: $(jq -r '.configs.tdd_workflow[:200]' "$context_file" 2>/dev/null || echo "Not configured")

### Recent Completed PRPs
$(jq -r '.recent_prps[] | "### \(.file)\n\(.content[:800])...\n"' "$context_file" 2>/dev/null || echo "None available")

### Git State
- Branch: $(jq -r '.git_state.branch' "$context_file")
- Recent commits: $(jq -r '.git_state.log' "$context_file" 2>/dev/null | head -n 5)
- Active PRs: $(jq -r '.git_state.pull_requests | .[] | "- #\(.number): \(.title) (\(.state))"' "$context_file" 2>/dev/null)

## Size Check and Splitting

1. **Count Characters**: Calculate total characters in draft
2. **Decision Point**:
   - If ≤5,000 chars: Generate single comprehensive PRP
   - If >5,000 chars: Split into atomic PRPs following these steps:
     a. Identify natural task boundaries
     b. Create separate PRP for each task (###-a-001, ###-a-002, etc.)
     c. Ensure each atomic PRP ≤5,000 chars
     d. Maintain dependency order
     e. Return ALL atomic PRPs in sequence

## Instructions

1. **Analyze Draft**: Review completeness and scope
2. **Check Size**: Determine if splitting needed
3. **Research Context**:
   - Review ALL provided standards
   - Study recent PRPs for patterns
   - Understand codebase structure
   - Identify integration points
4. **Create Comprehensive PRP**:
   - Follow generate-prp template exactly
   - Include detailed TDD test specifications
   - Define all quality gates
   - Specify agent coordination
   - Include complete implementation blueprint
5. **If Splitting Required**:
   - Create multiple atomic PRPs
   - Number sequentially: ###-a-001, ###-a-002, etc.
   - Each atomic PRP must be complete and independent
   - Include dependency information

## Output Format

If single PRP (≤5k chars):
- Return ONLY the markdown-formatted PRP
- No additional commentary

If atomic PRPs (>5k chars):
- Return each atomic PRP separated by:
\`\`\`
---ATOMIC-PRP-SEPARATOR---
filename: ###-a-001-description.md
---
\`\`\`
- Include ALL atomic PRPs in one response
- Maintain execution order

Follow the generate-prp template structure exactly as defined in the documentation.
PROMPT
    fi
}

# Extract core definition name from filename (handles draft/generated filenames)
extract_core_name() {
    local filename="$1"
    local basename_no_ext=$(basename "$filename" .md)

    # If it's a draft file (prp-prp-draft-NAME-TIMESTAMP)
    if [[ "$basename_no_ext" =~ ^prp-prp-draft-(.+)-[0-9]+$ ]]; then
        echo "${BASH_REMATCH[1]}"
    # If it's a generated PRP (prp-NAME-TIMESTAMP or similar)
    elif [[ "$basename_no_ext" =~ ^prp-(.+)-[0-9]+$ ]]; then
        echo "${BASH_REMATCH[1]}"
    # Otherwise just remove .md extension
    else
        echo "$basename_no_ext"
    fi
}

# Create batch request (wrapped in requests array for API)
{
    # Custom ID for tracking (max 64 chars)
    # Format: prp-{phase}-{core_name}-{timestamp}
    CORE_NAME=$(extract_core_name "$PRP_FILE")
    # Truncate core name if needed to stay under 64 char limit
    # prp-{phase}-{name}-{timestamp} = 4 + 9 + 1 + name + 1 + 10 = 25 + name
    MAX_CORE_LEN=$((64 - 25))
    if [[ ${#CORE_NAME} -gt $MAX_CORE_LEN ]]; then
        CORE_NAME="${CORE_NAME:0:$MAX_CORE_LEN}"
    fi
    CUSTOM_ID="prp-${PHASE}-${CORE_NAME}-$(date +%s)"

    # Build the request wrapped in requests array
    jq -n \
        --arg custom_id "$CUSTOM_ID" \
        --arg model "$MODEL" \
        --argjson max_tokens "$MAX_TOKENS" \
        --argjson temperature "$TEMPERATURE" \
        --arg system "$(build_system_prompt)" \
        --arg user "$(build_user_prompt "$PHASE" "$CONTEXT_FILE")" \
        '{
            requests: [{
                custom_id: $custom_id,
                params: {
                    model: $model,
                    max_tokens: $max_tokens,
                    temperature: $temperature,
                    messages: [
                        {
                            role: "user",
                            content: $user
                        }
                    ],
                    system: $system
                }
            }]
        }'
} > "$OUTPUT_FILE"

# Validate JSON
if ! jq empty "$OUTPUT_FILE" 2>/dev/null; then
    echo "Error: Generated invalid JSON" >&2
    exit 1
fi

echo "✓ Created batch request: $OUTPUT_FILE"
echo "  Custom ID: $CUSTOM_ID"
echo "  Phase: $PHASE"
echo "  Model: $MODEL"
echo "  Max tokens: $MAX_TOKENS"
