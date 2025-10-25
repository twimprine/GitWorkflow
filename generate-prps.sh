#!/usr/bin/env bash
set -euo pipefail

# generate-prps.sh
# Generate PRPs from definitions (Phases 1-5 only)
# Stops for review before execution

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "=== PRP Generation Mode (Review-First) ==="
log "This will generate PRPs and STOP for your review."
log ""

# Check for definitions in queue
if ! ls prp/queue/*.md 1>/dev/null 2>&1; then
    log "No definition files found in prp/queue/"
    log "Drop .md files there and re-run this script"
    exit 0
fi

# Activate venv
log "Activating virtual environment..."
source venv/bin/activate

# Configure rate limiting (can be overridden via environment)
export MAX_BATCHES_PER_HOUR="${MAX_BATCHES_PER_HOUR:-1}"
export MIN_BATCH_INTERVAL_MINUTES="${MIN_BATCH_INTERVAL_MINUTES:-60}"

log ""
log "=== Generating PRPs via Batch API ==="
log "Rate limits: $MAX_BATCHES_PER_HOUR batches/hour, ${MIN_BATCH_INTERVAL_MINUTES}min interval"
log ""

# Run Python orchestrator (generates PRPs, stops before execution)
python execute-prps.py

# Check results
prp_count=$(ls prp/active/*.md 2>/dev/null | wc -l || echo 0)

log ""
log "=== Generation Complete ==="
log ""

if [[ $prp_count -gt 0 ]]; then
    log "Generated PRPs ready for review:"
    for prp in prp/active/*.md; do
        if [[ -f "$prp" ]]; then
            log "  - $(basename "$prp")"
        fi
    done
    log ""
    log "Next steps:"
    log "  1. Review PRPs in prp/active/"
    log "  2. When ready to execute: ./execute-prps-from-active.sh"
    log ""
else
    log "No PRPs generated. Check logs for details:"
    log "  - logs/prp-orchestrator-dev.log"
    log ""

    remaining=$(ls prp/queue/*.md 2>/dev/null | wc -l || echo 0)
    if [[ $remaining -gt 0 ]]; then
        log "Definitions still in queue: $remaining"
        log "May need to wait for rate limit window to retry"
    fi
fi

exit 0
