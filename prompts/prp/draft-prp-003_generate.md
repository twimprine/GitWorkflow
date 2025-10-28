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
# TASK003 — Recommended Agents Prompt (elevated)

   - **Review Similar Features**: Find existing implementations to build upon

   - **CRITICAL**: All development must leverage existing patterns and standards, review prior work.



  - TASK001: Panel decomposition (atomic tasks draft)
  - TASK002: Architect answers per question (P–T–Q saved)

   - **Technology Assessment**: Use relevant developer agents (python-developer, nodejs-developer, etc.)

  - Copy the JSON template’s keys and nesting exactly. Do not add/remove keys.
  - Preserve key order. Replace only placeholder/example values.
  - Response must be a single JSON object with keys:
    - outputs.draft_file: string (suggest a simple name; the system will rewrite)
    - content: object (exactly the template shape)
  - No prose before/after JSON. No fenced code blocks. No markdown.
  - If the template has an agent field, set it to your own agent id.
  - Single objective. ≤ 2 affected components. ≤ 1 dependency (prefer 0).
  - 3–5 acceptance checks, concrete and verifiable.
  - Where applicable, cite back to architect answers (TASK002) or panel task items (TASK001) using stable labels/ids you reference in content.
  - Always include a brief risk/mitigation note relevant to your domain.
  - Flag compliance/regulatory concerns when any sensitive data or auth logic is involved.

   - Search for similar features/patterns in existing codebase


   - Best practices for identified technology stack

   - Security standards and implementation guides

   - Performance optimization techniques
   - Testing strategies and frameworks
   - Documentation and maintenance approaches

7. **Integration & Dependencies Assessment (MANDATORY FOR SINGLE PRP GENERATION)**
   - Which services/modules need modification?
   - API changes and backwards compatibility needs?
   - Database schema changes required?
   - Third-party service integrations?
   - Monitoring and observability requirements?

8. **Requirement Validation & Clarification (MANDATORY FOR SINGLE PRP GENERATION)**
   - Validate functional requirements with business-analyst
   - Clarify performance expectations with performance-profiler
   - Confirm security/compliance constraints with security-reviewer
   - Review user experience considerations with relevant UI/UX specialists

## PRP Generation

Create a comprehensive PRP by processing the draft file, leveraging specialized agents, and expanding it with detailed multi-agent analysis:

### Agent Contribution Framework
Before writing the PRP, systematically engage relevant agents to gather expert input:


  - business-analyst: Requirements validation and business impact


  - golang-developer: For Go microservices
  - java-developer: For Java/Spring applications

specialist_agents: # Select based on feature domain
  - api-designer: For API design and standards
  - database-administrator: For data modeling and migrations
  - performance-profiler: For performance requirements
  - test-automation: For testing strategy
  - compliance-officer: For regulatory requirements
  - cloud-architect: For infrastructure and deployment
  - ml-specialist: For AI/ML features
  - blockchain-developer: For crypto/blockchain features

quality_agents:
  - documentation-writer: For technical documentation
  - project-manager: For timeline and resource planning
```

### PRP Sections (Enhanced with Agent Input)


### 1. Goal & Purpose (Enhanced by business-analyst)
- Clear description of what needs to be built
- Business value and user benefits validated by business-analyst
- Success criteria and measurable outcomes defined
- Stakeholder impact assessment

### 2. Why (Business Value - Enhanced by business-analyst)
- User impact and benefits analysis
- Problem definition and solution fit
- Return on investment projections
- Integration with existing systems and workflows

### 3. What (Requirements - Multi-Agent Enhanced)
- **Functional Requirements**: User-facing behavior validated by business-analyst
- **Security Requirements**: Comprehensive assessment by security-reviewer
- **Performance Requirements**: Targets defined by performance-profiler
- **Technical Requirements**: Architecture validated by architect-reviewer
- **API Requirements**: Standards defined by api-designer (if applicable)
- **Data Requirements**: Schema design by database-administrator (if applicable)
- **Testing Requirements**: Strategy defined by test-automation
- **Compliance Requirements**: Standards verified by compliance-officer

### 4. All Needed Context (Agent-Sourced Intelligence)
```yaml
# Agent-Provided Analysis
agent_inputs:
  architect_reviewer:
    analysis: [System design patterns, integration points, scalability concerns]
    recommendations: [Architecture decisions, design patterns to follow]

  security_reviewer:
    threat_model: [Identified attack vectors, security controls needed]
    compliance: [Security standards, vulnerability assessments]

  technology_agents: # Based on detected stack
    patterns: [Framework-specific best practices, existing implementations]
    standards: [Coding conventions, testing approaches, deployment patterns]

  performance_profiler:
    benchmarks: [Performance targets, optimization strategies]
    monitoring: [Metrics to track, alerting requirements]

