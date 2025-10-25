# Installing Autonomous PRP Workflow in Another Project

This guide shows how to add the autonomous PRP orchestration system to any project.

---

## Quick Install

```bash
# 1. Go to your project
cd /path/to/your/project

# 2. Copy the workflow system
rsync -av --exclude='venv' --exclude='batch' --exclude='logs' \
  /home/thomas/Repositories/GitWorkflow/ .

# 3. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure your API key
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env

# 5. Create required directories
mkdir -p prp/{queue,drafts,active,completed,queue/processed,queue/failed}
mkdir -p batch logs

# 6. Initialize state
echo '{"last_batch_time": null, "processed_files": [], "current_processing": null, "batch_count_1h": 0, "batch_times": []}' > logs/prp-orchestrator-state.json

# 7. Test it
./generate-prps.sh
```

Done! 🎉

---

## What Gets Copied

### Core Scripts
- `execute-prps.py` - Main orchestrator (Phases 1-5)
- `run-autonomous-workflow.sh` - Fully autonomous mode
- `generate-prps.sh` - Generate PRPs for review
- `execute-prps-from-active.sh` - Execute reviewed PRPs

### Helper Scripts
- `scripts/collect-prp-context.sh` - Context collection
- `scripts/create-batch-request.sh` - Batch request formatting
- `scripts/submit-batch.sh` - Batch API interaction

### Configuration
- `requirements.txt` - Python dependencies
- `.env.example` - Environment template
- `.gitignore` - Ignore patterns

### Documentation
- `QUICKSTART.md` - Quick start guide
- `WORKFLOW-MODES.md` - Workflow modes explanation
- `INSTALLATION.md` - This file
- `READY-FOR-E2E-TEST.md` - Test instructions

### Directory Structure
```
your-project/
├── prp/
│   ├── queue/          # Drop definitions here
│   ├── drafts/         # Draft PRPs (auto-generated)
│   ├── active/         # Ready for execution
│   ├── completed/      # Finished PRPs
│   └── QUEUE-README.md
├── batch/              # Batch API artifacts
├── logs/               # Orchestrator logs
├── scripts/            # Helper scripts
├── execute-prps.py
├── run-autonomous-workflow.sh
├── generate-prps.sh
├── execute-prps-from-active.sh
├── requirements.txt
└── .env
```

---

## Selective Install (Minimal)

If you only want the core workflow without examples:

```bash
cd /path/to/your/project

# Copy core files only
cp /home/thomas/Repositories/GitWorkflow/execute-prps.py .
cp /home/thomas/Repositories/GitWorkflow/requirements.txt .
cp /home/thomas/Repositories/GitWorkflow/*.sh .
cp -r /home/thomas/Repositories/GitWorkflow/scripts .

# Create directories
mkdir -p prp/{queue,drafts,active,completed,queue/processed,queue/failed}
mkdir -p batch logs

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo '{"last_batch_time": null, "processed_files": [], "current_processing": null, "batch_count_1h": 0, "batch_times": []}' > logs/prp-orchestrator-state.json
```

---

## Project-Specific Configuration

### 1. Update Context Collection

Edit `scripts/collect-prp-context.sh` to include project-specific info:

```bash
# Add custom sections around line 150+
# Example: Database schemas
echo ", \"database\": {"
echo "    \"schemas\": $(cat db/schema.sql | jq -Rs .)"
echo "  }"

# Example: API routes
echo ", \"api_routes\": {"
echo "    \"routes\": $(grep -r "@app.route" . | jq -Rs .)"
echo "  }"
```

### 2. Configure Rate Limits

Edit `.env` for your environment:

```bash
# Development (fast, for testing)
MAX_BATCHES_PER_HOUR=10
MIN_BATCH_INTERVAL_MINUTES=0

# Production (careful, cost-controlled)
MAX_BATCHES_PER_HOUR=1
MIN_BATCH_INTERVAL_MINUTES=60
```

