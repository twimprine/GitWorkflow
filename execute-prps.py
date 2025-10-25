#!/usr/bin/env python3
"""
Autonomous PRP Batch Processor

Simple orchestrator that processes PRPs from queue to completion.
Just activate your env and run: python execute-prps.py

Features:
- Automatic queue processing
- Rate limiting to control costs
- State management for resume
- Clear progress reporting
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")
    print("Install with: pip install python-dotenv")

# Configuration
class Config:
    """Configuration with sensible defaults, overridable via .env file"""
    PROJECT_ROOT = Path(__file__).parent
    QUEUE_DIR = PROJECT_ROOT / "prp" / "queue"
    DRAFTS_DIR = PROJECT_ROOT / "prp" / "drafts"
    ACTIVE_DIR = PROJECT_ROOT / "prp" / "active"
    COMPLETED_DIR = PROJECT_ROOT / "prp" / "completed"
    PROCESSED_DIR = QUEUE_DIR / "processed"
    FAILED_DIR = QUEUE_DIR / "failed"
    LOGS_DIR = PROJECT_ROOT / "logs"
    BATCH_DIR = PROJECT_ROOT / "batch"
    SCRIPTS_DIR = PROJECT_ROOT / "scripts"

    # API Key (REQUIRED - from .env or environment)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

    # Rate limiting (from .env with defaults)
    MAX_BATCHES_PER_HOUR = int(os.getenv("MAX_BATCHES_PER_HOUR", "1"))
    MIN_BATCH_INTERVAL_MINUTES = int(os.getenv("MIN_BATCH_INTERVAL_MINUTES", "60"))

    # Polling (from .env with defaults)
    QUEUE_CHECK_INTERVAL_SECONDS = int(os.getenv("QUEUE_CHECK_INTERVAL_SECONDS", "300"))
    BATCH_POLL_INTERVAL_SECONDS = int(os.getenv("BATCH_POLL_INTERVAL_SECONDS", "60"))
    BATCH_TIMEOUT_HOURS = int(os.getenv("BATCH_TIMEOUT_HOURS", "3"))

    # State files
    STATE_FILE = LOGS_DIR / "prp-orchestrator-state.json"
    LOG_FILE = LOGS_DIR / f"prp-orchestrator-{ENVIRONMENT}.log"

    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not set! Create .env file with your API key.\n"
                "See .env.example for template."
            )


class State:
    """Persistent state management"""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.data = self._load()

    def _load(self) -> Dict:
        """Load state from disk"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "last_batch_time": None,
            "processed_files": [],
            "current_processing": None,
            "batch_count_1h": 0,
            "batch_times": []
        }

    def save(self):
        """Save state to disk"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def can_submit_batch(self, config: Config) -> tuple[bool, str]:
        """Check if we can submit a new batch based on rate limits"""
        now = datetime.now()

        # Clean old batch times (older than 1 hour)
        one_hour_ago = now - timedelta(hours=1)
        self.data["batch_times"] = [
            t for t in self.data["batch_times"]
            if datetime.fromisoformat(t) > one_hour_ago
        ]

        # Check hourly limit
        if len(self.data["batch_times"]) >= config.MAX_BATCHES_PER_HOUR:
            oldest = datetime.fromisoformat(self.data["batch_times"][0])
            wait_until = oldest + timedelta(hours=1)
            wait_minutes = int((wait_until - now).total_seconds() / 60)
            return False, f"Rate limit: {len(self.data['batch_times'])} batches in last hour. Wait {wait_minutes} minutes."

        # Check minimum interval
        if self.data["last_batch_time"]:
            last_batch = datetime.fromisoformat(self.data["last_batch_time"])
            min_interval = timedelta(minutes=config.MIN_BATCH_INTERVAL_MINUTES)
            next_allowed = last_batch + min_interval

            if now < next_allowed:
                wait_minutes = int((next_allowed - now).total_seconds() / 60)
                return False, f"Minimum interval: Wait {wait_minutes} minutes since last batch."

        return True, "OK"

    def record_batch_submission(self):
        """Record that a batch was submitted"""
        now = datetime.now().isoformat()
        self.data["last_batch_time"] = now
        self.data["batch_times"].append(now)
        self.data["batch_count_1h"] = len(self.data["batch_times"])
        self.save()

    def mark_processed(self, filename: str):
        """Mark a file as successfully processed"""
        if filename not in self.data["processed_files"]:
            self.data["processed_files"].append(filename)
        self.data["current_processing"] = None
        self.save()

    def set_current(self, filename: Optional[str]):
        """Set currently processing file"""
        self.data["current_processing"] = filename
        self.save()


class Logger:
    """Simple logger"""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """Log message to file and console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"

        print(log_line)

        with open(self.log_file, 'a') as f:
            f.write(log_line + "\n")


