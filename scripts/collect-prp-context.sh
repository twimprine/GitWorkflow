#!/usr/bin/env bash
set -euo pipefail

# collect-prp-context.sh
# Collects all necessary context data for batch-mode PRP planning
# Output: JSON structure ready for Anthropic Batch API submission

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Usage
usage() {
    cat <<EOF
Usage: $0 --prp-file <path> --output <path> [options]

Collect project context for batch-mode PRP planning.

Required:
  --prp-file PATH      Path to PRP definition or draft file
  --output PATH        Output JSON file for batch API submission

Optional:
  --project-root PATH  Project root directory (default: current dir)
  --include-tests      Include test files in context (default: true)
  --max-files NUM      Max related source files to include (default: 20)
  --verbose            Show collection progress

Examples:
  $0 --prp-file prp/queue/feature.md --output batch/context.json
  $0 --prp-file prp/drafts/001-a-feature.md --output batch/001-a-context.json --verbose
EOF
    exit 1
}

# Parse arguments
PRP_FILE=""
OUTPUT_FILE=""
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
INCLUDE_TESTS=true
MAX_FILES=20
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --prp-file) PRP_FILE="$2"; shift 2 ;;
        --output) OUTPUT_FILE="$2"; shift 2 ;;
        --project-root) PROJECT_ROOT="$2"; shift 2 ;;
        --include-tests) INCLUDE_TESTS=true; shift ;;
        --max-files) MAX_FILES="$2"; shift 2 ;;
        --verbose) VERBOSE=true; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

[[ -z "$PRP_FILE" ]] && { echo "Error: --prp-file required"; usage; }
[[ -z "$OUTPUT_FILE" ]] && { echo "Error: --output required"; usage; }
[[ ! -f "$PRP_FILE" ]] && { echo "Error: PRP file not found: $PRP_FILE"; exit 1; }

