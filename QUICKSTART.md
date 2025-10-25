# Autonomous PRP Workflow - Quick Start

## The Completely Hands-Off Workflow

Drop definition files and walk away. The system handles everything autonomously.

---

## One-Time Setup

```bash
cd /path/to/your/project

# 1. Ensure venv exists with dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Set your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

---

## Usage (The AFK Way)

### Step 1: Drop Definition Files

Create brain-dump markdown files in `prp/queue/`:

```bash
cat > prp/queue/my-feature.md << 'EOF'
# My Feature Name

## What I Want
Quick description of the feature

## Requirements
- Bullet points of what it needs
- Can be rough, AI will flesh it out

## Success Criteria
- How you know it's done
EOF
```

### Step 2: Run ONE Command

```bash
./run-autonomous-workflow.sh
```

**That's it!** Now walk away. ☕

---

## What Happens (Fully Autonomous)

```
[Your Input]
└─> prp/queue/my-feature.md

[Phase 1-5: Batch API] (~8 min per definition)
├─> Collect project context
├─> Generate draft PRP
├─> Generate final atomic PRPs
└─> PRPs appear in prp/active/

[Phase 6: Claude Code] (~varies per PRP)
├─> Execute PRP 1
│   ├─> Implement code
│   ├─> Write tests (100% coverage)
│   ├─> Run CI checks
│   └─> Move to prp/completed/
├─> Execute PRP 2
│   └─> (same)
└─> Execute PRP 3
    └─> (same)

[Completion]
├─> Definition moved to prp/queue/processed/
└─> Ready for next definition!
```

---

## Real-Time Monitoring

Watch the script output to see progress:

```bash
./run-autonomous-workflow.sh

# Output shows:
# - Batch API submission
# - PRP generation progress
# - Claude Code execution for each PRP
# - Test results
# - Completion status
```

---

## Multiple Definitions

Just drop multiple files in `prp/queue/`:

```bash
prp/queue/
├── feature-1.md
├── feature-2.md
└── feature-3.md
```

Run the script once:

```bash
./run-autonomous-workflow.sh
```

It processes them all sequentially, completely autonomous.

---

## Cost Control

Default rate limiting (configured in `.env`):

```bash
MAX_BATCHES_PER_HOUR=1          # Max batch API calls per hour
MIN_BATCH_INTERVAL_MINUTES=60    # Minimum time between batches
```

For testing with no limits:

```bash
export MAX_BATCHES_PER_HOUR=10
export MIN_BATCH_INTERVAL_MINUTES=0
./run-autonomous-workflow.sh
```

**Typical Costs:**
- Draft PRP: ~$0.02
- Generate PRPs: ~$0.10
- **Total per definition: ~$0.13**

---

## Error Handling

The system is resilient:

- **Batch API fails**: Retries with backoff
- **PRP execution fails**: Moves to `prp/queue/failed/`, continues with next
- **Rate limit hit**: Waits automatically, then continues
- **Definition remains in queue**: Until all PRPs complete successfully

Failed items:

```
prp/queue/failed/
├── my-feature.md          # The definition that failed
└── my-feature-error.txt   # Error details
```

Fix and move back to queue to retry.

---

## Checking Results

After the workflow completes:

```bash
# See what was processed
ls prp/queue/processed/

# See completed PRPs
ls prp/completed/

# See any failures
ls prp/queue/failed/
```

---

## Advanced: Multiple Environments

Create different `.env` files:

```bash
# .env.dev
ANTHROPIC_API_KEY=sk-ant-dev-...
MAX_BATCHES_PER_HOUR=10

# .env.qa
ANTHROPIC_API_KEY=sk-ant-qa-...
MAX_BATCHES_PER_HOUR=5

# .env.prod
ANTHROPIC_API_KEY=sk-ant-prod-...
MAX_BATCHES_PER_HOUR=1
```

Run with specific environment:

```bash
cp .env.dev .env
./run-autonomous-workflow.sh
```

---

## Example: Complete AFK Session

```bash
# Morning: Drop 5 feature definitions
cat > prp/queue/feature-1.md << 'EOF'
# User Authentication
Add login/logout with JWT tokens
EOF

cat > prp/queue/feature-2.md << 'EOF'
# Data Export
CSV/JSON export for reports
EOF

# ... 3 more features ...

# Start autonomous workflow
./run-autonomous-workflow.sh

# Walk away for lunch
# Come back 2 hours later
# All 5 features implemented, tested, and committed

# Check results
git log --oneline -10
ls prp/completed/
```

---

## Troubleshooting

### "No PRPs generated"
Check `logs/prp-orchestrator-dev.log` for batch API errors.

### "Claude command not found"
Ensure Claude Code CLI is installed and in PATH.

### "Rate limit exceeded"
Wait or adjust `.env` rate limits.

### "Definition stuck in queue"
Check `prp/queue/failed/` for errors. Fix and move back to queue.

---

## Summary

**Setup**: Once (venv + API key)

**Usage**: `./run-autonomous-workflow.sh`

**Result**: Fully implemented features with tests, zero manual work

**Your Job**: Review completed code and merge to main

That's it! 🎉