# Codebase Intelligence
codebase_analysis:
  similar_features: [Existing implementations to reference]
  patterns: [Architecture patterns in use, conventions to follow]
  dependencies: [Libraries and frameworks currently used]
  integration_points: [Services/modules that will be affected]

# External Context
industry_standards:
  security: [OWASP guidelines, security frameworks]
  performance: [Industry benchmarks, best practices]
  compliance: [Regulatory requirements, standards to meet]

# Project Context
project_standards:
  documentation: [README.md, CONTRIBUTING.md, API docs]
  testing: [Testing frameworks, coverage requirements]
  deployment: [Infrastructure patterns, CI/CD processes]
```

### 5. Design Considerations
- **UI/UX**: User experience and interface design requirements
- **Accessibility**: Compliance with accessibility standards
- **Responsive Design**: Multi-device support requirements
- **Performance**: Front-end optimization considerations

### 6. Test-Driven Development (TDD) Approach - REQUIRED

**CRITICAL**: All development MUST follow Red-Green-Refactor cycle. Write tests FIRST, then implementation.

#### TDD Process for Each Feature
1. **RED**: Write failing tests that specify the behavior
2. **GREEN**: Write minimal code to make tests pass
3. **REFACTOR**: Improve code while keeping tests green

#### Life-Critical Testing Requirements
For critical systems, implement comprehensive test coverage:

**Required Test Types (100% Coverage Each):**
1. **Unit Tests**: Every function, every path, every edge case
2. **Integration Tests**: All service boundaries and data flows
3. **E2E Tests**: Complete user journeys and workflows
4. **Security Tests**: Authentication, authorization, encryption, injection
5. **Chaos Tests**: Failure scenarios and recovery mechanisms
6. **Performance Tests**: Load, stress, endurance under peak conditions
7. **Accessibility Tests**: WCAG AA compliance verification

**Coverage Mandates (NO EXCEPTIONS):**
```yaml
minimum_coverage:
  lines: 100%
  branches: 100%
  functions: 100%
  statements: 100%
  security_functions: 100%
  error_paths: 100%
```

#### Example: Security Test First (Python)
```python
# STEP 1: Write failing security test FIRST (RED)
def test_authentication_required():
    """Verify unauthorized access is blocked"""
    # Attempt to access protected resource without auth
    response = client.get("/api/protected-endpoint")
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]

    # Verify authorized access works with valid token
    headers = {"Authorization": f"Bearer {valid_token}"}
    authenticated_response = client.get("/api/protected-endpoint", headers=headers)
    assert authenticated_response.status_code == 200
    assert authenticated_response.json()["data"] is not None
```

#### Example: Functional Test First (Python)
```python
# STEP 1: Write failing functional test FIRST (RED)
def test_feature_core_functionality():
    """Verify core feature behavior works as specified"""
    # Setup test data
    input_data = {"name": "test", "value": 42}

    # Execute feature
    result = execute_feature(input_data)

    # Verify expected behavior
    assert result["success"] is True
    assert result["output"] == "processed: test (42)"
    assert result["created_at"] is not None  # Side effect check
```

**Note**: Examples shown in Python (primary project language). Apply same TDD principles to Bash scripts, Docker configs, and other languages in the codebase.

### 7. Implementation Blueprint (Agent-Driven Development Plan)
```yaml
# Pre-Implementation Agent Analysis
agent_preparation:
  architect_reviewer:
    deliverables:
      - System architecture design
      - Integration point specifications
      - Scalability and reliability patterns

  security_reviewer:
    deliverables:
      - Comprehensive threat model
      - Security control specifications
      - Vulnerability mitigation strategies

  performance_profiler:
    deliverables:
      - Performance benchmarks and targets
      - Optimization strategy
      - Monitoring and alerting requirements