log() {
    [[ "$VERBOSE" == true ]] && echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

# Helper: Read file and escape for JSON
read_file_json() {
    local file="$1"
    if [[ -f "$file" ]]; then
        jq -Rs . < "$file"
    else
        echo '""'
    fi
}

# Helper: Read multiple files into array
read_files_array() {
    local pattern="$1"
    local max="${2:-10}"
    echo "["
    local count=0
    while IFS= read -r file; do
        [[ $count -gt 0 ]] && echo ","
        echo "{"
        echo "  \"path\": $(echo "$file" | jq -Rs .)"
        echo ", \"content\": $(read_file_json "$file")"
        echo "}"
        ((count++))
        [[ $count -ge $max ]] && break
    done < <(find "$PROJECT_ROOT" -type f -name "$pattern" 2>/dev/null | head -n "$max")
    echo "]"
}

log "Starting context collection for: $PRP_FILE"

# Create output directory
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Start building JSON context
{
    echo "{"

    # 1. PRP Document
    log "Collecting PRP document..."
    echo "  \"prp\": {"
    echo "    \"file\": $(echo "$PRP_FILE" | jq -Rs .)"
    echo "  , \"content\": $(read_file_json "$PRP_FILE")"
    echo "  }"

    # 2. CLAUDE.md files
    log "Collecting CLAUDE.md files..."
    echo ", \"claude_md\": {"
    echo "    \"global\": $(read_file_json ~/.claude/CLAUDE.md)"
    if [[ -f "$PROJECT_ROOT/CLAUDE.md" ]]; then
        echo "  , \"project\": $(read_file_json "$PROJECT_ROOT/CLAUDE.md")"
    else
        echo "  , \"project\": \"\""
    fi
    echo "  }"

    # 3. Project Standards
    log "Collecting project standards..."
    echo ", \"standards\": {"
    first=true
    shopt -s nullglob
    for std_file in "$PROJECT_ROOT"/docs/standards/*.md; do
        [[ ! -f "$std_file" ]] && continue
        [[ "$first" == false ]] && echo ","
        first=false
        std_name=$(basename "$std_file" .md)
        echo "    \"$std_name\": $(read_file_json "$std_file")"
    done
    shopt -u nullglob
    [[ "$first" == true ]] && echo "    \"none\": \"\"" # Placeholder if no standards
    echo "  }"

    # 4. Directory Structure
    log "Collecting directory structure..."
    echo ", \"structure\": {"
    echo "    \"tree\": $(cd "$PROJECT_ROOT" && tree -L 3 -I 'node_modules|dist|coverage|.git' --dirsfirst 2>/dev/null | jq -Rs . || echo '""')"
    echo "  }"

    # 5. Package Manifests
    log "Collecting package manifests..."
    echo ", \"packages\": {"
    echo "    \"root\": $(read_file_json "$PROJECT_ROOT/package.json")"
    echo "  , \"services\": $(read_files_array 'package.json' 10)"
    echo "  , \"lock\": $(read_file_json "$PROJECT_ROOT/package-lock.json")"
    echo "  }"

    # 6. Config Files
    log "Collecting config files..."
    echo ", \"configs\": {"
    echo "    \"jest\": $(read_file_json "$PROJECT_ROOT/jest.config.js")"
    echo "  , \"tsconfig\": $(read_file_json "$PROJECT_ROOT/tsconfig.json")"
    echo "  , \"eslint\": $(read_file_json "$PROJECT_ROOT/.eslintrc.js")"
    echo "  , \"tdd_workflow\": $(read_file_json "$PROJECT_ROOT/.github/workflows/tdd-enforcement.yml")"
    echo "  }"

    # 7. Related Source Files (basic - would need smarter detection)
    log "Collecting related source files..."
    echo ", \"source_files\": $(read_files_array '*.ts' $MAX_FILES)"

    # 8. Existing Tests (if requested)
    if [[ "$INCLUDE_TESTS" == true ]]; then
        log "Collecting test files..."
        echo ", \"test_files\": $(read_files_array '*.test.ts' $MAX_FILES)"
    else
        echo ", \"test_files\": []"
    fi

    # 9. Git State
    log "Collecting git state..."
    echo ", \"git_state\": {"
    git_status=$(cd "$PROJECT_ROOT" && git status --short 2>/dev/null || true)
    echo "    \"status\": $(echo "$git_status" | jq -Rs .)"
    git_log=$(cd "$PROJECT_ROOT" && git log --oneline -10 2>/dev/null || true)
    echo "  , \"log\": $(echo "$git_log" | jq -Rs .)"
    git_branch=$(cd "$PROJECT_ROOT" && git branch --show-current 2>/dev/null || true)
    echo "  , \"branch\": $(echo "$git_branch" | jq -Rs .)"
    git_prs=$(cd "$PROJECT_ROOT" && gh pr list --limit 5 --json number,title,state 2>/dev/null || echo '[]')
    echo "  , \"pull_requests\": $(echo "$git_prs" | jq -c . 2>/dev/null || echo '[]')"
    echo "  }"

    # 10. Recent PRPs
    log "Collecting recent PRPs..."
    echo ", \"recent_prps\": ["
    count=0
    if [[ -d "$PROJECT_ROOT/prp/completed" ]]; then
        for prp_file in "$PROJECT_ROOT"/prp/completed/COMPLETE-*.md; do
            [[ ! -f "$prp_file" ]] && continue
            [[ $count -gt 0 ]] && echo ","
            echo "    {"
            echo "      \"file\": $(echo "$prp_file" | jq -Rs .)"
            echo "    , \"content\": $(read_file_json "$prp_file")"
            echo "    }"
            ((count++))
            [[ $count -ge 3 ]] && break
        done
    fi
    [[ $count -eq 0 ]] && echo "    {}"
    echo "  ]"

    # 11. OpenAPI Specs (if exist)
    log "Collecting OpenAPI specs..."
    echo ", \"api_specs\": $(read_files_array '*.openapi.yaml' 5)"

    # Metadata
    echo ", \"metadata\": {"
    echo "    \"collected_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\""
    echo "  , \"project_root\": $(echo "$PROJECT_ROOT" | jq -Rs .)"
    echo "  , \"collector_version\": \"1.0.0\""
    echo "  }"

    echo "}"
} > "$OUTPUT_FILE"

log "Context collection complete: $OUTPUT_FILE"
log "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"

# Validate JSON
if ! jq empty "$OUTPUT_FILE" 2>/dev/null; then
    echo "Error: Generated invalid JSON" >&2
    exit 1
fi

echo "✓ Successfully collected context to: $OUTPUT_FILE"
