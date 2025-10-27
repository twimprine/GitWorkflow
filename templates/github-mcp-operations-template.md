# GitHub MCP Operations Template

## Purpose

This template provides a standardized format for adding GitHub MCP operations to any ClaudeAgents agent. Use this template to ensure consistency across all agents that need GitHub integration capabilities.

## Template Structure

### Section Placement
Insert the GitHub Operations section after "Integration Requirements" and before "Best Practices" in the agent file.

### Standard Template

```markdown
## GitHub Operations

You have access to GitHub MCP tools for:
- [PRIMARY_CAPABILITY_1]
- [PRIMARY_CAPABILITY_2]
- [PRIMARY_CAPABILITY_3]
- [PRIMARY_CAPABILITY_4]
- [PRIMARY_CAPABILITY_5]
Use these tools when working with GitHub repositories for [AGENT_DOMAIN] [OPERATIONS_TYPE].
Available tools use prefix: mcp__Github__

Common GitHub operations for [AGENT_NAME]:
- `[TOOL_1]` - [DESCRIPTION_1]
- `[TOOL_2]` - [DESCRIPTION_2]
- `[TOOL_3]` - [DESCRIPTION_3]
- `[TOOL_4]` - [DESCRIPTION_4]
- `[TOOL_5]` - [DESCRIPTION_5]
- `[TOOL_6]` - [DESCRIPTION_6]
```

## Replacement Variables

### Agent-Specific Variables
- `[AGENT_NAME]`: The exact agent name (e.g., "python-developer", "documentation-writer")
- `[AGENT_DOMAIN]`: The agent's domain expertise (e.g., "Python development", "documentation")
- `[OPERATIONS_TYPE]`: Type of operations (e.g., "operations", "tasks", "activities")

### Capability Variables
- `[PRIMARY_CAPABILITY_1-5]`: 5-6 key GitHub capabilities for this agent type
- Use action-oriented descriptions
- Focus on the agent's specific domain

### Tool Variables
- `[TOOL_1-6]`: Specific GitHub MCP tools most relevant to the agent
- Always use exact tool names with `mcp__Github__` prefix
- Verify tool names against GitHub MCP documentation
- Select 6 most relevant tools for the agent's domain

## Domain-Specific Examples

### Developer Agents
**Capabilities Focus**: Code operations, repository management, PR creation
**Tools**: `get_file_contents`, `create_or_update_file`, `create_pull_request`, `list_commits`, `get_pull_request_files`, `create_branch`

### Review Agents
**Capabilities Focus**: PR review, code analysis, feedback
**Tools**: `get_pull_request`, `get_pull_request_files`, `create_pending_pull_request_review`, `add_comment_to_pending_review`, `submit_pending_pull_request_review`

### Management Agents
**Capabilities Focus**: Issue tracking, project coordination, status monitoring
**Tools**: `list_issues`, `create_issue`, `update_issue`, `add_issue_comment`, `list_pull_requests`, `get_pull_request_status`

### DevOps Agents
**Capabilities Focus**: CI/CD, workflows, releases, deployments
**Tools**: `run_workflow`, `list_workflow_runs`, `get_workflow_run`, `list_workflow_jobs`, `rerun_failed_jobs`, `create_release`

### Documentation Agents
**Capabilities Focus**: Documentation management, README updates, docs site
**Tools**: `get_file_contents`, `create_or_update_file`, `create_pull_request`, `add_issue_comment`, `get_pull_request`, `search_repositories`

## Implementation Examples

### Example 1: Python Developer
```markdown
## GitHub Operations

You have access to GitHub MCP tools for:
- Accessing repository files and code
- Creating and updating pull requests
- Committing code changes
- Managing branches and merges
- Viewing commit history and diffs
Use these tools when working with GitHub repositories for Python development.
Available tools use prefix: mcp__Github__

Common GitHub operations for python-developer:
- `mcp__Github__get_file_contents` - Read Python source files
- `mcp__Github__create_or_update_file` - Commit Python code changes
- `mcp__Github__create_pull_request` - Create PR with Python changes
- `mcp__Github__list_commits` - Review commit history
- `mcp__Github__get_pull_request_files` - Review Python code in PRs
- `mcp__Github__create_branch` - Create feature branches for development
```

### Example 2: Security Reviewer
```markdown
## GitHub Operations

You have access to GitHub MCP tools for:
- Reviewing code changes for security issues
- Creating security-focused PR reviews
- Accessing security scanning results
- Managing security advisories
- Tracking security-related issues
Use these tools when working with GitHub repositories for security review and validation.
Available tools use prefix: mcp__Github__

Common GitHub operations for security-reviewer:
- `mcp__Github__get_pull_request_files` - Review code changes for security
- `mcp__Github__create_pending_pull_request_review` - Start security review
- `mcp__Github__add_comment_to_pending_review` - Add security feedback
- `mcp__Github__list_code_scanning_alerts` - View security scan results
- `mcp__Github__list_secret_scanning_alerts` - Check for exposed secrets
- `mcp__Github__list_repository_security_advisories` - Review advisories
```

## Quality Assurance Checklist

### Before Adding to Agent
- [ ] Verify all tool names against `docs/GITHUB_MCP_USAGE.md`
- [ ] Ensure 5-6 capabilities listed match agent domain
- [ ] Select 6 most relevant tools for the agent
- [ ] Use consistent formatting and structure
- [ ] Check capabilities are action-oriented
- [ ] Verify tools are domain-appropriate

### After Adding to Agent
- [ ] Test that section renders correctly in agent file
- [ ] Verify integration with existing agent structure
- [ ] Confirm no tool name typos or inconsistencies
- [ ] Check that capabilities make sense for agent role
- [ ] Validate against other agents for consistency

## Tool Reference Guidelines

### Tool Selection Criteria
1. **Relevance**: Tools must be directly relevant to agent's domain
2. **Frequency**: Select tools the agent would use most often
3. **Coverage**: Include tools for primary workflows
4. **Completeness**: Cover the full workflow (read, create, update, review)

### Common Tool Categories
- **File Operations**: `get_file_contents`, `create_or_update_file`, `delete_file`
- **Repository Management**: `create_branch`, `fork_repository`, `create_repository`
- **Pull Requests**: `create_pull_request`, `get_pull_request`, `merge_pull_request`
- **Reviews**: `create_pending_pull_request_review`, `add_comment_to_pending_review`, `submit_pending_pull_request_review`
- **Issues**: `create_issue`, `get_issue`, `update_issue`, `list_issues`
- **CI/CD**: `run_workflow`, `list_workflow_runs`, `get_workflow_run`
- **Search**: `search_repositories`, `search_code`, `search_issues`

## Validation Scripts

### Tool Name Validation
```bash
# Validate that all tool names in agent match documentation
./scripts/validate-github-tools.sh agents/[agent-name].md
```

### Consistency Check
```bash
# Check that GitHub operations sections follow template
./scripts/check-github-sections.sh
```

## Future Enhancements

### Template Evolution
- Add new tool categories as GitHub MCP expands
- Refine capability descriptions based on usage patterns
- Create domain-specific sub-templates
- Add automation for template application

### Integration Improvements
- Automated tool validation during agent updates
- Template-based agent generation
- Dynamic tool recommendations based on agent domain
- Integration with agent testing framework

---

*Template Version: 1.0.0*
*Created: 2025-09-26*
*Based on: GitHub MCP implementation (PRP-000-a)*