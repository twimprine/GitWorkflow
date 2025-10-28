# Generate-PRP Template

## Agent Coordination Strategy

### Core Agents (Always Required)
- **business-analyst**: Requirements validation, business value assessment
- **architect-reviewer**: System design, integration patterns, scalability review
- **security-reviewer**: Security assessment, compliance validation, threat modeling

### Technology Agent Selection
Based on detected project stack and requirements:
- **python-developer**: Python-based implementations
- **nodejs-developer**: Node.js/JavaScript implementations
- **java-developer**: Java-based implementations
- **golang-developer**: Go-based implementations
- **rust-developer**: Rust-based implementations
- **react-developer**: Frontend React implementations
- **typescript-developer**: TypeScript implementations

### Specialist Agent Selection
Based on feature domain:
- **database-administrator**: Database schema, queries, migrations
- **api-designer**: API design, REST/GraphQL specifications
- **cloud-architect**: Cloud infrastructure, deployment architecture
- **devops-engineer**: CI/CD, deployment automation, infrastructure
- **performance-profiler**: Performance requirements, optimization strategies

### Quality Agents (Always Required)
- **test-automation**: Test strategy, coverage requirements, TDD approach
- **documentation-writer**: Documentation requirements, user guides, API docs

## Multi-Agent Workflow

### Phase 1: Requirements Analysis
1. **business-analyst** validates business requirements using `docs/USER_STORIES.md` framework
   - Ensure all required stakeholder perspectives are covered
   - Validate user story categories (Functional, Security, Operational, Compliance)
   - Apply story validation checklist for business validation
2. **architect-reviewer** assesses technical feasibility and system integration
   - Add technical and integration user stories
   - Define performance and scalability stories
3. **security-reviewer** identifies security requirements and compliance needs
   - Ensure security and compliance user stories are comprehensive
   - Validate audit and regulatory stories
4. **Deliverables**: Complete user story matrix with all perspectives, categories, and acceptance criteria

### Phase 2: Technical Specification
1. **Technology agents** define implementation approach and patterns
2. **Specialist agents** provide domain-specific requirements
3. **architect-reviewer** validates overall technical architecture

### Phase 3: Quality Framework
1. **test-automation** defines testing strategy and coverage requirements
2. **performance-profiler** sets performance benchmarks and monitoring
3. **security-reviewer** defines security testing and validation requirements

### Phase 4: Documentation Framework
1. **documentation-writer** defines documentation requirements
2. **api-designer** (if applicable) defines API documentation standards
3. **business-analyst** defines user-facing documentation needs

## Quality Gates
- Business requirements validated and complete
- Technical architecture reviewed and approved
- Security requirements identified and addressable
- Testing strategy comprehensive with 100% coverage targets
- Performance benchmarks defined and measurable
- Documentation requirements complete and actionable

```json
{
   "task": "<...>",
   



   "agent_coordination_strategy": {
      "core_agents": [
         "business-analyst",
         "architect-reviewer",
         "security-reviewer"
      ],
      "technology_agent_selection": [
         "python-developer",
         "nodejs-developer",
         "java-developer",
         "golang-developer",
         "rust-developer",
         "react-developer",
         "typescript-developer"
      ],
      "specialist_agent_selection": [
         "database-administrator",
         "api-designer",
         "cloud-architect",
         "devops-engineer",
         "performance-profiler"
      ],
      "quality_agents": [
         "test-automation",
         "documentation-writer"
      ]
   },
   "multi_agent_workflow": {
      "phase_1_requirements_analysis": [
         "business-analyst",
         "architect-reviewer",
         "security-reviewer"
      ],
      "phase_2_technical_specification": [
         "technology_agents",
         "specialist_agents",
         "architect-reviewer"
      ],
      "phase_3_quality_framework": [
         "test-automation",
         "performance-profiler",
         "security-reviewer"
      ],
      "phase_4_documentation_framework": [
         "documentation-writer",
         "api-designer",
         "business-analyst"
      ]
   },
   "quality_gates": [
      "Business requirements validated and complete",
      "Technical architecture reviewed and approved",
      "Security requirements identified and addressable",
      "Testing strategy comprehensive with 100% coverage targets",
      "Performance benchmarks defined and measurable",
      "Documentation requirements complete and actionable"
   ]
}