# Technology-Specific Agent Planning
development_planning:
  technology_agents: # Selected based on stack
    responsibilities:
      - Review existing patterns and implementations
      - Define TDD approach with test examples
      - Specify coding standards and conventions
      - Plan integration with existing systems

  api_designer: # If API development needed
    responsibilities:
      - API specification and standards
      - Contract definition and validation
      - Integration patterns and protocols

  database_administrator: # If data changes needed
    responsibilities:
      - Schema design and migration planning
      - Performance optimization strategy
      - Data integrity and validation rules

# Implementation with Agent Oversight
component_development:
  backend_services:
    agent_oversight: [technology-agent, security-reviewer]
    tasks:
      - Agent-validated existing pattern analysis
      - Write failing tests per agent specifications
      - Implement with agent-defined security controls
      - Validate with agent-specified test coverage

  frontend_components:
    agent_oversight: [react-developer, ux-designer]
    tasks:
      - Agent-reviewed component patterns
      - Write failing tests for UI behavior and accessibility
      - Implement with agent-validated design patterns
      - Test with agent-specified user interaction scenarios

# Quality Gates with Agent Validation
test_coverage:
  requirements:
    - 100% code coverage overall (verified by test-automation)
    - 100% security function coverage (verified by security-reviewer)
    - 100% data handling coverage (verified by database-administrator)
    - All edge cases tested (validated by relevant specialist agents)

deployment_preparation:
  agent_responsibilities:
    - cloud-architect: Infrastructure and deployment specifications
    - devops-engineer: CI/CD pipeline and automation
    - monitoring-specialist: Observability and alerting setup
```

### 8. PRP Creation Process (Agent Coordination)

#### Phase 1: Agent Selection and Briefing
```bash
# Step 1: Verify available agents before selection
ls -la agents/                      # List all available agents
grep -l "business-analyst\|architect-reviewer\|security-reviewer" agents/*.md

# Step 2: Validate agent files exist before Task delegation
if [ -f "agents/business-analyst.md" ]; then
  Task(subagent_type="business-analyst", prompt="Analyze requirements and business value")
else
  echo "WARNING: business-analyst agent not found, using general analysis"
fi

# Step 3: Engage core agents for foundational analysis
Task(subagent_type="business-analyst", prompt="Analyze requirements and business value")
Task(subagent_type="architect-reviewer", prompt="Review architecture implications")
Task(subagent_type="security-reviewer", prompt="Conduct security assessment")
```

#### Phase 2: Technology-Specific Analysis
```bash
# Step 3: Engage technology-specific agents based on detected stack
# Python project example:
Task(subagent_type="python-developer", prompt="Analyze Python implementation patterns")

# React frontend example:
Task(subagent_type="react-developer", prompt="Review UI component requirements")

# Database changes example:
Task(subagent_type="database-administrator", prompt="Design schema changes")
```

#### Phase 3: Specialist Domain Analysis
```bash
# Step 4: Engage specialist agents based on feature domain
# API development:
Task(subagent_type="api-designer", prompt="Define API specifications")

# Performance requirements:
Task(subagent_type="performance-profiler", prompt="Define performance targets")

# Compliance needs:
Task(subagent_type="compliance-officer", prompt="Review regulatory requirements")
```

#### Phase 4: Quality and Documentation
```bash
# Step 5: Engage quality assurance agents
Task(subagent_type="test-automation", prompt="Define comprehensive test strategy")
Task(subagent_type="documentation-writer", prompt="Plan documentation requirements")
Task(subagent_type="project-manager", prompt="Create timeline and resource plan")
```

### 9. Multi-Agent Validation Requirements
```yaml
# PRP Validation by Multiple Agents
prp_validation:
  business_analyst:
    validates: [Requirements completeness, business value, success criteria]
    deliverable: "Business requirements validation report"

  architect_reviewer:
    validates: [System design, integration points, scalability approach]
    deliverable: "Architecture design validation"

  security_reviewer:
    validates: [Threat model, security controls, vulnerability mitigation]
    deliverable: "Security assessment and requirements"

  technology_agents:
    validates: [Implementation feasibility, existing pattern usage, TDD approach]
    deliverable: "Technical implementation plan with test specifications"

  performance_profiler:
    validates: [Performance targets, optimization strategy, monitoring plan]
    deliverable: "Performance requirements and benchmarks"

  compliance_officer:
    validates: [Regulatory compliance, industry standards, audit requirements]
    deliverable: "Compliance requirements and validation criteria"

# Implementation Validation (Post-PRP)
implementation_validation:
  test_automation:
    validates: [Test coverage, test strategy, quality gates]
    deliverable: "Comprehensive test plan and execution strategy"

  deployment_manager:
    validates: [Infrastructure requirements, deployment process, rollback plans]
    deliverable: "Deployment and infrastructure specifications"
```

### 9. Validation Gates (Must be Executable)

#### Backend Validation (Project Stack: Python/Bash)
```bash
# Python Code Quality
cd agents/[agent-name]/  # or relevant directory
python -m black . --check           # Format checking
python -m flake8 .                  # Linting
python -m mypy . --strict           # Type checking

# Python Unit Tests with Coverage (100% required)
python -m pytest tests/ -v \
  --cov=src \
  --cov-report=term-missing \
  --cov-fail-under=100

# Python Security Scanning
python -m bandit -r src/            # Security linting
python -m pip-audit                 # Dependency vulnerabilities

# Bash Script Validation
shellcheck hooks/**/*.sh            # Bash linting
bats tests/hooks/**/*.bats          # Bash unit tests

