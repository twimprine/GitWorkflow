# PRP Definition: Autonomous Batch PRP Orchestration System

**Status**: Definition
**Created**: 2025-10-25
**Repository**: GitWorkflow
**Target Implementation**: ClaudeAgents repository

## Overview

Build an autonomous batch processing system that executes the complete PRP workflow (definition → draft → generate → execute) without human intervention. This enables teams to submit brain-dump definition files and have them automatically processed through all phases, with Claude Code executing the implementation phase autonomously.

## Business Context

**Problem**: Teams need to process multiple PRPs efficiently but the current workflow requires manual execution of each phase (/draft-prp, /generate-prp, /execute-prp) and is expensive. This creates bottlenecks and prevents batch processing.

**Solution**: Autonomous orchestration script that monitors a queue directory, processes definitions through Phases 1-2 via Anthropic Batch API, then calls Claude Code for Phase 3 (implementation).

**Value**: Teams can drop brain-dump definition files in a queue and have complete implementations ready for review without manual intervention at each phase.

## Goals

1. **Autonomous Processing**: Zero human intervention from definition submission to implementation completion
2. **Batch Capability**: Process multiple PRPs sequentially without manual triggers
3. **Operational Today**: Must be functional immediately for team use
4. **Resilient**: Handle failures gracefully, continue processing, support resume
5. **Auditable**: Comprehensive logging and state tracking

## Functional Requirements

### Phase 1-2 Automation (Script-Based via Batch API)
- Monitor `prp/queue/` directory for new definition files (brain dumps from users)
- Process each definition file:
  - Submit to Anthropic Batch API with /draft-prp prompt template
  - Wait for batch completion, retrieve draft PRP
  - Submit draft to Batch API with /generate-prp prompt template
  - Wait for completion, retrieve final PRP(s) to `prp/active/`
  - Handle atomic PRP splitting automatically (if draft >5k chars)
- Move processed definitions to `prp/queue/processed/`

### Phase 3 Automation (Claude Code Integration)
- For each PRP in `prp/active/`:
  - Launch Claude Code with `/execute-prp [prp-filename]`
  - Wait for Claude Code to complete and exit
  - Verify PRP moved to `prp/completed/`
  - Continue with next active PRP
- Support sequential execution of atomic PRPs

### Queue Management
- Directory structure:
  ```
  prp/
  ├── queue/           # Drop definition files here
  │   ├── processed/   # Successfully processed
  │   └── failed/      # Failed with error logs
  ├── drafts/          # Draft PRPs from Phase 1
  ├── active/          # Ready-to-implement PRPs from Phase 2
  └── completed/       # Completed PRPs from Phase 3
  ```
- Process in chronological order (oldest first)
- Support batch processing of multiple definitions

### State Management
- Track processing state in `logs/batch-prp-state.json`:
  ```json
  {
    "current_definition": "filename.md",
    "current_phase": "draft|generate|execute",
    "batch_id": "anthropic-batch-id",
    "started_at": "timestamp",
    "status": "processing|waiting|completed|failed"
  }
  ```
- Support resume from interruption
- Prevent duplicate processing

### Error Handling
- Log all operations to `logs/batch-prp-processing.log`
- On failure: Move problematic file to `prp/queue/failed/` with error details
- Continue processing remaining PRPs in queue
- Generate summary report at end of batch

## Technical Context

### Existing Infrastructure
- **Slash Commands**: `commands/{draft-prp.md, generate-prp.md, execute-prp.md}` in ClaudeAgents repo
- **PRP Directories**: `prp/{drafts/, active/, completed/}` structure exists
- **Helper Scripts**: `scripts/{analyze-prp-size.py, split-prp-tasks.py, validate-atomic-prp.py}`
- **Templates**: `templates/prp/{draft-prp-template.md, generate-prp-template.md, execute-prp-template.md}`

### Technology Stack
- **Orchestration**: Bash script (cross-platform compatibility)
- **API Integration**: Anthropic Batch API for Phases 1-2
- **Claude Code**: CLI integration for Phase 3 implementation
- **State Storage**: JSON files for state tracking
- **Logging**: Standard bash logging with timestamps