class PRPOrchestrator:
    """Main orchestrator for batch PRP processing"""

    def __init__(self):
        self.config = Config()
        self.state = State(self.config.STATE_FILE)
        self.logger = Logger(self.config.LOG_FILE)
        self._setup_directories()

    def _setup_directories(self):
        """Ensure all required directories exist"""
        for dir_path in [
            self.config.QUEUE_DIR,
            self.config.DRAFTS_DIR,
            self.config.ACTIVE_DIR,
            self.config.COMPLETED_DIR,
            self.config.PROCESSED_DIR,
            self.config.FAILED_DIR,
            self.config.LOGS_DIR,
            self.config.BATCH_DIR
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def run_script(self, script_name: str, *args) -> subprocess.CompletedProcess:
        """Run a bash script with arguments"""
        script_path = self.config.SCRIPTS_DIR / script_name

        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        # Make executable
        script_path.chmod(0o755)

        cmd = [str(script_path)] + list(args)
        self.logger.log(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.config.PROJECT_ROOT
        )

        if result.returncode != 0:
            self.logger.log(f"Script failed: {result.stderr}", "ERROR")
            raise RuntimeError(f"Script failed: {script_name}")

        return result

    def get_queued_files(self) -> List[Path]:
        """Get list of files in queue (sorted by modification time)"""
        files = [
            f for f in self.config.QUEUE_DIR.iterdir()
            if f.is_file() and f.suffix == '.md' and f.name not in self.state.data["processed_files"]
        ]
        return sorted(files, key=lambda f: f.stat().st_mtime)

    def process_definition(self, def_file: Path):
        """Process a single definition file through all phases"""
        self.logger.log(f"Processing: {def_file.name}")
        self.state.set_current(def_file.name)

        try:
            # Check if PRPs already exist in active/ (skip regeneration)
            existing_prps = list(self.config.ACTIVE_DIR.glob("*.md"))
            if existing_prps:
                self.logger.log(f"Found {len(existing_prps)} existing PRPs in prp/active/")
                self.logger.log("Skipping generation phases (PRPs already exist)")
                self.logger.log(f"✓ PRPs generated from: {def_file.name}")
                self.logger.log(f"  Ready for execution: {len(existing_prps)} PRPs in prp/active/")
                return  # Skip to Phase 6 which is handled by run-autonomous-workflow.sh

            # Phase 1: Collect context
            self.logger.log("Phase 1: Collecting context...")
            context_file = self.config.BATCH_DIR / f"{def_file.stem}-context.json"
            self.run_script(
                "collect-prp-context.sh",
                "--prp-file", str(def_file),
                "--output", str(context_file),
                "--verbose"
            )

            # Phase 2: Create draft request
            self.logger.log("Phase 2: Creating draft batch request...")
            draft_request = self.config.BATCH_DIR / f"{def_file.stem}-draft-request.jsonl"
            self.run_script(
                "create-batch-request.sh",
                "--context", str(context_file),
                "--phase", "draft",
                "--output", str(draft_request)
            )

            # Check rate limit before submitting
            can_submit, reason = self.state.can_submit_batch(self.config)
            if not can_submit:
                self.logger.log(f"Rate limit check: {reason}", "WARN")
                self.logger.log(f"Will retry {def_file.name} later")
                return  # Don't mark as processed, will retry later

            # Phase 3: Submit draft batch
            self.logger.log("Phase 3: Submitting draft batch to API...")
            draft_results = self.config.BATCH_DIR / f"{def_file.stem}-draft-results"
            self.run_script(
                "submit-batch.sh",
                "--request", str(draft_request),
                "--output-dir", str(draft_results),
                "--api-key", self.config.ANTHROPIC_API_KEY,
                "--poll-interval", str(self.config.BATCH_POLL_INTERVAL_SECONDS),
                "--timeout", str(self.config.BATCH_TIMEOUT_HOURS * 3600)
            )
            self.state.record_batch_submission()

            # Find generated draft PRP
            draft_prp = None
            for f in draft_results.iterdir():
                if f.suffix == '.md' and 'prp-' in f.name:
                    draft_prp = f
                    break

            if not draft_prp:
                raise FileNotFoundError("No draft PRP generated from batch")

            # Move draft to drafts directory
            final_draft = self.config.DRAFTS_DIR / draft_prp.name
            draft_prp.rename(final_draft)
            self.logger.log(f"Draft created: {final_draft.name}")

            # Phase 4: Create generate request
            self.logger.log("Phase 4: Creating generate batch request...")
            gen_context = self.config.BATCH_DIR / f"{def_file.stem}-gen-context.json"
            self.run_script(
                "collect-prp-context.sh",
                "--prp-file", str(final_draft),
                "--output", str(gen_context),
                "--verbose"
            )

            gen_request = self.config.BATCH_DIR / f"{def_file.stem}-gen-request.jsonl"
            self.run_script(
                "create-batch-request.sh",
                "--context", str(gen_context),
                "--phase", "generate",
                "--output", str(gen_request)
            )

            # Check rate limit again
            can_submit, reason = self.state.can_submit_batch(self.config)
            if not can_submit:
                self.logger.log(f"Rate limit check: {reason}", "WARN")
                self.logger.log(f"Draft created, will generate later: {final_draft.name}")
                return  # Draft is saved, will continue later

            # Phase 5: Submit generate batch
            self.logger.log("Phase 5: Submitting generate batch to API...")
            gen_results = self.config.BATCH_DIR / f"{def_file.stem}-gen-results"
            self.run_script(
                "submit-batch.sh",
                "--request", str(gen_request),
                "--output-dir", str(gen_results),
                "--api-key", self.config.ANTHROPIC_API_KEY,
                "--poll-interval", str(self.config.BATCH_POLL_INTERVAL_SECONDS),
                "--timeout", str(self.config.BATCH_TIMEOUT_HOURS * 3600)
            )
            self.state.record_batch_submission()

            # Find generated PRP(s)
            generated_prps = [f for f in gen_results.iterdir() if f.suffix == '.md']

            if not generated_prps:
                raise FileNotFoundError("No PRPs generated from batch")

            # Move PRPs to active directory
            for prp in generated_prps:
                final_prp = self.config.ACTIVE_DIR / prp.name
                prp.rename(final_prp)
                self.logger.log(f"PRP ready for implementation: {final_prp.name}")

            # Phases 1-5 complete - PRPs are ready for execution
            # Note: Phase 6 (execution) is handled externally by run-autonomous-workflow.sh
            # which calls Claude Code for each PRP
            self.logger.log(f"✓ PRPs generated from: {def_file.name}")
            self.logger.log(f"  Ready for execution: {len(generated_prps)} PRPs in prp/active/")
            self.logger.log(f"  Note: Definition remains in queue until all PRPs complete")

        except Exception as e:
            self.logger.log(f"Failed to process {def_file.name}: {e}", "ERROR")

            # Move to failed directory with error log
            failed = self.config.FAILED_DIR / def_file.name
            error_log = self.config.FAILED_DIR / f"{def_file.stem}-error.txt"

            def_file.rename(failed)
            with open(error_log, 'w') as f:
                f.write(f"Failed at: {datetime.now()}\n")
                f.write(f"Error: {str(e)}\n")

            self.state.set_current(None)
            raise

    def run_once(self):
        """Process all queued items once and exit"""
        self.logger.log("=== Starting batch PRP processing (run once) ===")

        queued = self.get_queued_files()

        if not queued:
            self.logger.log("No files in queue")
            return

        self.logger.log(f"Found {len(queued)} files in queue")

        for def_file in queued:
            try:
                self.process_definition(def_file)
            except Exception as e:
                self.logger.log(f"Continuing with next file after error", "WARN")
                continue

        self.logger.log("=== Batch processing complete ===")

    def run_daemon(self):
        """Run continuously, monitoring queue"""
        self.logger.log("=== Starting PRP orchestrator in daemon mode ===")
        self.logger.log(f"Queue directory: {self.config.QUEUE_DIR}")
        self.logger.log(f"Check interval: {self.config.QUEUE_CHECK_INTERVAL_SECONDS}s")
        self.logger.log(f"Rate limit: {self.config.MAX_BATCHES_PER_HOUR} batches/hour")

        try:
            while True:
                queued = self.get_queued_files()

                if queued:
                    self.logger.log(f"Found {len(queued)} files in queue")

                    for def_file in queued:
                        try:
                            self.process_definition(def_file)
                        except Exception:
                            continue  # Already logged, continue with next
                else:
                    self.logger.log("Queue empty, waiting...")

                time.sleep(self.config.QUEUE_CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            self.logger.log("Shutting down gracefully...")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Autonomous PRP Batch Processor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python execute-prps.py                    # Process queue once and exit
  python execute-prps.py --daemon           # Run continuously
  python execute-prps.py --status           # Show current status
        """
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in daemon mode (continuous monitoring)"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status and exit"
    )

    args = parser.parse_args()

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    orchestrator = PRPOrchestrator()

    if args.status:
        # Show status
        print(f"\n=== PRP Orchestrator Status ===")
        print(f"Queue directory: {orchestrator.config.QUEUE_DIR}")
        print(f"Queued: {len(orchestrator.get_queued_files())} files")
        print(f"Processed: {len(orchestrator.state.data['processed_files'])} files")
        print(f"Current: {orchestrator.state.data['current_processing'] or 'None'}")
        print(f"Last batch: {orchestrator.state.data['last_batch_time'] or 'Never'}")
        print(f"Batches (1h): {orchestrator.state.data['batch_count_1h']}")
        can_submit, reason = orchestrator.state.can_submit_batch(orchestrator.config)
        print(f"Can submit: {can_submit} ({reason})")
        print()
        return

    if args.daemon:
        orchestrator.run_daemon()
    else:
        orchestrator.run_once()


if __name__ == "__main__":
    main()
