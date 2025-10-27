---
allowed-tools: Task, Read, Grep, Glob
argument-hint: [feature description]
description: Create a rough draft PRP for initial review
---

Create a rough draft PRP for initial review: $ARGUMENTS

**Purpose**: Quick requirements capture for "$ARGUMENTS"

**Process**: This is a lightweight first pass focusing on functionality and context without running extensive validation checks.

**Output**: Draft PRP saved to `./prp/drafts/` ready for `/generate-prp` enhancement.

Follow methodology in `templates/prp/draft-prp-template.md`.

## Process

This command quickly drafts a PRP focusing on:
- Core functionality description
- Basic requirements gathering
- Initial context and scope
- High-level security/privacy considerations
- Life-critical development considerations (when applicable)
- Task decomposition and breakdown for complex features

### Implementation Steps

1. **Create Draft**: Generate draft PRP following the template below
2. **Save Draft**: Write to `./prp/drafts/[###]-[a]-[feature-desc]-[timestamp].md`
3. **Analyze Size**: Call python-developer agent to analyze draft size
   - Use `scripts/prp/analyze-prp-size.py` (when available)
   - Count total characters (markdown, code, whitespace)
   - Identify section sizes and boundaries
4. **Generate Report**: Include splitting analysis in output
   - Total character count
   - Size status (under/over 5k limit)
   - Estimated atomic PRPs needed (if >5k)
   - Recommended split points (if >5k)
   - Next steps for user

**Note**: Size analysis is informational only. Actual splitting occurs during `/generate-prp` phase.

## Life-Critical Standards Consideration

When drafting PRPs, consider if the feature involves:
- **Critical Systems**: Life-safety, security, or financial impact
- **Sensitive Data**: PII, PHI, financial, or confidential information
- **High Availability**: Systems requiring 99.9%+ uptime
- **Regulatory Compliance**: GDPR, HIPAA, SOX, PCI DSS requirements

If YES to any above, the draft must include:
- **NIST Framework Applicability**: Which standards may apply
- **Emergency Stop Triggers**: What could halt development
- **Quality Gate Requirements**: Which validation checkpoints needed
- **Compliance Implications**: Regulatory requirements to consider 

**Note**: This is NOT the final PRP. After your review, use `/generate-prp` for the complete validated version.

## Task Decomposition and Agent Coordination

Leverage @Project Manager, @Architect and other agents as needed to **break down and define tasks** - NOT to solve them (solving happens in `/generate-prp`).

**Decomposition Process**:
- Break down complex features into smaller objectives and finally individual single tasks
- Each task should be independently testable and deliverable
- Include all clarifying questions in the draft for user responses
- **Formula**: Complex Feature → N Tasks → N PRPs → N Commits → Complete Feature (merged to main, all tests passing)

**Size and Scope Guidelines**:
- Each task PRP must be focused and concise, target <5k characters
- All template sections must be completed (not optional - see template below)
- Be concise but complete in each section using bullet points over paragraphs
- If a single task legitimately exceeds 5k with all sections filled, that's acceptable
- If approaching 8k+ characters, consider if the task should be split further


## Draft PRP Template