### Integration Points
1. **Anthropic Batch API**:
   - Submit draft-prp prompt with definition content
   - Submit generate-prp prompt with draft content
   - Poll for completion, retrieve results
   - Handle rate limits and errors

2. **Claude Code CLI**:
   - Launch with slash command: `claude /execute-prp [filename]`
   - Wait for exit signal (completion)
   - Capture output and logs

3. **File System**:
   - Monitor queue directory for new files
   - Create/move files between directories
   - Maintain state and log files

## Initial Security Considerations

### Data Sensitivity
- **PII in Definitions**: User brain dumps may contain sensitive information
- **Credentials**: API keys for Anthropic Batch API must be secured
- **Audit Trail**: Complete logging of all PRP processing for compliance

### Authentication Needs
- Secure Anthropic API key storage (environment variable or secrets manager)
- File system permissions on queue directories
- Log file access control

### Authorization Requirements
- Only authorized users can drop files in queue directory
- Script runs with appropriate file system permissions
- API key has appropriate Anthropic access level

## Initial Privacy Considerations

### PII Involved
- User brain dumps may contain customer names, emails, or other PII
- Implementation PRPs may reference specific systems or data

### Data Collection Scope
- Definition files collected in queue
- All processing logged with timestamps
- State files track current operations

### User Consent Needs
- Team members acknowledge PRP content will be processed via Anthropic API
- Logs may be retained for audit purposes

## Scope Definition

### In Scope
- Autonomous batch orchestration script
- Queue directory monitoring and management
- Anthropic Batch API integration for Phases 1-2
- Claude Code CLI integration for Phase 3
- State management and resume capability
- Comprehensive logging and error handling
- Directory structure creation
- Sample definition file
- Usage documentation

### Out of Scope
- Web UI for queue management (future enhancement)
- Real-time notifications (future enhancement)
- Multi-repository support (single repo for now)
- Distributed processing (single machine for now)
- Modifications to existing slash commands
- Changes to PRP templates

### Assumptions
- Anthropic Batch API is available and functional
- Claude Code CLI is installed and accessible
- User has valid Anthropic API key
- File system has sufficient storage for PRPs and logs
- Network connectivity for API calls

## Success Criteria

### Measurable Outcomes
1. **Throughput**: Process at least 10 PRPs sequentially without manual intervention
2. **Reliability**: 95% success rate for well-formed definitions
3. **Resume Capability**: Successfully resume after interruption at any phase
4. **Error Handling**: Failed PRPs moved to failed/ directory with clear error messages
5. **Logging**: Complete audit trail of all operations

### Performance Targets
- Queue monitoring: Check every 60 seconds
- Phase 1-2 processing: Complete within Batch API SLA (typically minutes to hours)
- Phase 3 execution: Depends on PRP complexity (no timeout enforced)
- State file updates: Within 1 second of phase transitions

### Quality Metrics
- Zero data loss (all definitions tracked)
- 100% state consistency (state file always accurate)
- Complete error logging (all failures documented)
- Idempotent operations (safe to re-run)

## Questions for Review

### Clarifications Needed
1. Should the script run as a daemon (continuous monitoring) or cron job (periodic)?
2. What should happen if Claude Code fails during /execute-prp? Retry? Manual intervention?
3. Should atomic PRPs be executed sequentially or can they run in parallel?
4. What is the maximum queue depth before we alert/pause processing?

### Design Decisions Required
1. **Batch API vs Claude Code for Phases 1-2**: Use Batch API (cheaper, async) or Claude Code CLI? Batch
2. **State Storage**: JSON file vs SQLite database for better querying? JSON file for simplicity
3. **Notification**: Email/Slack on completion or just logs? logs
4. **Concurrency**: Process one definition at a time or support parallel processing? Support parallel processing in future - needs dependency management first.

### Risk Assessments Needed
1. **API Rate Limits**: How many batch submissions can we make per hour/day? start 1/hr
2. **Failure Recovery**: What happens if script crashes mid-processing?
3. **Disk Space**: How much storage needed for large batch processing?
4. **Long-Running**: Should we have timeout limits for Phase 3 (execute-prp)?

