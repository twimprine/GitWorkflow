#!/usr/bin/env bash
set -euo pipefail

# submit-batch.sh
# Submit request to Anthropic Batch API and monitor completion
# Handles submission, polling, and result retrieval

usage() {
    cat <<EOF
Usage: $0 --request <path> --output-dir <path> [options]

Submit request to Anthropic Batch API and retrieve results.

Required:
  --request PATH       Path to batch request JSONL file
  --output-dir PATH    Directory for results

Optional:
  --api-key KEY        Anthropic API key (or use ANTHROPIC_API_KEY env var)
  --poll-interval SEC  Polling interval in seconds (default: 60)
  --timeout SEC        Timeout in seconds (default: 7200 / 2 hours)
  --no-wait            Submit but don't wait for completion

Environment:
  ANTHROPIC_API_KEY    API key for authentication

Examples:
  $0 --request batch/request.jsonl --output-dir batch/results
  $0 --request batch/001-a-req.jsonl --output-dir batch/001-a-results --poll-interval 30
EOF
    exit 1
}

# Parse arguments
REQUEST_FILE=""
OUTPUT_DIR=""
API_KEY="${ANTHROPIC_API_KEY:-}"
POLL_INTERVAL=60
TIMEOUT=7200
NO_WAIT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --request) REQUEST_FILE="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --api-key) API_KEY="$2"; shift 2 ;;
        --poll-interval) POLL_INTERVAL="$2"; shift 2 ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        --no-wait) NO_WAIT=true; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

[[ -z "$REQUEST_FILE" ]] && { echo "Error: --request required"; usage; }
[[ -z "$OUTPUT_DIR" ]] && { echo "Error: --output-dir required"; usage; }
[[ ! -f "$REQUEST_FILE" ]] && { echo "Error: Request file not found: $REQUEST_FILE"; exit 1; }
[[ -z "$API_KEY" ]] && { echo "Error: API key required (--api-key or ANTHROPIC_API_KEY)"; exit 1; }

# Create output directory
mkdir -p "$OUTPUT_DIR"

API_BASE="https://api.anthropic.com/v1"
API_VERSION="2023-06-01"

# Submit batch request
echo "Submitting batch request..."
BATCH_RESPONSE=$(curl -s -X POST "$API_BASE/messages/batches" \
    -H "anthropic-version: $API_VERSION" \
    -H "anthropic-beta: message-batches-2024-09-24" \
    -H "content-type: application/json" \
    -H "x-api-key: $API_KEY" \
    --data-binary "@$REQUEST_FILE")

# Extract batch ID
BATCH_ID=$(echo "$BATCH_RESPONSE" | jq -r '.id // empty')

if [[ -z "$BATCH_ID" ]]; then
    echo "Error: Failed to submit batch request" >&2
    echo "Response: $BATCH_RESPONSE" >&2
    exit 1
fi

echo "✓ Batch submitted successfully"
echo "  Batch ID: $BATCH_ID"

# Save batch info
echo "$BATCH_RESPONSE" | jq . > "$OUTPUT_DIR/batch-info.json"
echo "$BATCH_ID" > "$OUTPUT_DIR/batch-id.txt"

if [[ "$NO_WAIT" == true ]]; then
    echo "Not waiting for completion (--no-wait specified)"
    echo "To check status later: curl -H 'x-api-key: $API_KEY' $API_BASE/messages/batches/$BATCH_ID"
    exit 0
fi

