---
allowed-tools: Task, Read, Grep, Glob
argument-hint: [draft-prp-filepath]
description: Generate a complete Product Requirements Proposal from draft file
---

Generate a complete Product Requirements Proposal from draft file: $ARGUMENTS

**Process**:
0. **Documentation Reading Phase**: Read project documentation for context
   - Read `README.md`, `CLAUDE.md`, relevant docs
   - Extract standards, patterns, conventions
   - Build context for agent coordination
1. **Size Check**: Analyze draft size to determine workflow path
   - If ≤5,000 chars: Proceed to step 2 (single PRP generation)
   - If >5,000 chars: Trigger automatic splitting workflow (step 1a)
1a. **Automatic Splitting Workflow** (when draft >5k chars):
   - Call project-manager agent to parse tasks
   - Call architect-reviewer to validate boundaries
   - Call business-analyst to confirm independence
   - Use split-prp-tasks.py to generate atomic PRPs
   - Validate each atomic PRP with validate-atomic-prp.py
   - Archive original with `DRAFT-OVERSIZED-` prefix
   - Output: Multiple atomic PRPs (###-a-001, ###-a-002, etc.)
2. **Single PRP Generation** (when draft ≤5k chars):
   - Read draft from `./prp/drafts/$ARGUMENTS.md`
   - Use Task tool to engage specialized agents for comprehensive analysis
   - Create validated PRP with multi-agent input
   - Save to `./prp/active/$ARGUMENTS.md`
   - Archive draft to `./prp/completed/DRAFT-$ARGUMENTS.md`

**Agent Coordination Required**: This PRP will be used by specialized agents in sequential workflow. Use Task tool to systematically engage:
- Core agents: business-analyst, architect-reviewer, security-reviewer
- Technology agents: Based on detected project stack
- Specialist agents: Based on feature domain requirements
- Quality agents: test-automation, documentation-writer

Follow comprehensive methodology in `templates/prp/generate-prp-template.md`.

**Core Principles**: Security first, comprehensive testing, clear requirements, complete documentation.

**Quality Gates Required**: Security, architecture, compliance, testing, and performance validation.

**Critical Steps**:
1. Agent analysis & selection (core, technology, specialist, quality agents)
2. Codebase analysis (existing patterns, architecture, dependencies)
3. Multi-agent validation with comprehensive input
4. TDD approach with 100% coverage mandates
5. Update all software and node modules to latest stable versions - compatability and security
6. Life-critical standards compliance (NIST, emergency stops)

**Output**: Complete, agent-validated PRP ready for `/execute-prp` implementation.

**Workflow**:
- **Input**: `./prp/drafts/filename.md`
- **Output**: `./prp/active/filename.md`
- **Archive**: Move draft to `./prp/completed/DRAFT-filename.md`

**CRITICAL**: This PRP will be used by specialized AI agents (Architect, Security, Developer, etc.) in a sequential workflow. Each agent only sees the PRP and their specific context, so comprehensive documentation and examples are essential.

## Core Principles
1. **Security First**: All features must meet security standards
2. **Quality Assurance**: Comprehensive testing and validation required
3. **Clear Requirements**: Detailed specifications for agent workflows
4. **Documentation**: Complete context for multi-agent development
5. **Maintainability**: Long-term support and evolution considerations

## Life-Critical Development Standards (When Applicable)

### NIST Compliance Integration
When developing critical systems, all PRPs must incorporate:
- NIST Cybersecurity Framework (CSF) requirements
- NIST 800-53 Security Controls (Moderate Impact Level)
- NIST 800-218 Secure Software Development Framework
- NIST 800-122 PII Protection Guidelines
- NIST Privacy Framework compliance

### Mandatory Quality Gates
Every PRP must define validation checkpoints:
1. **Security Gate**: security-reviewer validates threat model and controls
2. **Architecture Gate**: architect-reviewer validates design decisions
3. **Compliance Gate**: compliance-officer validates regulatory requirements
4. **Testing Gate**: test-automation validates 100% coverage strategy
5. **Performance Gate**: performance-profiler validates benchmarks

### Redesign Loop Protocol
Failed quality gates trigger redesign process:
- Maximum 3 redesign iterations per gate
- Clear feedback documentation required
- Root cause analysis for each failure
- Escalation to higher authority agents if needed

### Emergency Stop Conditions
PRPs must halt development for:
- Encryption weakening attempts
- Privacy principle violations
- Safety feature removal
- Backdoor implementation
- Data exposure risks

## Project Context Detection
Auto-detect project context from codebase and adapt requirements and agent use accordingly:
- **Languages**: Python, JavaScript/TypeScript, Go, Java, etc.
- **Frameworks**: FastAPI, React/Next.js, Spring Boot, etc.
- **Databases**: PostgreSQL, MongoDB, MySQL, etc.
- **Infrastructure**: Docker, Kubernetes, cloud providers
- **Testing**: Unit, integration, security, performance requirements

## Research Process

0. **Documentation Reading Phase (MANDATORY FIRST STEP - NEW)**
   - **Read Core Documentation**: Parse `README.md` and `CLAUDE.md` for project context
   - **Extract Standards**: Identify coding standards, patterns, conventions
   - **Review Architecture**: Understand system design and integration points
   - **Gather Constraints**: Note security, compliance, performance requirements
   - **Build Context Dictionary**: Compile documentation insights for all agents
   - **CRITICAL**: This context informs all subsequent agent analysis and validation

1. **Size Check and Workflow Decision (MANDATORY SECOND STEP - NEW)**
   - **Analyze Draft Size**: Use python-developer with `scripts/prp/analyze-prp-size.py`
   - **Count Characters**: Total characters including markdown, code blocks, whitespace
   - **Determine Path**:
     - Draft ≤5,000 chars: Continue to step 2 (single PRP generation)
     - Draft >5,000 chars: Branch to step 1a (automatic splitting workflow)
   - **CRITICAL**: Size determines whether single or multi-PRP output

1a. **Automatic Splitting Workflow (WHEN DRAFT >5k CHARS - NEW)**
   - **Phase 1 - Task Parsing**:
     - Call project-manager agent with documentation context
     - Parse draft into discrete, independent tasks
     - Identify task boundaries using section markers and content analysis
     - Extract task metadata (title, description, requirements)

   - **Phase 2 - Boundary Validation**:
     - Call architect-reviewer agent with task definitions
     - Validate technical boundaries (no circular dependencies)
     - Ensure clear integration points between tasks
     - Verify each task can be implemented independently

   - **Phase 3 - Independence Confirmation**:
     - Call business-analyst agent with validated tasks
     - Confirm each task delivers independent business value
     - Verify no hidden dependencies or coupling
     - Validate execution order and prerequisite chains

   - **Phase 4 - Atomic PRP Generation**:
     - Use python-developer with `scripts/prp/split-prp-tasks.py`
     - Generate atomic PRP for each task using `templates/prp/atomic-prp-template.md`
     - Apply naming convention: `###-[a]-###-[task-desc]-[timestamp].md`
     - Sequence numbering: 001, 002, 003, etc.
     - Maintain traceability to original draft

   - **Phase 5 - Validation**:
     - Use python-developer with `scripts/prp/validate-atomic-prp.py` for each atomic PRP
     - Verify ≤5,000 character limit per atomic PRP
     - Check single responsibility (one task per PRP)
     - Validate completeness (all required sections present)
     - Ensure no content loss from original draft

   - **Phase 6 - Archival**:
     - Move original draft to `./prp/completed/DRAFT-OVERSIZED-$ARGUMENTS.md`
     - Save all atomic PRPs to `./prp/active/###-[a]-###-[desc]-[timestamp].md`
     - Generate summary report with atomic PRP count and execution order

   - **Output**: Multiple atomic PRPs ready for sequential execution
   - **CRITICAL**: Process is fully autonomous - no user prompts during splitting

2. **Agent Analysis & Selection (MANDATORY FOR SINGLE PRP GENERATION)**
   - **Review Available Agents**: Analyze `agents/` directory to identify relevant specialists
   - **Map Requirements to Agents**: Match feature requirements to appropriate domain experts
   - **Plan Agent Utilization**: Define which agents will contribute to PRP creation
   - **CRITICAL**: Leverage specialized agents to ensure comprehensive PRP coverage

3. **Codebase Analysis (MANDATORY FOR SINGLE PRP GENERATION)**
   - **Read Draft File**: Parse the input draft from `./prp/drafts/`
   - **Analyze Project Structure**: Understand existing architecture, dependencies and patterns
   - **Identify Technologies**: Detect frameworks, languages, and tools in use
   - **Review Similar Features**: Find existing implementations to build upon
   - **CRITICAL**: All development must leverage existing patterns and standards, review prior work.

4. **Agent-Driven Analysis (MANDATORY FOR SINGLE PRP GENERATION)**
   - **Security Analysis**: Use `security-reviewer` agent for comprehensive threat assessment
   - **Architecture Review**: Leverage `architect-reviewer` for design validation
   - **Technology Assessment**: Use relevant developer agents (python-developer, nodejs-developer, etc.)
   - **Business Analysis**: Engage `business-analyst` for requirements validation
   - **Compliance Review**: Use `compliance-officer` for regulatory requirements
   - **Performance Planning**: Engage `performance-profiler` for optimization strategy
   - **CRITICAL**: Each agent provides detailed input to ensure no aspect is overlooked

5. **Technical Deep-Dive Analysis (MANDATORY FOR SINGLE PRP GENERATION)**
   - Search for similar features/patterns in existing codebase
   - Identify integration points and service boundaries
   - Review existing conventions and architectural patterns
   - Check current security and quality implementations
   - Analyze deployment and infrastructure requirements

6. **Industry Standards Research (MANDATORY FOR SINGLE PRP GENERATION)**
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

```yaml
# Agent Selection Matrix (Select based on feature requirements)
core_agents:
  - business-analyst: Requirements validation and business impact
  - architect-reviewer: System design and integration patterns
  - security-reviewer: Security assessment and threat modeling

technology_agents: # Select based on detected tech stack
  - python-developer: For Python/FastAPI backends
  - nodejs-developer: For Node.js/Express services
  - react-developer: For React/Next.js frontends
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
