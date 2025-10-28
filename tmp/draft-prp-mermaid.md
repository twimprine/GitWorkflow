```mermaid
flowchart TD
  subgraph Draft PRP Processing
    direction TB
    A(STDIN) --> C[Draft PRP Input]
    B(Markdown Files) --> C
    subgraph PRP Batch Builder
        direction TB
        C --> W[Create Request System Prompt]
        C --> D[Attach docs/]
        C --> E[Attach contracts/]
        C --> G[Attach schemas/]
        C --> H[Attach api/]
        C --> I[Attach templates/]
        C --> J[Attach draft-prp instructions]
        C --> K[Attach project CLAUDE.md]
        C --> L[Attach global CLAUDE.md]

        G --> F[Build PRP Batch Request]
        D --> F
        E --> F
        J --> F
        H --> F
        I --> F
        W --> F
        K --> F
        L --> F
        F --> X[Output draft-request.jsonl]
    end
    subgraph PRP Orchestrator
        direction TB
        X --> Z[Attach task template]
        Z --> AA[Create Architect Prompt]
        Z --> AB[Create Project Manager Prompt]
        Z --> AC[Create Developer Prompt]
        Z --> AD[Create Security Engineer Prompt]
        Z --> AE[Create QA Engineer Prompt]
        Z --> AF[Create Final Synthesis Prompt]
        Z --> AG[Create Accessibility Engineer Prompt]
        Z --> AH[Create UX Engineer Prompt]
        Z --> AI[Create Compliance Officer Prompt]
        Z --> AJ[Create DevOps Engineer Prompt]
        Z --> AK[Create API Engineer Prompt]
        Z --> AL[Create Data Engineer Prompt]
        Z --> AM[Create Business Analyst Prompt]
        Z --> AN[Create Documentation Developer Prompt]
        Z --> AO[Create Support Reliability Engineer Prompt]
        Z --> AP[Create Performance Engineer Prompt]
        Z --> AR[Create Testing Engineer Prompt]

        AA --> BA[Create Batch]
        AB --> BA
        AC --> BA
        AD --> BA
        AE --> BA
        AF --> BA
        AG --> BA
        AH --> BA
        AI --> BA
        AJ --> BA
        AK --> BA
        AL --> BA
        AM --> BA
        AN --> BA
        AO --> BA
        AP --> BA
        AR --> BA

        BA --> BB[Output gen-request.jsonl]
        BB --> BC[Submit to Anthropic Batch API]
        BC --> BD[Poll for Results]
        BD --> BE[Attach results to agent outputs]
        BE --> BA
        BE --> BF[Output gen-results]

    end
  end