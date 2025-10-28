---
allowed-tools: Task, Read, Grep, Glob, WebSearch, FileRead
argument-hint: [Organize and Consolidate Tasks]
description: Review task list and questions for agent consensus and organize
model: sonnet-20250822
agent: project-manager
---


Task files will be uploaded with the following schema
@templates/prp/draft-prp-001.json

These will be accompanied with files derived from the questions and will appear as follows:

@templates/prp/draft-prp-002.json

Each question will reference where it was from and where the response was found. 

# Tasks
Organize the tasks into a single task list taking into account:
- Dependencies
- Documentation Requirements
- Standards References
- Required Tests
- Required Validations
- Validate against existing standards in the repo
- Validate against existing user stories and requirements in the repo
- Ensure all questions have been answered or marked as needs-input

# Rules
- Improve standards 
- Never regress standards 
- Security is a design feature - non optional
- Each task should be:
  - Atomic
  - Be able to be rolled back 
  - Documented
  - As simple as possible to achieve the tasks
- Ensure all tasks are deterministic and unambiguous
- Ensure all tasks are testable and verifiable
- Ensure all tasks are accounted for in the final synthesis

# Output
@templates/prp/draft-prp-003.json