## User Stories

### User Experience
- **As a developer**, I want to drop a brain-dump definition file in a queue directory so that I can continue with other work while the PRP is automatically processed through all phases
- **User workflow**:
  1. Create definition file with brain dump of feature requirements
  2. Drop file in `prp/queue/` directory
  3. Monitor logs or wait for completion notification
  4. Review completed implementation in `prp/completed/`
- **Acceptance criteria**:
  - Definition file automatically detected
  - All phases complete without manual intervention
  - Clear error messages if processing fails
  - Completed PRPs ready for review

### Admin Experience
- **As an admin**, I need to monitor batch processing status to ensure the system is healthy and catch failures early
- **Admin workflows**:
  - Check status: `./scripts/batch-process-prps.sh --status`
  - View logs: `tail -f logs/batch-prp-processing.log`
  - Retry failed: Move from `failed/` back to `queue/`
  - Emergency stop: `./scripts/batch-process-prps.sh --stop`
- **Management requirements**:
  - Real-time status reporting
  - Log rotation and archival
  - Alert on repeated failures

### Auditor Experience
- **As an auditor**, I must verify that all PRP processing is logged and traceable to ensure compliance with development standards
- **Audit trail requirements**:
  - Every definition tracked from submission to completion
  - All API calls logged with timestamps
  - State transitions documented
  - Error conditions captured with root cause
- **Compliance checkpoints**:
  - No PII in logs
  - Secure API key handling
  - Complete audit trail

### Customer Experience
- **As a customer**, I expect features to be delivered reliably when using the automated PRP process
- **Service impact**:
  - Faster feature delivery through automation
  - More consistent quality through standardized workflow
  - Reduced human error in PRP processing
- **Support requirements**:
  - Clear documentation for submitting definitions
  - Status visibility for submitted PRPs
  - Error messages that guide corrective action

### 3rd Party Experience (DevOps/Platform Team)
- **As a platform engineer**, I need the batch processing system to integrate with our CI/CD pipeline and monitoring infrastructure
- **External integration**:
  - Prometheus metrics endpoint for monitoring
  - Webhook support for notifications
  - API for programmatic queue submission
- **Communication needs**:
  - Status updates via webhook
  - Failure alerts via monitoring system
  - Completion notifications

## Stakeholder Impact Analysis

### Internal Stakeholders
- **Development Team**: Faster PRP processing, less manual work, focus on implementation review
- **Operations Team**: New system to monitor and maintain, requires runbook and alerting setup
- **Security Team**: Need to audit Anthropic API usage, ensure secure credential handling
- **Compliance Team**: Requires audit trail documentation and retention policy
- **Product Team**: Faster feature delivery, better capacity planning with batch processing

### External Stakeholders
- **Customer Communication**: Faster feature delivery timeline
- **Partner Integration**: Automated PRP processing for partner-requested features
- **Regulatory Bodies**: Must demonstrate controlled, auditable development process

## Implementation Approach

### Phase 1: Core Orchestration Script
- Create `scripts/batch-process-prps.sh` with:
  - Queue monitoring loop
  - File processing state machine
  - Anthropic Batch API integration
  - Error handling and logging

### Phase 2: Claude Code Integration
- Implement Phase 3 execution:
  - Call Claude Code CLI with /execute-prp
  - Wait for completion signal
  - Verify output and move to completed/

### Phase 3: Testing and Documentation
- Create sample definition file
- End-to-end test with real PRP
- Write usage documentation
- Create operational runbook

## Dependencies

- **Anthropic API Key**: Required for Batch API access
- **Claude Code CLI**: Must be installed and accessible
- **ClaudeAgents Repository**: Contains slash commands and templates
- **Python 3.x**: For helper scripts (analyze-prp-size.py, etc.)
- **jq**: For JSON parsing in bash
- **curl**: For API calls

## Next Steps

1. Review this definition for completeness and accuracy
2. Create `/draft-prp` from this definition
3. Generate comprehensive PRP with `/generate-prp`
4. Execute implementation with `/execute-prp`
5. Deploy and test with real PRP workloads