# Integration Testing
python -m pytest tests/integration/ -v
```

#### Infrastructure Validation (Project Stack: Docker/Git Hooks)
```bash
# Docker Container Validation
docker build -t test-image .
docker run --rm test-image python -m pytest

# Git Hooks Validation
./hooks/tools/test-hook.sh [hook-name]
./scripts/tdd-enforcement/verify-tdd-cycle.sh

# GPG Signature Verification (if security hooks)
gpg --verify hooks/core/[script].sh.sig hooks/core/[script].sh
```

#### Security & Compliance Validation (Project Standards)
```bash
# Dependency Vulnerability Scanning
python -m pip-audit --strict        # Fail on any vulnerabilities

# Secret Scanning
git secrets --scan                  # Check for committed secrets
grep -r "API_KEY\|SECRET\|PASSWORD" src/ || echo "No hardcoded secrets"

# TDD Cycle Verification
./scripts/tdd-enforcement/verify-tdd-cycle.sh

# Mock Detection (production code must be clean)
python3 scripts/tdd-enforcement/detect-mocks.py src/

# Coverage Validation
./scripts/test-coverage.sh [agent-name] 100
```

#### Project-Specific Quality Gates
```bash
# Agent Deployment Validation (if creating new agent)
./scripts/deploy-agents.sh --dry-run [agent-name]

# Hook Security Validation (if modifying hooks)
./hooks/core/signature-verify.sh hooks/core/[script].sh
./hooks/core/version-check.sh hooks/core/[script].sh

# CI/CD Pipeline Check (all gates must pass)
# - TDD verification
# - Mock detection
# - Contract testing
# - 100% coverage
# - Mutation testing
# - Results aggregation
```

### 10. Testing Strategy & TDD Verification

#### Test Categories (All Written FIRST)
- **Unit Tests**: Test individual functions with mocked dependencies
- **Integration Tests**: Test component boundaries and API contracts
- **Security Tests**: Authentication, authorization, input validation tests
- **Performance Tests**: Load testing, response time verification
- **E2E Tests**: Full user journey testing (if applicable)

#### TDD Verification Commands
```bash
# Verify tests were written first (check git history)
git log --oneline --grep="test" --grep="implementation" --all-match

# Verify test coverage meets requirements (adapt to your testing framework)
# Python: pytest --cov=src --cov-report=html --cov-fail-under=80
# Java: mvn jacoco:check
# Node.js: npm test -- --coverage --coverageThreshold.global.statements=80

