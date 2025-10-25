#!/usr/bin/env bash
set -euo pipefail

# execute-prps-from-active.sh
# Execute PRPs that are already in prp/active/ (after review)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "=== PRP Execution Mode (Post-Review) ==="
log "Executing PRPs from prp/active/"
log ""

# Check for PRPs in active
if ! ls prp/active/*.md 1>/dev/null 2>&1; then
    log "No PRPs found in prp/active/"
    log ""
    log "Run ./generate-prps.sh first to generate PRPs for review"
    exit 0
fi

# Count and display PRPs
prp_count=$(ls prp/active/*.md 2>/dev/null | wc -l)
log "Found $prp_count PRP(s) ready for execution:"
for prp in prp/active/*.md; do
    if [[ -f "$prp" ]]; then
        log "  - $(basename "$prp")"
    fi
done

log ""
read -p "Execute these PRPs? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Execution cancelled"
    exit 0
fi

log ""
log "=== Executing PRPs with Claude Code ==="
log ""

prp_completed=0
prp_failed=0

# Process each PRP in sequence
for prp_file in prp/active/*.md; do
    if [[ ! -f "$prp_file" ]]; then
        continue
    fi

    prp_name=$(basename "$prp_file" .md)
    log ""
    log "Executing ($((prp_completed + prp_failed + 1))/$prp_count): $prp_name"
    log "---"

    # Call Claude Code to execute the PRP
    if claude /execute-prp "$prp_name"; then
        log "✓ PRP completed: $prp_name"
        ((prp_completed++))
    else
        log "✗ PRP failed: $prp_name (exit code: $?)"
        log "Moving failed PRP to prp/queue/failed/"
        mkdir -p prp/queue/failed
        mv "$prp_file" "prp/queue/failed/"
        echo "Failed at: $(date)" > "prp/queue/failed/${prp_name}-error.txt"
        echo "Exit code: $?" >> "prp/queue/failed/${prp_name}-error.txt"
        ((prp_failed++))
    fi

    log ""
done

# Move definition to processed if all PRPs succeeded
if [[ $prp_completed -eq $prp_count ]]; then
    # Find and move the definition file
    def_file=$(ls prp/queue/*.md 2>/dev/null | head -1)
    if [[ -n "$def_file" ]]; then
        mkdir -p prp/queue/processed
        mv "$def_file" prp/queue/processed/
        log "✓ All PRPs completed - moved definition to processed: $(basename "$def_file")"
    fi
fi

log ""
log "=== Execution Complete ==="
log "  Completed: $prp_completed"
log "  Failed:    $prp_failed"
log ""

if [[ $prp_failed -eq 0 ]]; then
    log "All PRPs executed successfully! 🎉"
else
    log "Some PRPs failed. Check prp/queue/failed/ for details"
fi

exit 0