### 3. Add Project Standards

Create `standards/` directory with your coding standards:

```bash
mkdir -p standards
cat > standards/coding-style.md << 'EOF'
# Project Coding Standards
- Use TypeScript strict mode
- 100% test coverage required
- ESLint + Prettier configured
- Conventional commits
EOF
```

The context collector will automatically include these in PRP generation.

---

## Multi-Environment Setup

### Development Environment

```bash
# .env.dev
ANTHROPIC_API_KEY=sk-ant-dev-key
MAX_BATCHES_PER_HOUR=10
MIN_BATCH_INTERVAL_MINUTES=0
ENVIRONMENT=dev
```

### QA Environment

```bash
# .env.qa
ANTHROPIC_API_KEY=sk-ant-qa-key
MAX_BATCHES_PER_HOUR=5
MIN_BATCH_INTERVAL_MINUTES=20
ENVIRONMENT=qa
```

### Production Environment

```bash
# .env.prod
ANTHROPIC_API_KEY=sk-ant-prod-key
MAX_BATCHES_PER_HOUR=1
MIN_BATCH_INTERVAL_MINUTES=60
ENVIRONMENT=prod
```

Use with:
```bash
cp .env.dev .env && ./run-autonomous-workflow.sh
```

---

## Integration with Existing CI/CD

### GitHub Actions

Add to `.github/workflows/prp-workflow.yml`:

```yaml
name: Autonomous PRP Workflow

on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM
  workflow_dispatch:

jobs:
  process-prps:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt

      - name: Process PRP queue
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          source venv/bin/activate
          ./run-autonomous-workflow.sh

      - name: Commit changes
        run: |
          git config user.name "PRP Bot"
          git config user.email "bot@example.com"
          git add .
          git commit -m "feat: Autonomous PRP implementation" || true
          git push
```

---

## Gitignore Updates

Add to your `.gitignore`:

```gitignore
# PRP Workflow
venv/
batch/
logs/
.env
prp/queue/failed/
prp/queue/processed/
```

---

## Testing the Installation

### 1. Verify Setup

```bash
# Check all scripts are executable
ls -lh *.sh

# Check Python dependencies
source venv/bin/activate
python -c "import dotenv; print('✓ OK')"

# Check directory structure
ls -ld prp/{queue,drafts,active,completed}
```

### 2. Run Test Definition

```bash
cat > prp/queue/test.md << 'EOF'
# Test Feature
Simple test to verify workflow is working.
Just create a function that adds two numbers.
EOF

./generate-prps.sh
```

### 3. Verify Output

```bash
# Should see PRPs in active/
ls -lh prp/active/

# Should see logs
tail logs/prp-orchestrator-dev.log
```

---

## Troubleshooting Installation

### "Module not found" errors
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Permission denied" on scripts
```bash
chmod +x *.sh
chmod +x scripts/*.sh
```

### "No API key" errors
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

### Directory structure issues
```bash
mkdir -p prp/{queue,drafts,active,completed,queue/processed,queue/failed}
mkdir -p batch logs
```

---

## Keeping Up to Date

Sync updates from the GitWorkflow repo:

```bash
# Pull latest changes
cd /home/thomas/Repositories/GitWorkflow
git pull

# Sync to your project (preserves your .env and data)
cd /path/to/your/project
rsync -av --exclude='venv' --exclude='batch' --exclude='logs' \
  --exclude='.env' --exclude='prp/queue' --exclude='prp/completed' \
  /home/thomas/Repositories/GitWorkflow/ .
```

---

## Summary

**Minimal install**: 5 commands, 2 minutes
**Full install**: Copy everything, 5 minutes
**Testing**: 1 test definition, 8 minutes
**Ready for production**: Yes!

**Need help?** See documentation:
- `QUICKSTART.md` - Usage
- `WORKFLOW-MODES.md` - Different modes
- `E2E-TEST-RESULTS.md` - Expected behavior