```markdown
# DRAFT PRP: [Feature Name]
**Status**: DRAFT - Requires Review
**Created**: [Date]

## Overview
[Brief description of the feature/task based on user input]

## Functional Requirements
- [Core functionality needed]
- [User-facing features]
- [Integration points]

## Technical Context
- [Affected systems/services]
- [Technology stack involved]
- [Dependencies identified]

## Initial Security Considerations
- [Data sensitivity level]
- [Authentication needs]
- [Authorization requirements]

## Initial Privacy Considerations
- [PII involved?]
- [Data collection scope]
- [User consent needs]

## Scope Definition
- **In Scope**: [What's included]
- **Out of Scope**: [What's excluded]
- **Assumptions**: [Key assumptions]

## Success Criteria
- [Measurable outcomes]
- [Performance targets]
- [Quality metrics]

## Questions for Review
- [Clarifications needed]
- [Design decisions required]
- [Risk assessments needed]

## User Stories
### User Experience
- As a [user type], I want [goal] so that [benefit]
- User workflow: [step-by-step user journey]
- Acceptance criteria: [specific requirements for user satisfaction]

### Admin Experience
- As an admin, I need [capability] to [accomplish administrative task]
- Admin workflows: [administrative processes and procedures]
- Management requirements: [reporting, monitoring, configuration needs]

### Auditor Experience
- As an auditor, I must verify [compliance requirement] to ensure [regulatory standard]
- Audit trail requirements: [what needs to be logged, tracked, and reportable]
- Compliance checkpoints: [validation points and documentation needs]

### Customer Experience
- As a customer, I expect [service level] when [using the system]
- Service impact: [how changes affect customer experience and satisfaction]
- Support requirements: [help desk, documentation, training needs]

### 3rd Party Experience (Family, Friend, etc)
- As a [family member/friend/partner], I need [access/information] to [support user]
- External integration: [third-party system requirements and API needs]
- Communication needs: [notifications, updates, status information]

## Stakeholder Impact Analysis
### Internal Stakeholders
- **Development Team**: Implementation complexity, technical debt, maintenance burden
- **Operations Team**: Deployment requirements, monitoring needs, support procedures
- **Security Team**: Threat model implications, access controls, audit requirements
- **Compliance Team**: Regulatory adherence, documentation needs, reporting requirements
- **Product Team**: Feature alignment, user research validation, success metrics

### External Stakeholders
- **Customer Communication**: Change notifications, training materials, support updates
- **Partner Integration**: API changes, integration testing, coordination requirements
- **Regulatory Bodies**: Compliance notifications, audit preparation, documentation
- **Public Disclosure**: Security announcements, privacy policy updates, transparency reports

## User Journey Considerations
### Onboarding Experience
- Initial setup and configuration requirements
- Training and education needs
- First-time user success criteria

### Day-to-Day Usage Experience
- Routine workflows and common tasks
- Performance and reliability expectations
- Integration with existing user habits

### Error/Exception Experience
- Error handling and recovery procedures
- Support escalation paths
- User communication during issues

### Offboarding Experience
- Data export and migration requirements
- Access revocation procedures
- Knowledge transfer needs

### Emergency/Crisis Experience
- System failure scenarios and backup procedures
- Emergency contact and communication protocols
- Business continuity requirements

## Accessibility and Inclusion Requirements
### Visual Accessibility
- Screen reader compatibility and ARIA labels
- Color contrast and visual design considerations
- Font size and readability requirements

### Motor Accessibility
- Keyboard navigation and shortcuts
- Touch target sizes and gesture alternatives
- Alternative input method support

### Cognitive Accessibility
- Clear language and simplified workflows
- Consistent navigation and predictable behavior
- Error prevention and clear feedback

### Language and Cultural Considerations
- Internationalization and localization needs
- Cultural sensitivity in design and content
- Multi-language support requirements
```

## Workflow

1. **You run**: `/draft-prp "Add user profile management with avatar upload"`
2. **System creates**: Quick draft focusing on functionality
3. **System analyzes**: Automatic size analysis and splitting recommendations
4. **You review**: Make corrections/additions to draft
5. **You run**: `/generate-prp [draft-filename]` for full validation
   - If ≤5k chars: Single PRP generated
   - If >5k chars: Automatic splitting into atomic PRPs
6. **You review**: Final PRP(s) with all checks
7. **You run**: `/execute-prp [prp-filename]` to start development
   - For atomic PRPs: Execute each sequentially with commit/push after each

## Key Differences from `/generate-prp`

| draft-prp | generate-prp |
|-----------|--------------|
| Task breakdown (15-30 min) | Complete implementation (30-60 min) |
| Defines what to build | Solves how to build it |
| Agent coordination for decomposition | Agent coordination for implementation |
| Multiple focused PRPs created | Single PRP executed |
| Questions for review | Validated requirements |

## Example Usage

```
/draft-prp "Implement two-factor authentication for admin users"
```

Creates a draft covering:
- Basic 2FA flow
- Admin user context
- Initial security needs
- Questions about SMS vs TOTP
- Scope boundaries

## Benefits

- **Fast**: Get initial requirements documented quickly
- **Iterative**: Refine before full analysis
- **Collaborative**: Review points built in
- **Efficient**: Avoid rework by clarifying early

Remember: This is step 1 of 3 in your PRP process. Always review and refine before proceeding to `/generate-prp`.