# Poll for completion
echo "Waiting for batch completion (polling every ${POLL_INTERVAL}s, timeout ${TIMEOUT}s)..."
START_TIME=$(date +%s)

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    if [[ $ELAPSED -gt $TIMEOUT ]]; then
        echo "Error: Timeout waiting for batch completion" >&2
        exit 1
    fi

    # Get batch status
    STATUS_RESPONSE=$(curl -s "$API_BASE/messages/batches/$BATCH_ID" \
        -H "anthropic-version: $API_VERSION" \
        -H "anthropic-beta: message-batches-2024-09-24" \
        -H "x-api-key: $API_KEY")

    PROCESSING_STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.processing_status')

    echo "[$(date +'%H:%M:%S')] Status: $PROCESSING_STATUS (elapsed: ${ELAPSED}s)"

    case "$PROCESSING_STATUS" in
        ended)
            echo "✓ Batch processing completed"
            break
            ;;
        expired|canceled)
            echo "Error: Batch $PROCESSING_STATUS" >&2
            echo "$STATUS_RESPONSE" | jq . >&2
            exit 1
            ;;
        in_progress)
            # Get progress info
            REQUEST_COUNTS=$(echo "$STATUS_RESPONSE" | jq -r '.request_counts')
            echo "  Progress: $REQUEST_COUNTS"
            ;;
    esac

    sleep "$POLL_INTERVAL"
done

# Save final status
echo "$STATUS_RESPONSE" | jq . > "$OUTPUT_DIR/batch-status.json"

# Retrieve results
echo "Retrieving batch results..."
RESULTS_RESPONSE=$(curl -s "$API_BASE/messages/batches/$BATCH_ID/results" \
    -H "anthropic-version: $API_VERSION" \
    -H "anthropic-beta: message-batches-2024-09-24" \
    -H "x-api-key: $API_KEY")

# Save raw results
echo "$RESULTS_RESPONSE" > "$OUTPUT_DIR/results.jsonl"

# Parse results
echo "Parsing results..."
SUCCESS_COUNT=0
ERROR_COUNT=0

while IFS= read -r line; do
    RESULT_TYPE=$(echo "$line" | jq -r '.result.type // "unknown"')
    CUSTOM_ID=$(echo "$line" | jq -r '.custom_id')

    if [[ "$RESULT_TYPE" == "succeeded" ]]; then
        # Extract PRP content
        CONTENT=$(echo "$line" | jq -r '.result.message.content[0].text')

        # Check if atomic PRPs (multiple PRPs separated)
        if echo "$CONTENT" | grep -qF -- "---ATOMIC-PRP-SEPARATOR---"; then
            # Split into separate atomic PRPs
            echo "  Detected atomic PRPs, splitting..."

            # Save content to temp file for reliable awk processing
            TEMP_CONTENT=$(mktemp)
            echo "$CONTENT" > "$TEMP_CONTENT"

            # Extract each atomic PRP using awk
            awk -v outdir="$OUTPUT_DIR" '
                BEGIN { prp_num=0; in_prp=0; filename="" }
                /^---ATOMIC-PRP-SEPARATOR---$/ {
                    if (in_prp && filename != "") close(filename)
                    prp_num++
                    in_prp=1
                    getline
                    if ($0 ~ /^filename:/) {
                        split($0, parts, " ")
                        filename = outdir "/" parts[2]
                        print "  Creating atomic PRP: " parts[2]
                    }
                    getline
                    next
                }
                in_prp && filename != "" { print > filename }
            ' "$TEMP_CONTENT"

            rm -f "$TEMP_CONTENT"
        else
            # Single PRP
            echo "$CONTENT" > "$OUTPUT_DIR/prp-${CUSTOM_ID}.md"
        fi

        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        ERROR=$(echo "$line" | jq -r '.result.error // "Unknown error"')
        echo "  Error in $CUSTOM_ID: $ERROR" >&2
        echo "$line" | jq . > "$OUTPUT_DIR/error-${CUSTOM_ID}.json"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
done < "$OUTPUT_DIR/results.jsonl"

# Summary
echo ""
echo "=== Batch Processing Complete ==="
echo "Batch ID: $BATCH_ID"
echo "Success: $SUCCESS_COUNT"
echo "Errors: $ERROR_COUNT"
echo "Results saved to: $OUTPUT_DIR"
echo ""

if [[ -d "$OUTPUT_DIR" ]]; then
    echo "Generated files:"
    ls -lh "$OUTPUT_DIR"/*.md 2>/dev/null || echo "  No PRP files generated"
fi

exit 0
