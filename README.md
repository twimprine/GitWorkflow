# Autonomous PRP Batch Orchestrator

**Status**: Design & Reference Implementation

This repository contains the **design documentation and reference implementation** for an autonomous PRP batch orchestrator. The actual production implementation will be done through the ClaudeAgents PRP process.

## What's in This Repo

- ✅ **PRP Definition**: Complete requirements for the orchestrator
- ✅ **Reference Implementation**: Working prototype (`execute-prps.py`)
- ✅ **Helper Scripts**: Batch API integration scripts
- ✅ **Documentation**: Setup and usage guides
- ❌ **No Git Remote**: Currently local-only repository
- ⚠️ **Queue is Empty**: Safe to run without processing anything

Process Product Requirements Proposals (PRPs) autonomously from brain-dump definitions to complete implementations using Anthropic Batch API and Claude Code.

## ⚡ Quick Actions

### Submit to ClaudeAgents for Production Implementation

```bash
# Copy definition to ClaudeAgents queue
./submit-to-claudeagents.sh

# Then follow PRP process in ClaudeAgents repo
cd ~/Repositories/ClaudeAgents
# Use /draft-prp, /generate-prp, /execute-prp commands
```

### Test Prototype Locally (Optional)

```bash
# It's safe to run - queue is empty!
python execute-prps.py --status

# To test with example:
cd prp/queue
mv EXAMPLE-test-feature-definition.md.disabled EXAMPLE-test-feature-definition.md
cd ../..
python execute-prps.py
```

## Quick Start (Prototype Testing)

### 1. Setup

```bash
# Clone or navigate to repository
cd GitWorkflow

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Make scripts executable
chmod +x scripts/*.sh
```

### 2. Run

```bash
# Activate your environment
source venv/bin/activate  # or your env activation command

# Process all PRPs in queue (one-time)
python execute-prps.py

# Or run in daemon mode (continuous monitoring)
python execute-prps.py --daemon

# Check status
python execute-prps.py --status
```

### 3. Submit PRPs

Drop brain-dump definition files in `prp/queue/`:

```bash
# Create a definition file
cat > prp/queue/my-feature-definition.md <<'EOF'
# Feature: User Authentication

Add OAuth2 login with Google and GitHub providers.

Requirements:
- Secure token storage
- Session management
- User profile sync
- 2FA support

...
EOF

# The orchestrator will automatically:
# 1. Create draft PRP
# 2. Generate complete PRP(s)
# 3. Execute implementation via Claude Code
# 4. Move completed to prp/completed/
```

## How It Works

### Workflow

```
Definition → Draft → Generate → Execute → Complete
   (You)    (Batch)  (Batch)   (Claude)   (Done)
```

1. **Definition Phase** (Human): Drop brain-dump `.md` file in `prp/queue/`
2. **Draft Phase** (Batch API): Converts definition to structured draft PRP
3. **Generate Phase** (Batch API): Creates comprehensive implementation-ready PRP
4. **Execute Phase** (Claude Code): Implements PRP with full TDD workflow
5. **Complete**: Results in `prp/completed/`, definition moved to `prp/queue/processed/`

### Directory Structure

```
GitWorkflow/
├── execute-prps.py              # Main orchestrator
├── .env                          # Your configuration (API keys, rate limits)
├── scripts/
│   ├── collect-prp-context.sh   # Gather project context
│   ├── create-batch-request.sh  # Format batch API requests
│   └── submit-batch.sh          # Submit and monitor batches
├── prp/
│   ├── queue/                   # Drop definitions here
│   │   ├── processed/           # Successfully processed
│   │   └── failed/              # Failed with error logs
│   ├── drafts/                  # Draft PRPs (Phase 1 output)
│   ├── active/                  # Ready-to-implement PRPs (Phase 2 output)
│   └── completed/               # Completed implementations (Phase 3 output)
├── batch/                       # Batch API intermediate files
└── logs/                        # Orchestrator logs and state
```

## Configuration

Edit `.env` to customize:

```bash
# API Key (REQUIRED)
ANTHROPIC_API_KEY=your-key-here

# Environment (optional)
ENVIRONMENT=dev  # dev, qa, or prod

# Rate Limiting (adjust to budget)
MAX_BATCHES_PER_HOUR=1            # Conservative default
MIN_BATCH_INTERVAL_MINUTES=60     # Minimum time between batches

# Polling Intervals
QUEUE_CHECK_INTERVAL_SECONDS=300  # Check queue every 5 min
BATCH_POLL_INTERVAL_SECONDS=60    # Check batch status every 1 min
BATCH_TIMEOUT_HOURS=3             # Max batch wait time
```