# Verify security-critical functions have 100% coverage
# Adapt coverage commands to check security-specific modules
```

## File Workflow Management

### Process Steps:
1. **Read Draft**: Parse `./prp/drafts/$ARGUMENTS.md`
2. **Generate Complete PRP**: Create comprehensive requirements document
3. **Archive Draft**: Move draft to `./prp/completed/DRAFT-$ARGUMENTS.md`
4. **Output Active PRP**: Save complete PRP to `./prp/active/$ARGUMENTS.md`

### Directory Structure:
```
./prp/
├── drafts/           # Input: rough draft PRPs
├── active/           # Output: complete, ready-to-implement PRPs
└── completed/        # Archive: processed drafts with DRAFT- prefix
```

## Quality Checklist (Agent-Validated PRP)

### Pre-PRP Agent Analysis
- [ ] Agent availability verified: `ls agents/ | grep -E "business-analyst|architect-reviewer|security-reviewer"`
- [ ] Agent selection matrix completed based on feature requirements
- [ ] Core agents confirmed available before delegation:
  - business-analyst: `test -f agents/business-analyst.md && echo "Available" || echo "Missing"`
  - architect-reviewer: `test -f agents/architect-reviewer.md && echo "Available" || echo "Missing"`
  - security-reviewer: `test -f agents/security-reviewer.md && echo "Available" || echo "Missing"`
- [ ] Technology-specific agents identified and existence verified
- [ ] Specialist domain agents selected with availability confirmation
- [ ] Cost estimation completed (multiple agent API calls can hit usage limits)

### Agent Input Integration
- [ ] Business-analyst: Requirements validation and business value assessment
- [ ] Architect-reviewer: System design and integration analysis
- [ ] Security-reviewer: Comprehensive threat model and security requirements
- [ ] Technology agents: Implementation patterns and TDD specifications
- [ ] Performance-profiler: Benchmarks and optimization strategy (if applicable)
- [ ] API-designer: API specifications and standards (if applicable)
- [ ] Database-administrator: Schema design and data requirements (if applicable)
- [ ] Compliance-officer: Regulatory and standards compliance (if applicable)

### PRP Content Validation
- [ ] Draft file successfully read and analyzed with agent input
- [ ] Agent-sourced codebase patterns and architecture identified
- [ ] Multi-agent security assessment with comprehensive threat model
- [ ] Agent-validated TDD approach with test specifications
- [ ] Agent-provided test examples for critical functionality and security
- [ ] Complete agent-sourced context for multi-agent development workflow
- [ ] Agent-validated implementation patterns and existing code usage
- [ ] Agent-specified error handling and edge case documentation
- [ ] Clear multi-agent handoff requirements and responsibilities defined

### Quality Assurance
- [ ] Industry best practices validated by relevant specialist agents
- [ ] Compliance standards verified by compliance-officer
- [ ] Test coverage requirements specified and validated by test-automation
- [ ] Performance benchmarks defined and validated by performance-profiler
- [ ] Documentation requirements specified by documentation-writer

## Multi-Agent Workflow Context

This PRP will be processed by specialized agents in sequence:

1. **Project Manager** → Coordinates overall feature development
2. **Architect** → Reviews and validates architectural design
3. **Security Reviewer** → Validates security requirements and implementation
4. **Developer Agents** → Implement code following TDD approach
5. **Test Automation** → Executes comprehensive test suites
6. **Quality Assurance** → Validates code quality and coverage standards
7. **Documentation Writer** → Creates technical documentation
8. **Deployment Manager** → Handles deployment artifacts and processes

**IMPORTANT**: Any agent can escalate issues that require architectural changes or security reviews. The workflow supports iteration and feedback loops.

## Example Usage (Agent-Driven PRP Generation)

### Example 1: Small Draft (≤5k chars) - Single PRP Output

```bash
# Step 1: Create initial draft
/draft-prp "Add user login endpoint"

# Step 2: Review and edit the draft in ./prp/drafts/
# Draft size: 3,200 characters (under 5k limit)

# Step 3: Generate comprehensive agent-validated PRP
/generate-prp "009-a-user-login-endpoint-20251011-120000"

# This process will:
# 0. Read project documentation (README.md, CLAUDE.md)
# 1. Check size: 3,200 chars ≤ 5,000 → single PRP generation
# 2. Analyze available agents and select appropriate specialists:
#    - business-analyst (requirements validation)
#    - architect-reviewer (system design)
#    - security-reviewer (auth security assessment)
#    - python-developer (if Python backend detected)
#    - api-designer (for API design)
# 3. Systematically engage each agent for detailed input
# 4. Synthesize agent outputs into comprehensive PRP
# 5. Move draft to ./prp/completed/DRAFT-009-a-user-login-endpoint-20251011-120000.md
# 6. Save agent-validated PRP to ./prp/active/009-a-user-login-endpoint-20251011-120000.md

# Result: A single comprehensive PRP ready for implementation
```

### Example 2: Large Draft (>5k chars) - Automatic Splitting

```bash
# Step 1: Create initial draft
/draft-prp "Complete user authentication system with OAuth, 2FA, and session management"

# Step 2: Review and edit the draft in ./prp/drafts/
# Draft size: 12,400 characters (exceeds 5k limit)

