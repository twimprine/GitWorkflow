# Project Requirements Plan (PRP)

## 1. Overview
- **Purpose:** {{ purpose }}
- **Scope:** {{ scope }}
- **In-Scope Components:** {{ components }}
- **Out-of-Scope:** {{ out_of_scope }}

## 2. Traceability
- **Source File(s):** {{ source_files }}
- **User Stories Map:** 
{{#each user_stories}}
- {{id}}: {{description}}
{{/each}}

## 3. Architecture Summary

## 4. Interfaces (Application/Class)
{{#each code_interfaces}}
### {{name}} ({{package}})
- Description: {{description}}
- Responsibilities: {{responsibilities}}
- Invariants: {{invariants}}
- Methods:
{{#each methods}}
	- {{name}}({{params}}): {{returns}} — {{summary}}
		- Preconditions: {{preconditions}}
		- Postconditions: {{postconditions}}
{{/each}}
{{/each}}

## 5. HTTP API
### 5.1 Endpoints
- **Base Port:** `{{ base_port }}`
- **Endpoints:**
{{#each http.endpoints}}
#### {{method}} {{path}}
- **Summary:** {{summary}}
- **Headers:** {{headers}}
- **Request Schema:** {{request_schema_ref}}
- **Response Schema(s):** {{response_schema_refs}}
- **Status Codes:** {{status_codes}}
- **Constraints:** {{constraints}}
{{/each}}

### 5.2 Environment Variables
{{#each env}}
- `{{name}}` (default: `{{default}}`) — {{description}} {{constraints}}
{{/each}}

## 6. Contracts
{{#each contracts}}
### {{id}} — {{title}}
- **Preconditions:** {{pre}}
- **Postconditions:** {{post}}
- **Invariants:** {{invariants}}
- **Rollback:** {{rollback}}
- **Security Controls:** {{security}}
- **Validation Steps:** {{validation}}
{{/each}}

## 7. Data Schemas
### 7.1 OpenAPI
```yaml
{{ openapi }}
```