## Size Awareness and Splitting Analysis

After draft creation, the system automatically analyzes the draft size and provides splitting recommendations if the draft exceeds 5,000 characters.

### Automatic Size Analysis

When a draft is created, the system:
1. Counts total characters in the draft (including markdown, code blocks, whitespace)
2. If draft ≤5,000 chars: Ready for `/generate-prp` (single PRP)
3. If draft >5,000 chars: Provides splitting analysis and recommendations

### Splitting Analysis Report

For drafts exceeding 5,000 characters, the system generates a report including:

**Size Metrics**:
- Total character count
- Overage amount (chars over 5k limit)
- Estimated number of atomic PRPs needed

**Natural Boundaries**:
- Identified task boundaries in the draft
- Section-level analysis (which sections could become atomic PRPs)
- Dependency relationships between tasks

**Recommendations**:
- Suggested split points
- Proposed atomic PRP structure
- Execution order based on dependencies

### Next Steps After Analysis

**For drafts ≤5k chars**:
- Proceed directly to `/generate-prp [draft-filename]`
- Single comprehensive PRP will be generated

**For drafts >5k chars**:
- Review splitting analysis recommendations
- Use `/generate-prp [draft-filename]` to trigger automatic splitting
- System will create multiple atomic PRPs (###-a-001, ###-a-002, etc.)
- Original draft archived with `DRAFT-OVERSIZED-` prefix

**Note**: Splitting happens automatically during `/generate-prp` - no manual intervention required. The analysis here is informational to help you understand how your draft will be processed.

## Output Location and Naming Convention

### Directory
Draft PRPs are saved to: `./prp/drafts/`

### Naming Convention (Actual Usage)
**Standard Format**: `[###]-[a]-[feature-description]-[YYYYMMDD-HHMMSS].md`

Where:
- **[###]**: 3-digit PRP number (001, 002, 003, etc.)
- **[a]**: Single letter for variations (a, b, c, etc.)
- **[feature-description]**: Hyphenated description of the feature
- **[YYYYMMDD-HHMMSS]**: Timestamp (year-month-day-hour-minute-second)

**Real Examples from Repository**:
- `001-c-execute-prp-integration-20250126-100000.md`
- `002-a-fix-precommit-hook-coverage-20251004-190500.md`
- `003-a-one-prp-per-pr-enforcement-20251004-190700.md`
- `005-a-ux-designer-agent-20251004-221700.md`

### Atomic PRP Naming (After Splitting)

When a draft is split into atomic PRPs during `/generate-prp`, the naming convention includes a 3-digit sequence:

**Format**: `[###]-[a]-[###]-[feature-description]-[YYYYMMDD-HHMMSS].md`

**Examples**:
- `008-a-001-size-analysis-20251010-220000.md`
- `008-a-002-split-logic-20251010-220000.md`
- `008-a-003-validation-framework-20251010-220000.md`

Where:
- First `[###]`: Main PRP number
- `[a]`: Variant letter
- Second `[###]`: Atomic sequence (001, 002, 003, etc.)
- Rest: Feature description and timestamp

### Best Practices
- **Single Responsibility**: Each PRP should address one focused feature or fix
- **Clear Description**: Use descriptive hyphenated names that explain the feature
- **Sequential Numbering**: Use next available number in sequence
- **Letter Variants**: Use 'a' for first attempt, 'b' for revision if needed
- **Size Limit**: Keep drafts focused; if >5k chars, automatic splitting will occur

**Note**: Keep PRPs focused and single-purpose. Complex features can be broken into multiple sequential PRPs rather than trying to handle everything in one. The system will automatically handle splitting during generation.

```prp-steps
version: 0
command: draft-prp
args:
  - feature_description
agents:
  - project-manager
  - python-developer
steps:
  - id: create_draft
    agent: project-manager
    action: generate_from_template
    inputs:
      template: templates/prp/draft-prp-template.md
      feature: $ARGUMENTS
    outputs:
      draft_file: prp/drafts/{prp_id}-{variant}-{slug}-{timestamp}.md

  - id: analyze_size
    agent: python-developer
    action: run_script
    inputs:
      script: scripts/prp/analyze-prp-size.py
      file: $steps.create_draft.outputs.draft_file
    outputs:
      report: tmp/reports/{slug}-size.json
```