#!/usr/bin/env bash
set -euo pipefail

# run-autonomous-workflow.sh
# Fully autonomous PRP workflow - drop definitions and walk away
# This runs OUTSIDE Claude Code and calls it for each PRP implementation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "=== Starting Autonomous PRP Workflow ==="
log "This process will run until all PRPs are complete."
log "You can safely walk away - it handles everything."
log ""
log "📊 REAL-TIME PROGRESS MONITORING:"
log "   Run this in another terminal to watch agent activity:"
log "   $ tail -f logs/agent-progress.log"
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

# Configure for autonomous operation
export MAX_BATCHES_PER_HOUR=10
export MIN_BATCH_INTERVAL_MINUTES=0

while true; do
    log ""
    log "=== PHASE 1-5: Generate PRPs via Batch API ==="

    # Run Python orchestrator (generates PRPs, stops before execution)
    python execute-prps.py

    # Check if any PRPs were generated
    if ! ls prp/active/*.md 1>/dev/null 2>&1; then
        log "No PRPs in active queue"

        # Check if there are more definitions to process
        if ls prp/queue/*.md 1>/dev/null 2>&1; then
            log "Definitions still in queue, retrying in 60 seconds (rate limit)..."
            sleep 60
            continue
        else
            log "All definitions processed!"
            break
        fi
    fi

    log ""
    log "=== PHASE 6: Execute PRPs with Claude Code ==="

    # Count PRPs for this definition
    prp_count=$(ls prp/active/*.md 2>/dev/null | wc -l)
    prp_completed=0
    prp_failed=0

    # Process each PRP in sequence
    for prp_file in prp/active/*.md; do
        if [[ ! -f "$prp_file" ]]; then
            continue
        fi

        prp_name=$(basename "$prp_file" .md)
        log ""
        log "Executing PRP ($((prp_completed + prp_failed + 1))/$prp_count): $prp_name"
        log "---"

        # Call Claude Code to execute the PRP in headless mode
        # Headless mode (-p flag):
        # - Runs non-interactively (no UI)
        # - Auto-exits when complete
        # - Returns JSON with results and costs

        log "Calling Claude Code in headless mode..."
        result_json=$(echo "/execute-prp $prp_name" | claude -p --output-format json 2>&1)
        exit_code=$?

        # Parse JSON result
        if [[ $exit_code -eq 0 ]] && echo "$result_json" | jq empty 2>/dev/null; then
            is_error=$(echo "$result_json" | jq -r '.is_error // false')
            cost_usd=$(echo "$result_json" | jq -r '.total_cost_usd // 0')
            duration_ms=$(echo "$result_json" | jq -r '.duration_ms // 0')

            if [[ "$is_error" == "false" ]]; then
                log "✓ PRP completed: $prp_name"
                log "  Cost: \$${cost_usd} | Duration: ${duration_ms}ms"
                prp_completed=$((prp_completed + 1))

                # Cleanup after successful PRP execution
                log "Cleaning up after PRP execution..."

                # 1. Verify PRP moved from active/ to completed/
                if [[ -f "$prp_file" ]]; then
                    log "  Moving PRP from active/ to completed/"
                    mkdir -p prp/completed
                    mv "$prp_file" "prp/completed/ACTIVE-${prp_name}.md"
                fi

                # 2. Remove any temporary files in active/
                rm -f prp/active/.*.tmp prp/active/*.tmp 2>/dev/null || true

                log "✓ PRP cleanup complete"
            else
                log "✗ PRP failed: $prp_name"
                log "  Error from Claude Code execution"
                log "  Moving failed PRP to prp/queue/failed/"
                mkdir -p prp/queue/failed
                mv "$prp_file" "prp/queue/failed/"
                echo "Failed at: $(date)" > "prp/queue/failed/${prp_name}-error.txt"
                echo "Error: is_error field was true" >> "prp/queue/failed/${prp_name}-error.txt"
                prp_failed=$((prp_failed + 1))
            fi
        else
            # JSON parsing failed or non-zero exit code
            log "✗ PRP failed: $prp_name (exit code: $exit_code)"
            log "  Failed to parse JSON response from Claude Code"
            log "  Moving failed PRP to prp/queue/failed/"
            mkdir -p prp/queue/failed
            mv "$prp_file" "prp/queue/failed/"
            echo "Failed at: $(date)" > "prp/queue/failed/${prp_name}-error.txt"
            echo "Exit code: $exit_code" >> "prp/queue/failed/${prp_name}-error.txt"
            echo "Response: $result_json" >> "prp/queue/failed/${prp_name}-error.txt"
            prp_failed=$((prp_failed + 1))
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

            # Final cleanup: Remove ONLY temporary/intermediate files
            # KEEP: prp/completed/* (archived PRPs and summaries)
            # KEEP: prp/queue/processed/* (processed definitions)
            def_stem=$(basename "$def_file" .md)
            log "Final cleanup for: $def_stem (keeping archives)"

            # 1. Remove batch processing artifacts (temporary)
            log "  Removing batch artifacts..."
            rm -rf batch/${def_stem}-* 2>/dev/null || true

            # 2. Remove draft PRPs (intermediate, no longer needed)
            log "  Removing draft PRPs..."
            rm -f prp/drafts/*${def_stem}*.md 2>/dev/null || true
            rm -f prp/drafts/prp-prp-draft-*.md 2>/dev/null || true

            # 3. Verify active/ is empty (execute-prp should have moved to completed/)
            log "  Verifying active/ is clean..."
            active_count=$(ls -1 prp/active/*.md 2>/dev/null | wc -l)
            if [[ $active_count -gt 0 ]]; then
                log "  Warning: ${active_count} files still in active/"
                log "  These should have been archived by /execute-prp"
                log "  Leaving in place for review"
            fi

            # 4. Clean temporary files only
            rm -f prp/active/.*.tmp prp/drafts/.*.tmp batch/*.tmp 2>/dev/null || true

            log "✓ Cleanup complete - temporary files removed, archives preserved"
            log ""
            log "Preserved archives:"
            log "  - prp/completed/ ($(ls prp/completed/*.md 2>/dev/null | wc -l) files)"
            log "  - prp/queue/processed/ ($(ls prp/queue/processed/*.md 2>/dev/null | wc -l) files)"
        fi
    elif [[ $prp_failed -gt 0 ]]; then
        log "⚠ Some PRPs failed - definition remains in queue for retry"
        log "  Intermediate files preserved for debugging"
    fi

    # Check if more work to do
    if ls prp/queue/*.md 1>/dev/null 2>&1; then
        log "More definitions in queue, continuing..."
    else
        log "All work complete!"
        break
    fi
done

log ""
log "=== Autonomous Workflow Complete ==="
log ""
log "Summary:"
log "  Processed: $(ls prp/queue/processed/*.md 2>/dev/null | wc -l) definitions"
log "  Completed: $(ls prp/completed/*.md 2>/dev/null | wc -l) PRPs"
log "  Failed:    $(ls prp/queue/failed/*.md 2>/dev/null | wc -l) items"
log ""
log "You can now review the completed work!"

exit 0