### Per-Environment Configuration

Each environment (prod/qa/dev) should have its own API key and rate limits:

**Development:**
```bash
ENVIRONMENT=dev
ANTHROPIC_API_KEY=sk-ant-dev-...
MAX_BATCHES_PER_HOUR=10
MIN_BATCH_INTERVAL_MINUTES=10
```

**QA:**
```bash
ENVIRONMENT=qa
ANTHROPIC_API_KEY=sk-ant-qa-...
MAX_BATCHES_PER_HOUR=5
MIN_BATCH_INTERVAL_MINUTES=20
```

**Production:**
```bash
ENVIRONMENT=prod
ANTHROPIC_API_KEY=sk-ant-prod-...
MAX_BATCHES_PER_HOUR=2
MIN_BATCH_INTERVAL_MINUTES=45
```

## Usage Examples

### One-Time Processing

```bash
# Process all queued definitions once
python execute-prps.py
```

### Continuous Monitoring

```bash
# Run as daemon (monitors queue continuously)
python execute-prps.py --daemon

# Use with systemd or supervisor for production
```

### Status Check

```bash
$ python execute-prps.py --status

=== PRP Orchestrator Status ===
Queue directory: /path/to/prp/queue
Queued: 3 files
Processed: 15 files
Current: None
Last batch: 2025-10-25T14:30:00Z
Batches (1h): 1
Can submit: False (Minimum interval: Wait 45 minutes since last batch.)
```

## Cost Control

The orchestrator includes built-in rate limiting to prevent unexpected costs:

1. **Hourly Limits**: Max batches per hour (default: 1)
2. **Minimum Intervals**: Min time between batches (default: 60 min)
3. **Automatic Throttling**: Waits if rate limits would be exceeded
4. **State Tracking**: Remembers batch history across restarts

### Adjusting Rate Limits

For higher throughput (adjust in `.env`):

```bash
MAX_BATCHES_PER_HOUR=5       # Up to 5 batches per hour
MIN_BATCH_INTERVAL_MINUTES=15 # Min 15 min between batches
```

For cost savings (more conservative):

```bash
MAX_BATCHES_PER_HOUR=1        # Only 1 batch per hour
MIN_BATCH_INTERVAL_MINUTES=120 # Wait 2 hours between batches
```

## Troubleshooting

### API Key Not Set

```
Error: ANTHROPIC_API_KEY not set! Create .env file with your API key.
```

**Solution**: Copy `.env.example` to `.env` and add your API key.

### Rate Limit Reached

```
Rate limit: 1 batches in last hour. Wait 45 minutes.
```

**Solution**: Either wait or increase `MAX_BATCHES_PER_HOUR` in `.env` (costs will increase).

### Script Not Found

```
Error: Script not found: /path/to/scripts/collect-prp-context.sh
```

**Solution**: Ensure all scripts are executable:
```bash
chmod +x scripts/*.sh
```

### Batch Timeout

```
Error: Timeout waiting for batch completion
```

**Solution**: Increase `BATCH_TIMEOUT_HOURS` in `.env` or check Anthropic API status.

### Failed Definitions

Check `prp/queue/failed/` directory:

```bash
# View error log
cat prp/queue/failed/my-feature-error.txt

# Retry: move back to queue
mv prp/queue/failed/my-feature-definition.md prp/queue/
```

## Logs

All operations are logged:

```bash
# View orchestrator log
tail -f logs/prp-orchestrator-dev.log

# View batch API responses
cat batch/*/batch-status.json

# View state file
cat logs/prp-orchestrator-state.json
```

## Integration with ClaudeAgents

This orchestrator is designed to work with the ClaudeAgents repository:

1. **Slash Commands**: Uses `/draft-prp` and `/generate-prp` prompts
2. **Templates**: Follows PRP templates from `templates/prp/`
3. **Execute**: Calls Claude Code with `/execute-prp` for implementation
4. **Standards**: Respects all project standards and TDD requirements

##Dependencies

- Python 3.8+
- python-dotenv
- jq (system package for JSON processing)
- curl
- Claude Code CLI
- Anthropic API key

Install Python dependencies:
```bash
pip install -r requirements.txt
```

## License

Proprietary - For internal use only.

## Support

For issues or questions:
1. Check logs in `logs/prp-orchestrator-dev.log`
2. Review failed PRPs in `prp/queue/failed/`
3. Run status check: `python execute-prps.py --status`
4. Open issue with log excerpts if needed
