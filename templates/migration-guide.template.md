# Migration Guide: [Hook Name] v[OLD] to v[NEW]

## Overview

This guide helps you migrate from [Hook Name] version [OLD] to version [NEW].

**Migration Urgency**: [LOW | MEDIUM | HIGH | CRITICAL]
**Estimated Time**: [X minutes/hours]
**Backward Compatible**: [YES | NO | PARTIAL]

## Breaking Changes Summary

| Change | Impact | Required Action |
|--------|--------|-----------------|
| Example: Removed `--legacy` flag | Scripts using this flag will fail | Replace with `--compatibility-mode` |
| Example: Changed output format | Parsers expecting JSON will fail | Update parsers for YAML |
| Example: New required parameter | Hook calls missing parameter will fail | Add `context` parameter |

## Prerequisites

Before starting the migration:

- [ ] Backup current hook configuration
- [ ] Review current hook usage in your workflows
- [ ] Ensure test environment is available
- [ ] Have rollback plan ready
- [ ] Review new version requirements

### System Requirements

- **Old Version Requirements**:
  - Bash 4.0+
  - Python 3.7+
  - Git 2.0+

- **New Version Requirements**:
  - Bash 4.0+ (unchanged)
  - Python 3.8+ (⚠️ upgraded)
  - Git 2.0+ (unchanged)
  - jq 1.5+ (⚠️ new requirement)

## Step-by-Step Migration

### Step 1: Analyze Current Usage

```bash
# Find all hook invocations in your codebase
grep -r "[hook-name]" --include="*.sh" --include="*.yaml" .

# List current configuration
cat ~/.claude/hooks/config.yaml | grep "[hook-name]"

# Check version
./hooks/core/version-check.sh validate "[hook-name]" "[current-version]"
```

### Step 2: Update Hook Configuration

#### Old Configuration (v[OLD])
```yaml
hooks:
  example-hook:
    version: "[OLD]"
    enabled: true
    config:
      timeout: 30
      format: "json"
      legacy_mode: true
```

#### New Configuration (v[NEW])
```yaml
hooks:
  example-hook:
    version: "[NEW]"
    enabled: true
    config:
      timeout: 60           # Changed: increased default
      output_format: "yaml" # Changed: renamed from 'format'
      compatibility_mode: true # Changed: renamed from 'legacy_mode'
      context:             # New: required context object
        environment: "production"
        trace_id: "${TRACE_ID}"
```

### Step 3: Update Hook Invocations

#### Example 1: Direct Invocation

**Old Code (v[OLD])**:
```bash
# Direct call with old parameters
./hooks/example-hook --legacy --format=json process "$data"
```

**New Code (v[NEW])**:
```bash
# Updated call with new parameters
./hooks/example-hook \
  --compatibility-mode \
  --output-format=yaml \
  process "$data" \
  --context='{"environment":"production"}'
```

#### Example 2: Pipeline Integration

**Old Pipeline (v[OLD])**:
```yaml
steps:
  - name: Run Hook
    run: |
      hooks/example-hook validate --legacy
```

**New Pipeline (v[NEW])**:
```yaml
steps:
  - name: Run Hook
    run: |
      hooks/example-hook validate \
        --compatibility-mode \
        --context="${{ env.CONTEXT_JSON }}"
```

### Step 4: Update Output Parsers

#### Parsing Old JSON Output
```python
# Old: Expecting JSON
import json

output = run_hook()
data = json.loads(output)
result = data['status']
```

#### Parsing New YAML Output
```python
# New: Expecting YAML
import yaml

output = run_hook()
data = yaml.safe_load(output)
result = data['status']

# For backward compatibility:
try:
    data = yaml.safe_load(output)
except yaml.YAMLError:
    # Fallback to JSON for old format
    import json
    data = json.loads(output)
```

### Step 5: Test Migration

```bash
# Run migration validation script
./scripts/validate-migration.sh "[hook-name]" "[OLD]" "[NEW]"

# Test with sample data
./hooks/[hook-name] --version  # Should show [NEW]
./hooks/[hook-name] validate --test-mode

# Run integration tests
pytest tests/hooks/test_[hook-name].py -v

# Verify backward compatibility (if applicable)
./hooks/[hook-name] --compatibility-mode process "$legacy_data"
```

### Step 6: Gradual Rollout

#### Phase 1: Parallel Running (Week 1-2)
```bash
# Run both versions in parallel, compare outputs
./scripts/parallel-run.sh "[hook-name]" "[OLD]" "[NEW]"
```

#### Phase 2: Canary Deployment (Week 3-4)
```yaml
# Route 10% traffic to new version
deployment:
  canary:
    enabled: true
    percentage: 10
    version: "[NEW]"
```

