# PRP Queue Directory

Drop your PRP definition files (brain dumps) here for autonomous processing.

## File Format

Files should be `.md` (Markdown) and contain:
- Feature overview
- Requirements (functional, technical, security)
- Success criteria
- Out of scope items

See `../EXAMPLE-test-feature-definition.md.disabled` for template.

## Processing

When you run `python execute-prps.py`, all `.md` files in this directory will be:
1. Collected and analyzed
2. Converted to draft PRPs via Batch API
3. Enhanced to complete PRPs via Batch API
4. Implemented via Claude Code
5. Moved to `processed/` when complete

## Enable Example

To test with the example:
```bash
# Enable example
mv EXAMPLE-test-feature-definition.md.disabled EXAMPLE-test-feature-definition.md

# Process it
python ../../execute-prps.py

# Example will be processed and moved to processed/
```

## Queue is Empty

This directory is empty on purpose. Drop your definition files here when ready.

**Rate Limits**: Check `../../.env` for current throttling settings to avoid unexpected costs.
