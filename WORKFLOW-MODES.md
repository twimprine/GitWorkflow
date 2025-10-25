# PRP Workflow Modes

This system supports **three workflow modes** to match your trust level and project requirements.

---

## Mode 1: Fully Autonomous (AFK Mode) ☕

**Use when**: You trust the system completely and want zero manual intervention.

**Command**:
```bash
./run-autonomous-workflow.sh
```

**What happens**:
```
prp/queue/definition.md
  ↓ (auto - 8min)
prp/drafts/draft.md
  ↓ (auto)
prp/active/PRP-001.md, PRP-002.md, PRP-003.md
  ↓ (auto - varies)
prp/completed/COMPLETE-PRP-001.md, etc.
  ↓ (auto)
prp/queue/processed/definition.md
```

**You can**: Walk away completely. Come back to completed features.

**Cost**: ~$0.13 per definition + Claude Code usage

---

## Mode 2: Review-First (Controlled Mode) 👀

**Use when**: You want to review PRPs before implementation (new projects, critical features).

### Step 1: Generate PRPs for Review

```bash
./generate-prps.sh
```

**What happens**:
```
prp/queue/definition.md
  ↓ (auto - 8min)
prp/drafts/draft.md
  ↓ (auto)
prp/active/PRP-001.md, PRP-002.md, PRP-003.md
  ↓ (STOPS HERE)
```

**You review**: Read PRPs in `prp/active/`, make any adjustments.

### Step 2: Execute Reviewed PRPs

```bash
./execute-prps-from-active.sh
```

Confirms before executing, then runs all PRPs in sequence.

**What happens**:
```
prp/active/PRP-001.md  [you reviewed this]
  ↓ (manual trigger)
prp/completed/COMPLETE-PRP-001.md
```

**Cost**: Same as Mode 1, just split into 2 steps

---

## Mode 3: Manual Everything (Full Control) 🎮

**Use when**: Learning the system, testing, or maximum control needed.

### Generate Draft Only

```bash
# 1. Run orchestrator with rate limits disabled
source venv/bin/activate
export MAX_BATCHES_PER_HOUR=10
export MIN_BATCH_INTERVAL_MINUTES=0

# 2. Generate just the draft
python execute-prps.py  # Stops after draft creation

# 3. Review draft in prp/drafts/

# 4. Run again to generate final PRPs
python execute-prps.py  # Generates from draft

# 5. Review PRPs in prp/active/

# 6. Execute specific PRP
/execute-prp PRP-NAME-001
```

**Cost**: Same, but you control each step

---

## Comparison Table

| Feature | Mode 1 (Autonomous) | Mode 2 (Review-First) | Mode 3 (Manual) |
|---------|-------------------|---------------------|----------------|
| **Commands** | 1 | 2 | Many |
| **Review Points** | 0 | 1 (before exec) | Multiple |
| **Time Required** | 0 (AFK) | 5-10min review | Full attention |
| **Risk** | Medium | Low | Lowest |
| **Throughput** | Highest | High | Medium |
| **Best For** | Trusted features | New projects | Testing/learning |

---

## Recommended Workflow by Project Stage

### New Project (First 1-2 Features)
**Use Mode 2** (Review-First)
- Generate PRPs → Review → Execute
- Learn what the system generates
- Build trust

### Established Project (Feature 3+)
**Use Mode 1** (Autonomous)
- Drop definitions, walk away
- Review completed code before merge
- Maximum efficiency

### Critical Features (Security/Money)
**Use Mode 2** (Review-First)
- Always review PRPs before execution
- Verify test coverage requirements
- Double-check security controls

### Debugging/Testing
**Use Mode 3** (Manual)
- Step through each phase
- Inspect intermediate outputs
- Troubleshoot issues

---

## Daily Workflow Example (Review-First)

### Morning (Start of Day)

```bash
# 1. Drop all feature definitions in queue
cat > prp/queue/feature-1.md << 'EOF'
[Feature description...]
EOF

cat > prp/queue/feature-2.md << 'EOF'
[Feature description...]
EOF

# 2. Generate all PRPs
./generate-prps.sh

# Walk away for coffee while batch API processes (~8min per definition)
```

### Mid-Morning (Review)

```bash
# 3. Review generated PRPs
ls prp/active/
cat prp/active/PRP-FEATURE-1-a-001-*.md

# Make any adjustments if needed
vim prp/active/PRP-FEATURE-1-a-001-core.md

# 4. Execute all reviewed PRPs
./execute-prps-from-active.sh
# Confirms: "Execute these PRPs? [y/N]" → y

# Now walk away again - Claude Code implements everything
```

### End of Day (Review Code)

```bash
# 5. Review completed implementations
ls prp/completed/
git log --oneline -10
git diff main

# 6. Merge to main if satisfied
git push
```

**Total hands-on time**: ~10-15 minutes (just reviews)

---

## Advanced: Hybrid Workflow

Mix modes based on feature criticality:

```bash
# High-priority, simple features → Autonomous
./run-autonomous-workflow.sh  # Queue: feature-1.md, feature-2.md

# Critical security feature → Review-First
./generate-prps.sh            # Queue: auth-feature.md
# [Review PRPs carefully]
./execute-prps-from-active.sh
```

---

## Switching Modes Mid-Stream

### From Autonomous to Review-First

If autonomous workflow is running and you want to stop:

```bash
# 1. Kill the autonomous script (Ctrl+C)

# 2. PRPs already in prp/active/ can be reviewed

# 3. Execute manually when ready
./execute-prps-from-active.sh
```

### From Review-First to Autonomous

After reviewing some PRPs, execute the rest autonomously:

```bash
# 1. Review and approve specific PRPs
# 2. Run autonomous script for remaining work
./run-autonomous-workflow.sh
```

---

## Summary

**Choose Your Mode**:

1. 🚀 **Trust the system?** → `./run-autonomous-workflow.sh`
2. 👀 **Want to review first?** → `./generate-prps.sh` → review → `./execute-prps-from-active.sh`
3. 🎮 **Need full control?** → Manual step-by-step

All modes are **production-ready**. Pick what fits your comfort level and project needs.