#### Phase 3: Full Migration (Week 5)
```bash
# Switch all traffic to new version
./scripts/switch-version.sh "[hook-name]" "[NEW]"
```

## Rollback Procedure

If issues arise during migration:

### Immediate Rollback
```bash
# Revert to previous version
./scripts/rollback-hook.sh "[hook-name]" "[OLD]"

# Verify rollback
./hooks/core/version-check.sh validate "[hook-name]" "[OLD]"
```

### Rollback Checklist
- [ ] Stop new version deployment
- [ ] Restore old hook version
- [ ] Revert configuration changes
- [ ] Clear caches if applicable
- [ ] Notify team of rollback
- [ ] Document issues encountered

## Common Issues and Solutions

### Issue 1: Missing Required Parameter
**Error**: `Error: Required parameter 'context' is missing`

**Solution**:
```bash
# Add default context if not provided
export HOOK_CONTEXT='{"environment":"production","user":"system"}'
```

### Issue 2: Output Format Mismatch
**Error**: `ParseError: Expecting value: line 1 column 1`

**Solution**:
```bash
# Use compatibility mode for transition period
./hooks/[hook-name] --compatibility-mode --output-format=json
```

### Issue 3: Version Conflict
**Error**: `Version 1.0.0 is below minimum supported version 2.0.0`

**Solution**:
```bash
# Update hook to minimum version
./scripts/update-hook.sh "[hook-name]" "[NEW]"
```

### Issue 4: Dependency Missing
**Error**: `Command 'jq' not found`

**Solution**:
```bash
# Install missing dependency
apt-get update && apt-get install -y jq  # Debian/Ubuntu
brew install jq                           # macOS
```

## Validation Checklist

Before considering migration complete:

### Pre-Migration
- [ ] All dependencies installed
- [ ] Backup created
- [ ] Test environment ready
- [ ] Team notified

### During Migration
- [ ] Configuration updated
- [ ] Code changes applied
- [ ] Tests passing
- [ ] Performance acceptable

### Post-Migration
- [ ] All workflows functional
- [ ] No errors in logs
- [ ] Performance metrics normal
- [ ] Documentation updated
- [ ] Team trained on changes

## Performance Comparison

| Metric | v[OLD] | v[NEW] | Change |
|--------|--------|--------|---------|
| Startup Time | 50ms | 35ms | -30% ✅ |
| Memory Usage | 25MB | 20MB | -20% ✅ |
| Processing Time | 100ms | 80ms | -20% ✅ |
| CPU Usage | 15% | 12% | -20% ✅ |

## Support and Resources

### Documentation
- [New Version Documentation](docs/v[NEW]/)
- [API Reference](docs/api/v[NEW]/)
- [FAQ](docs/faq.md)

### Getting Help
- GitHub Issues: [Project Issues](https://github.com/project/issues)
- Slack Channel: #hook-migration
- Email Support: hooks-support@example.com

### Deprecation Timeline
- **v[OLD] Deprecation Date**: 2025-06-01
- **v[OLD] Warning Period**: 2025-06-01 to 2025-12-01
- **v[OLD] End of Support**: 2025-12-31

## Migration Scripts

### Automated Migration Script
```bash
#!/bin/bash
# Save as: migrate-hook.sh

HOOK_NAME="[hook-name]"
OLD_VERSION="[OLD]"
NEW_VERSION="[NEW]"

echo "Starting migration of $HOOK_NAME from $OLD_VERSION to $NEW_VERSION"

# Step 1: Backup
echo "Creating backup..."
cp -r hooks/$HOOK_NAME hooks/${HOOK_NAME}.backup.$(date +%Y%m%d)

# Step 2: Update version
echo "Updating version..."
sed -i "s/version: $OLD_VERSION/version: $NEW_VERSION/g" hooks/registry/versions.json

# Step 3: Update configuration
echo "Updating configuration..."
# Add your configuration updates here

# Step 4: Test
echo "Running tests..."
./hooks/core/version-check.sh validate "$HOOK_NAME" "$NEW_VERSION"

echo "Migration complete!"
```

## Appendix: Changed APIs

### Removed APIs
- `process_legacy()` - Use `process()` instead
- `--legacy` flag - Use `--compatibility-mode` instead

### Changed APIs
- `format` → `output_format`
- `timeout: 30` → `timeout: 60` (default change)

### New Required APIs
- `context` parameter in all function calls
- `--metrics` flag for performance monitoring

---

**Last Updated**: [DATE]
**Version**: [NEW]
**Migration Guide Version**: 1.0.0