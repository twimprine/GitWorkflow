# PRP Orchestrator Architecture

This document visualizes the current Python orchestrator (`execute-prps.py`) and how it interacts with shell scripts and project folders.

## Class diagram

```mermaid
classDiagram
    class Config {
      +PROJECT_ROOT: Path
      +QUEUE_DIR: Path
      +DRAFTS_DIR: Path
      +ACTIVE_DIR: Path
      +COMPLETED_DIR: Path
      +PROCESSED_DIR: Path
      +FAILED_DIR: Path
      +LOGS_DIR: Path
      +BATCH_DIR: Path
      +SCRIPTS_DIR: Path
      +ANTHROPIC_API_KEY: str
      +ENVIRONMENT: str
      +MAX_BATCHES_PER_HOUR: int
      +MIN_BATCH_INTERVAL_MINUTES: int
      +QUEUE_CHECK_INTERVAL_SECONDS: int
      +BATCH_POLL_INTERVAL_SECONDS: int
      +BATCH_TIMEOUT_HOURS: int
      +STATE_FILE: Path
      +LOG_FILE: Path
      +validate(): void
    }

    class State {
      -state_file: Path
      -data: Dict
      +save(): void
      +can_submit_batch(config): (bool, str)
      +record_batch_submission(): void
      +mark_processed(filename): void
      +set_current(filename): void
    }

    class Logger {
      -log_file: Path
      +log(message, level): void
    }

    class PRPOrchestrator {
      -config: Config
      -state: State
      -logger: Logger
      +run_once(): void
      +run_daemon(): void
      +process_definition(def_file: Path): void
      +get_queued_files(): List[Path]
      +run_script(script_name, args): CompletedProcess
    }

    class ScriptCollect {
      <<script>>
      name: collect-prp-context.sh
    }
    class ScriptCreate {
      <<script>>
      name: create-batch-request.sh
    }
    class ScriptSubmit {
      <<script>>
      name: submit-batch.sh
    }
    class RunnerAutonomous {
      <<script>>
      name: run-autonomous-workflow.sh
    }

    PRPOrchestrator --> Config : has
    PRPOrchestrator --> State : maintains
    PRPOrchestrator --> Logger : logs to
    State --> Config : uses
    PRPOrchestrator ..> ScriptCollect : calls
    PRPOrchestrator ..> ScriptCreate : calls
    PRPOrchestrator ..> ScriptSubmit : calls
    PRPOrchestrator ..> RunnerAutonomous : phase 6 executor
```

## Per-definition processing flow

This is the flow inside `PRPOrchestrator.process_definition(def_file)`.

```mermaid
flowchart TD
  Start[Start processing definition] --> CheckActive{PRPs exist in prp/active?}
  CheckActive -- Yes --> SkipGen[Skip phases 1 to 5; PRPs already ready] --> End
  CheckActive -- No --> P1[Phase 1: collect-prp-context.sh to context.json]
  P1 --> P2[Phase 2: create-batch-request.sh draft to draft-request.jsonl]
  P2 --> Rate1{Rate limit OK?}
  Rate1 -- No --> Defer1[Log and retry later]
  Defer1 --> End
  Rate1 -- Yes --> P3[Phase 3: submit-batch.sh draft to draft-results]
  P3 --> FindDraft{Draft PRP found?}
  FindDraft -- No --> Err1[Error: no draft PRP]
  Err1 --> End
  FindDraft -- Yes --> MoveDraft[Move draft to prp/drafts]
  MoveDraft --> P4a[Phase 4: collect-prp-context.sh on draft to gen-context.json]
  P4a --> P4b[create-batch-request.sh generate to gen-request.jsonl]
  P4b --> Rate2{Rate limit OK?}
  Rate2 -- No --> Defer2[Log and generate later]
  Defer2 --> End
  Rate2 -- Yes --> P5[Phase 5: submit-batch.sh generate to gen-results]
  P5 --> FindGen{Generated PRPs found?}
  FindGen -- No --> Err2[Error: no generated PRPs]
  Err2 --> End
  FindGen -- Yes --> MoveActive[Move PRPs to prp/active]
  MoveActive --> Note6[Phase 6 execution via run-autonomous-workflow.sh]
  Note6 --> End[Done]
```

## Daemon loop (queue processing)

This shows `run_daemon()` polling the queue and invoking the per-definition flow.

```mermaid
sequenceDiagram
  participant User as Operator or CI
  participant Orchestrator as PRPOrchestrator
  participant Queue as prp/queue
  participant Scripts as scripts dir
  participant Active as prp/active

  User->>Orchestrator: start daemon
  loop every QUEUE_CHECK_INTERVAL_SECONDS
    Orchestrator->>Queue: get_queued_files()
    alt files found
      Orchestrator->>Orchestrator: process_definition(file)
      Orchestrator->>Scripts: collect-prp-context.sh
      Orchestrator->>Scripts: create-batch-request.sh (draft)
      Orchestrator->>Scripts: submit-batch.sh (draft)
      Orchestrator->>Scripts: collect-prp-context.sh (generate)
      Orchestrator->>Scripts: create-batch-request.sh (generate)
      Orchestrator->>Scripts: submit-batch.sh (generate)
      Scripts-->>Orchestrator: results
      Orchestrator->>Active: move generated PRPs to prp/active
    else no files
      Orchestrator->>Orchestrator: log: Queue empty
    end
  end
```

## Folder roles (current)

- prp/queue: Markdown definitions waiting to be processed (input to process_definition)
- batch: Temporary working outputs (context JSON, request JSONL, results folders)
- prp/drafts: Draft PRP created after the draft phase
- prp/active: Final generated PRPs, ready for execution by run-autonomous-workflow.sh
- prp/completed: Destination after execution (handled outside this script)
- prp/failed: Definitions moved here on errors, with an error txt
- logs: Orchestrator logs and state JSON
- scripts: Shell scripts invoked by the orchestrator

## Rate limiting behavior

- Enforced twice: before submitting the draft batch and before submitting the generate batch.
- State keeps a sliding window of the last hour to cap MAX_BATCHES_PER_HOUR.
- Also enforces a minimum interval (MIN_BATCH_INTERVAL_MINUTES) between submissions.