# Step 3: Generate comprehensive agent-validated PRPs with automatic splitting
/generate-prp "010-a-complete-auth-system-20251011-130000"

# This process will:
# 0. Read project documentation (README.md, CLAUDE.md)
# 1. Check size: 12,400 chars > 5,000 → trigger automatic splitting
# 1a. Automatic Splitting Workflow:
#     Phase 1: project-manager parses draft into tasks:
#       - Task 1: OAuth integration
#       - Task 2: 2FA implementation
#       - Task 3: Session management
#     Phase 2: architect-reviewer validates boundaries
#     Phase 3: business-analyst confirms independence
#     Phase 4: python-developer generates atomic PRPs:
#       - ./prp/active/010-a-001-oauth-integration-20251011-130000.md (4,200 chars)
#       - ./prp/active/010-a-002-2fa-implementation-20251011-130000.md (3,800 chars)
#       - ./prp/active/010-a-003-session-management-20251011-130000.md (4,100 chars)
#     Phase 5: python-developer validates each atomic PRP
#     Phase 6: Archive original as DRAFT-OVERSIZED-010-a-complete-auth-system-20251011-130000.md
# 2. Output summary:
#    - 3 atomic PRPs created
#    - Execution order: 001 → 002 → 003
#    - All PRPs ≤5,000 chars
#    - Original draft preserved in completed/

# Result: Multiple focused atomic PRPs ready for sequential implementation
# Execute with: /execute-prp 010-a-001-oauth-integration-20251011-130000
#              /execute-prp 010-a-002-2fa-implementation-20251011-130000
#              /execute-prp 010-a-003-session-management-20251011-130000
```

### Agent Selection Example for Authentication Feature:
```yaml
selected_agents:
  core_analysis:
    - business-analyst: "Validate authentication requirements and user impact"
    - architect-reviewer: "Design authentication architecture and integration"
    - security-reviewer: "Comprehensive auth security assessment and threat model"

  technology_specific:
    - python-developer: "Review FastAPI auth patterns and JWT implementation"
    - react-developer: "Design login/signup components and auth state management"

  specialist_domains:
    - api-designer: "Define authentication API standards and endpoints"
    - database-administrator: "Design user auth schema and session management"
    - performance-profiler: "Define auth performance benchmarks and caching"

  quality_assurance:
    - test-automation: "Define comprehensive auth testing strategy"
    - compliance-officer: "Ensure GDPR/CCPA compliance for user data"
```

## References
- **CLAUDE.md**: Project-specific development rules and standards
- **README.md**: Project overview and setup instructions
- **CONTRIBUTING.md**: Development workflow and contribution guidelines
- **docs/**: Project documentation and architectural decisions
- **tests/**: Existing test patterns and frameworks

## Agent-Driven Development Philosophy

**Key Principle**: No PRP is complete without comprehensive multi-agent analysis and validation.

### Why Agent-Driven PRPs?
1. **Comprehensive Coverage**: Each specialist agent brings domain expertise that ensures no critical aspect is overlooked
2. **Quality Assurance**: Multiple expert perspectives validate requirements before implementation begins
3. **Reduced Rework**: Thorough upfront analysis by specialists prevents costly mid-development discoveries
4. **Standards Compliance**: Specialist agents ensure adherence to industry standards and best practices
5. **Risk Mitigation**: Security, compliance, and performance risks are identified and addressed in planning phase

### Agent Utilization Benefits:
- **business-analyst**: Ensures requirements are complete and business-aligned
- **architect-reviewer**: Validates system design and integration patterns
- **security-reviewer**: Provides comprehensive threat modeling and security controls
- **technology-agents**: Ensure implementation follows established patterns and conventions
- **specialist-agents**: Address domain-specific requirements (API design, database optimization, etc.)
- **quality-agents**: Define comprehensive testing, documentation, and deployment strategies

### Success Criteria:
A PRP is ready for implementation only when:
- [ ] All relevant agents have provided input and validation
- [ ] Agent recommendations are synthesized into actionable requirements
- [ ] Multi-agent quality checklist is complete
- [ ] Implementation path is validated by appropriate technology agents
- [ ] Security and compliance requirements are verified by specialist agents

Remember: Every feature must meet security, quality, and maintainability standards while following established project conventions. The agent-driven PRP process ensures these standards are met before development begins, not after.
