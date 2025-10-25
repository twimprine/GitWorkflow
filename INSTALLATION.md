# Installing Autonomous PRP Workflow in Another Project

This guide shows how to add the autonomous PRP orchestration system to any project.

---

## Prerequisites

Before installing, ensure you have:

### System Requirements
```bash
# Debian/Ubuntu
sudo apt-get install jq curl tree git

# macOS
brew install jq curl tree git

# Verify installations
jq --version      # Should be 1.6+
curl --version    # Any recent version
python3 --version # Should be 3.8+
```

### Claude Code CLI
Install Claude Code from: https://docs.claude.com/en/docs/claude-code

```bash
# Verify Claude CLI is installed
which claude
claude --version
```

### Python Environment
- Python 3.8 or higher
- pip package manager
- Virtual environment support

---

## Quick Install

```bash
# Define source repository location
SOURCE_REPO="/path/to/GitWorkflow"  # UPDATE THIS PATH

# 1. Go to your project
cd /path/to/your/project

# 2. Backup existing files (if they exist)
[[ -f requirements.txt ]] && cp requirements.txt requirements.txt.backup
[[ -f .gitignore ]] && cp .gitignore .gitignore.backup

# 3. Copy the workflow system (preserves prp/ structure, excludes data)
rsync -av \
  --exclude='venv' \
  --exclude='batch' \
  --exclude='logs' \
  --exclude='prp/queue/*' \
  --exclude='prp/drafts/*' \
  --exclude='prp/active/*' \
  --exclude='prp/completed/*' \
  --exclude='.env' \
  "$SOURCE_REPO/" .

# 4. Merge requirements.txt (if your project already has one)
if [[ -f requirements.txt.backup ]]; then
  echo "⚠️  Merging requirements.txt with existing file..."
  cat "$SOURCE_REPO/requirements.txt" >> requirements.txt
  echo "Review requirements.txt for duplicates"
else
  cp "$SOURCE_REPO/requirements.txt" requirements.txt
fi

# 5. Merge .gitignore (if your project already has one)
if [[ -f .gitignore.backup ]]; then
  echo "⚠️  Merging .gitignore with existing file..."
  cat "$SOURCE_REPO/.gitignore" >> .gitignore
  echo "Review .gitignore for duplicates"
fi

# 6. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 7. Configure your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
echo "⚠️  IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY"

# 8. Create required directories
mkdir -p prp/{queue,drafts,active,completed,queue/processed,queue/failed}
mkdir -p batch logs

# 9. Initialize state
echo '{"last_batch_time": null, "processed_files": [], "current_processing": null, "batch_count_1h": 0, "batch_times": []}' > logs/prp-orchestrator-state.json

# 10. Test it
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
- `.env.example` - Environment template (copy to .env)
- `.gitignore` - Ignore patterns (merge with existing)

### Documentation
- `QUICKSTART.md` - Quick start guide
- `WORKFLOW-MODES.md` - Workflow modes explanation
- `INSTALLATION.md` - This file
- `README.md` - Project overview

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
├── .env               # Your configuration (copy from .env.example)
└── .gitignore
```

---

## Selective Install (Minimal)

If you only want the core workflow without examples:

```bash
cd /path/to/your/project

# Define source
SOURCE_REPO="/path/to/GitWorkflow"  # UPDATE THIS PATH

# Copy core files only
cp "$SOURCE_REPO/execute-prps.py" .
cp "$SOURCE_REPO"/*.sh .
cp -r "$SOURCE_REPO/scripts" .

# Copy configuration templates
cp "$SOURCE_REPO/requirements.txt" .
cp "$SOURCE_REPO/.env.example" .

# Create directories
mkdir -p prp/{queue,drafts,active,completed,queue/processed,queue/failed}
mkdir -p batch logs

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Initialize state
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

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y jq curl tree

      - name: Install Python dependencies
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

**Important**: If your project already has a `.gitignore`, merge these patterns:

```gitignore
# PRP Workflow
venv/
batch/
logs/
.env
prp/queue/failed/
prp/queue/processed/
prp/drafts/*
prp/active/*
prp/completed/*

# Keep structure files
!prp/drafts/.gitkeep
!prp/active/.gitkeep
!prp/completed/.gitkeep
```

---

## Testing the Installation

### 1. Verify Setup

```bash
# Check all scripts are executable
ls -lh *.sh

# Check Python dependencies
source venv/bin/activate
python -c "import dotenv; print('✓ python-dotenv OK')"

# Check system dependencies
jq --version && echo "✓ jq OK"
curl --version && echo "✓ curl OK"
tree --version && echo "✓ tree OK"
which claude && echo "✓ Claude Code CLI OK"

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
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY=sk-ant-...
```

### "Command not found: jq/curl/tree"
```bash
# Debian/Ubuntu
sudo apt-get install jq curl tree

# macOS
brew install jq curl tree
```

### "Command not found: claude"
Install Claude Code CLI from: https://docs.claude.com/en/docs/claude-code

### Directory structure issues
```bash
mkdir -p prp/{queue,drafts,active,completed,queue/processed,queue/failed}
mkdir -p batch logs
```

### Existing files conflict
```bash
# Review backup files
diff requirements.txt requirements.txt.backup
diff .gitignore .gitignore.backup

# Manually merge as needed
```

---

## Rollback Instructions

If installation causes issues:

```bash
# 1. Restore backed up files
[[ -f requirements.txt.backup ]] && mv requirements.txt.backup requirements.txt
[[ -f .gitignore.backup ]] && mv .gitignore.backup .gitignore

# 2. Remove workflow files
rm -f execute-prps.py *.sh
rm -rf scripts/collect-prp-context.sh scripts/create-batch-request.sh scripts/submit-batch.sh
rm -f .env.example

# 3. Remove directories (if empty)
rmdir prp/{queue/processed,queue/failed,queue,drafts,active,completed} 2>/dev/null
rmdir batch logs 2>/dev/null

# 4. Remove Python environment
rm -rf venv/

# 5. Check git status
git status
```

---

## Keeping Up to Date

Sync updates from the GitWorkflow repo:

```bash
# Define source
SOURCE_REPO="/path/to/GitWorkflow"  # UPDATE THIS PATH

# Pull latest changes from source
cd "$SOURCE_REPO"
git pull

# Sync to your project (preserves your .env and data)
cd /path/to/your/project
rsync -av \
  --exclude='venv' \
  --exclude='batch' \
  --exclude='logs' \
  --exclude='.env' \
  --exclude='prp/queue/*' \
  --exclude='prp/drafts/*' \
  --exclude='prp/active/*' \
  --exclude='prp/completed/*' \
  "$SOURCE_REPO/" .

# Reinstall dependencies if requirements.txt changed
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

---

## Summary

**Minimal install**: 10 commands, 5 minutes
**Full install**: Copy everything, 10 minutes
**Testing**: 1 test definition, 8 minutes
**Ready for production**: Yes!

**Need help?** See documentation:
- `QUICKSTART.md` - Usage guide
- `WORKFLOW-MODES.md` - Different workflow modes
- `README.md` - System overview
- `PRP_Process.md` - PRP workflow documentation

---

## Safety Checklist for Production Projects

Before installing in OrgCash, AWS_Environments, or other production projects:

- [ ] Backed up existing `requirements.txt`
- [ ] Backed up existing `.gitignore`
- [ ] Verified Python 3.8+ available
- [ ] Installed system dependencies (jq, curl, tree)
- [ ] Installed Claude Code CLI
- [ ] Reviewed `.env.example` and configured `.env`
- [ ] Tested in development environment first
- [ ] Have rollback plan ready
- [ ] Know where to check logs (`logs/prp-orchestrator-dev.log`)
