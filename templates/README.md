# Templates Directory

This directory contains reusable templates for ClaudeAgents project workflows and documentation.

## Available Templates

### Atomic PRP Template

**File**: `atomic-prp-template.md`
**Purpose**: Standardized template for atomic Product Requirements Proposals (PRPs)

Atomic PRPs are small, focused tasks (≤5,000 characters) that enforce single-task clarity and enable parallel execution. This template provides the structure for creating consistent, traceable, and actionable atomic PRPs.

#### When to Use

Use this template when:
- Decomposing a large PRP into smaller atomic tasks
- Creating a new standalone task that's part of a larger workflow
- You need a task small enough to complete in one session
- Clear traceability to parent PRPs is required

#### Template Structure

The atomic PRP template includes these sections:

1. **Metadata**: Status, dates, sequence numbering, dependencies, and references
2. **Task Overview**: One-sentence description (max 100 characters)
3. **What This Task Accomplishes**: 3-5 bullet points of concrete outcomes
4. **Prerequisites**: Required PRPs, tools, and knowledge
5. **Implementation Steps**: 5-8 specific, actionable steps
6. **Validation Checklist**: Checkbox items to verify completion
7. **Success Criteria**: Measurable, objective completion criteria
8. **Testing Requirements**: Manual and automated test specifications
9. **Documentation Updates**: Required documentation changes
10. **Next Task**: Link to the following PRP in sequence
11. **Traceability**: Links to parent PRP and sequence information
12. **Notes**: Optional context and considerations

#### How to Use the Template

**Step 1: Copy the Template**
```bash
cp templates/atomic-prp-template.md prp/[sequence-id]-[task-name].md
# Example: cp templates/atomic-prp-template.md prp/008-a-001-create-template.md
```

**Step 2: Fill in Metadata**
- Set Status (usually ACTIVE for new tasks)
- Add creation date (YYYY-MM-DD format)
- Assign sequence number (PARENT-LETTER-NUMBER format)
  - Example: 008-a-001 means PRP 008, atomic series 'a', task 1
- List all dependencies (other PRPs that must complete first)
- Reference the original draft or parent PRP

**Step 3: Define the Task**
- Write a clear, concise Task Overview (one sentence, max 100 chars)
- List 3-5 concrete outcomes in "What This Task Accomplishes"
- Ensure outcomes are specific and measurable

**Step 4: Specify Prerequisites**
- List required PRPs with brief descriptions
- Document required tools (with versions if needed)
- Note any special knowledge or skills required

**Step 5: Write Implementation Steps**
- Break the task into 5-8 specific steps
- Each step should have:
  - Clear title
  - Specific action to take
  - Expected outcome
  - Files that will be affected
- Steps should be sequential and atomic

**Step 6: Define Success Criteria**
- Write 3-4 measurable success criteria
- Each criterion must be objective (no subjective judgments)
- Include how to measure or verify each criterion

**Step 7: Specify Testing**
- Define manual test cases with expected results
- Add automated test requirements if applicable
- Document where test evidence will be stored

**Step 8: List Documentation Updates**
- Identify all documentation that needs changes
- Specify what needs to be added or modified
- Include file paths for clarity

**Step 9: Link to Next Task**
- Reference the next PRP in the sequence
- Leave empty if this is the final task

**Step 10: Complete Traceability**
- Link back to the original draft or parent PRP
- Note sequence position (X of Y total tasks)
- List all related PRPs (dependencies and followers)

**Step 11: Remove Template Comments**
- Delete all HTML comments (<!-- ... -->)
- Keep the structure but remove instructional text

#### Sequence Numbering Convention

Atomic PRP sequences follow this format: `PARENT-LETTER-NUMBER`

**Components**:
- **PARENT**: The parent PRP number (e.g., 008)
- **LETTER**: Atomic series identifier (a, b, c, etc.)
- **NUMBER**: Sequential task number (001, 002, 003, etc.)

**Examples**:
- `008-a-001`: First task in atomic series 'a' of PRP 008
- `008-a-002`: Second task in atomic series 'a' of PRP 008
- `012-b-005`: Fifth task in atomic series 'b' of PRP 012

**Why letters?**: Multiple atomic decompositions of the same parent PRP can coexist. Series 'a' might be the original decomposition, while series 'b' could be an alternative approach.

#### Character Limit Guidance

The 5,000 character limit is a guideline to enforce single-task focus:
- ✅ If your PRP is under 5,000 chars, it's likely focused enough
- ⚠️ If you're approaching 5,000 chars, review for scope creep
- ❌ If you exceed 5,000 chars, split into multiple atomic PRPs

**Tips for staying within limits**:
- Keep implementation steps concise but clear
- Avoid redundant explanations
- Use bullet points instead of paragraphs
- Reference other docs instead of duplicating information
- Focus on "what" and "how", not "why" (that's in the parent PRP)

#### Example

See `atomic-prp-template-example.md` for a complete, filled example using PRP 008-a-001 (the task that created this template).

#### Validation

Before marking an atomic PRP complete, verify:
- [ ] All sections are filled in completely
- [ ] Success criteria are measurable and objective
- [ ] Implementation steps are specific and actionable
- [ ] Dependencies are clearly documented
- [ ] Testing requirements are defined
- [ ] Documentation updates are listed
- [ ] Traceability links are accurate
- [ ] Task is under 5,000 characters (guidance)

## Adding New Templates

When adding new templates to this directory:

1. Create the template file with `.md` extension
2. Include inline instructions as HTML comments
3. Provide a filled example file with `-example.md` suffix
4. Update this README with template documentation
5. Follow the documentation structure used for atomic PRP template above

## Template Maintenance

Templates should be updated when:
- New requirements emerge from actual usage
- Feedback identifies missing sections or unclear instructions
- ClaudeAgents workflow processes change
- Better practices are identified through experience

Document all template changes in commit messages and update version information if templates include version metadata.

---

**Related Documentation**:
- `/prp/instructions.md` - PRP workflow overview
- `/prp/drafts/` - Draft PRPs before decomposition
- `/prp/` - Completed and active PRPs
