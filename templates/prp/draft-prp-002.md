# Draft-PRP Template

## Draft PRP Structure

```markdown
- atomic: true
- objective: once concise sentence
- affected_components: (2 max)
  - component1
  - component2
- dependencies:
  - dependency1
  - dependency2
- cross_service_changes: false


# PRP: [Feature Name]

## Executive Summary
Brief description of the feature and its purpose.

## Business Justification
Why this feature is needed and what business value it provides.

## User Stories
*Follow the comprehensive framework in `docs/USER_STORIES.md`*

### Required Stakeholder Perspectives
1. **Primary End User**: Core functionality stories
2. **System Administration**: Operational and maintenance stories
3. **Security Administration**: Security and compliance stories
4. **Company Administration**: Business value and ROI stories

### Story Categories
- **Functional Stories**: What the system should do
- **Non-Functional Stories**: How the system should perform
- **Security Stories**: Security requirements and protections
- **Operational Stories**: Monitoring, deployment, maintenance
- **Compliance Stories**: Regulatory and audit requirements
- **Recovery Stories**: Disaster recovery and error handling

### Validation Checklist
- [ ] All required perspectives covered
- [ ] Clear acceptance criteria defined
- [ ] Business value articulated
- [ ] Technical feasibility assessed
- [ ] Security requirements identified

## Functional Requirements
- High-level functionality description
- Key user interactions
- Expected behavior

## Technical Considerations
- Technology stack implications
- Integration requirements
- Data flow considerations

## Success Criteria
- How success will be measured
- Acceptance criteria
- Definition of done

## Next Steps
- Areas needing more detailed analysis
- Questions for follow-up
- Dependencies to investigate
```

# PRP Processing Instructions

## Quality Reminders
- Keep it focused on core requirements
- Avoid over-engineering at draft stage
- Focus on clarity and completeness of the problem statement
- Save detailed technical analysis for `/generate-prp` phase

## Quick Requirements Capture Framework

### Core Information Gathering
- **Feature Description**: What functionality is being requested?
- **User Context**: Who will use this feature and how?
- **Business Justification**: Why is this feature needed?
- **Success Criteria**: How will we know it's successful?

### User Stories
Capture key user stories following the comprehensive framework in `docs/USER_STORIES.md`.

#### Required Perspectives (minimum)
- **Primary End User**: As a [main user], I want [core functionality] so that [primary benefit]
- **System Administrator**: As a [sysadmin], I want [operational capability] so that [system benefit]
- **Security Administrator**: As a [security role], I want [security control] so that [security benefit]
- **Company Administration**: As a [business role], I want [business value] so that [ROI/strategic benefit]

#### Additional Perspectives (as applicable)
- **Developer/Maintainer**: Technical maintenance and code quality stories
- **Support Staff**: User assistance and troubleshooting stories
- **Audit & Compliance**: Regulatory and compliance stories
- **External Stakeholders**: Customer, partner, or regulatory stories

*Reference: See `docs/USER_STORIES.md` for complete perspective list, story categories, and validation checklist.*

### Initial Technical Considerations
- **Technology Stack**: What technologies might be involved?
- **Integration Points**: How does this connect to existing systems?
- **Data Requirements**: What data is needed or produced?
- **User Interface**: What UI/UX considerations exist?

### Basic Quality Requirements
- **Testing Approach**: How should this be tested?
- **Security Considerations**: Any obvious security concerns?
- **Performance Expectations**: Basic performance requirements
- **Documentation Needs**: What documentation will be required?