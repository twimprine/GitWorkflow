"""Main agent implementation."""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Agent:
    """Base agent class implementing standard protocols."""

    def __init__(self, config_path: str = "config.json"):
        """Initialize the agent with configuration.

        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger(self.config["name"])
        self.prompts = self._load_prompts()
        self.logger.info(
            f"Agent initialized: {self.config['name']} v{self.config['version']}"
        )

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load agent configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        with open(config_path, "r") as f:
            return json.load(f)

    def _load_prompts(self) -> Dict[str, str]:
        """Load agent prompts from files.

        Returns:
            Dictionary of prompt name to content
        """
        prompts = {}
        prompt_config = self.config.get("prompts", {})

        for prompt_name in ["system", "examples", "context"]:
            prompt_file = prompt_config.get(prompt_name)
            if prompt_file and Path(prompt_file).exists():
                with open(prompt_file, "r") as f:
                    prompts[prompt_name] = f.read()
                self.logger.info(f"Loaded {prompt_name} prompt from {prompt_file}")
            elif prompt_name == "system":
                # System prompt is required
                self.logger.warning("No system prompt found, using default")
                prompts[prompt_name] = self._get_default_system_prompt()

        return prompts

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt if none specified.

        Returns:
            Default system prompt string
        """
        return f"""You are the {self.config['name']} agent.

Your responsibilities are: {', '.join(self.config.get('capabilities', []))}

You must delegate security issues to security-reviewer agent.
You must delegate architecture issues to architect-reviewer agent.
Provide clear, actionable responses."""

    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an agent action.

        Args:
            request: Request dictionary with action and parameters

        Returns:
            Response dictionary with status and data
        """
        start_time = time.time()
        request_id = request.get("context", {}).get("request_id", "unknown")

        self.logger.info(
            f"Executing request: {request_id} action={request.get('action')}"
        )

        try:
            # Validate request
            self._validate_request(request)

            # Route to appropriate handler
            action = request["action"]
            handler = getattr(self, f"_handle_{action}", None)

            if not handler:
                raise ValueError(f"Unknown action: {action}")

            # Execute handler
            result = await handler(request["parameters"])

            # Build response
            response = {
                "status": "success",
                "data": result,
                "errors": [],
                "metadata": {
                    "request_id": request_id,
                    "execution_time": time.time() - start_time,
                    "agent_version": self.config["version"],
                },
            }

            self.logger.info(
                f"Request completed: {request_id} "
                f"time={response['metadata']['execution_time']:.3f}s"
            )

            return response

        except Exception as e:
            # Categorize error for delegation
            error_category = self._categorize_error(e)

            self.logger.error(
                f"Request failed: {request_id} error={str(e)} "
                f"category={error_category['category']} "
                f"delegate_to={error_category.get('delegate_to')}"
            )

            return {
                "status": "failure",
                "data": {},
                "errors": [
                    {
                        "code": error_category["code"],
                        "category": error_category["category"],
                        "message": str(e),
                        "delegate_to": error_category.get("delegate_to"),
                        "severity": error_category["severity"],
                        "action_required": error_category.get("action_required"),
                        "details": {
                            "action": request.get("action"),
                            "request_id": request_id,
                        },
                    }
                ],
                "metadata": {
                    "request_id": request_id,
                    "execution_time": time.time() - start_time,
                    "agent_version": self.config["version"],
                },
            }

    async def execute_parallel(
        self, requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute multiple requests in parallel.

        Args:
            requests: List of request dictionaries

        Returns:
            List of response dictionaries
        """
        tasks = [self.execute(request) for request in requests]
        return await asyncio.gather(*tasks)

    def _validate_request(self, request: Dict[str, Any]) -> None:
        """Validate incoming request structure.

        Args:
            request: Request dictionary to validate

        Raises:
            ValueError: If request is invalid
        """
        if "action" not in request:
            raise ValueError("Request missing 'action' field")

        if not isinstance(request.get("parameters"), dict):
            request["parameters"] = {}

    async def _handle_example(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Example action handler.

        Args:
            parameters: Action parameters

        Returns:
            Action result
        """
        # Simulate some async work
        await asyncio.sleep(0.1)

        return {"message": "Example action completed", "parameters": parameters}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check.

        Returns:
            Health status dictionary
        """
        return {
            "status": "healthy",
            "agent": self.config["name"],
            "version": self.config["version"],
            "timestamp": time.time(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics.

        Returns:
            Metrics dictionary
        """
        return {
            "agent": self.config["name"],
            "version": self.config["version"],
            "uptime": time.time(),
            "requests_processed": 0,  # Would track in production
            "errors": 0,  # Would track in production
            "avg_response_time": 0.0,  # Would calculate in production
        }

    def _categorize_error(self, error: Exception) -> Dict[str, Any]:
        """Categorize error for proper delegation.

        Args:
            error: The exception to categorize

        Returns:
            Error category information with delegation requirements
        """
        error_str = str(error).lower()

        # Security-related errors
        security_indicators = [
            "auth",
            "token",
            "password",
            "credential",
            "permission",
            "unauthorized",
            "forbidden",
            "injection",
            "xss",
            "csrf",
            "crypto",
            "ssl",
        ]
        if any(indicator in error_str for indicator in security_indicators):
            return {
                "code": "SEC-001",
                "category": "security",
                "delegate_to": "security-reviewer",
                "severity": "critical",
                "action_required": "MUST delegate to security-reviewer agent",
            }

        # Architecture/complexity errors
        architecture_indicators = [
            "complexity",
            "refactor",
            "design",
            "pattern",
            "structure",
            "dependency",
            "coupling",
            "inheritance",
        ]
        if any(indicator in error_str for indicator in architecture_indicators):
            return {
                "code": "ARCH-001",
                "category": "architecture",
                "delegate_to": "architect-reviewer",
                "severity": "high",
                "action_required": "MUST delegate to architect-reviewer agent",
            }

        # Performance errors
        performance_indicators = [
            "timeout",
            "slow",
            "performance",
            "memory",
            "leak",
            "bottleneck",
            "optimization",
        ]
        if any(indicator in error_str for indicator in performance_indicators):
            return {
                "code": "PERF-001",
                "category": "performance",
                "delegate_to": "architect-reviewer",
                "severity": "high",
                "action_required": "MUST delegate to architect-reviewer agent",
            }

        # Default for non-critical errors
        return {
            "code": "LOG-001",
            "category": "logic",
            "severity": "medium",
            "action_required": "Can be handled locally",
        }

    async def delegate_to_agent(
        self, agent_name: str, request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delegate request to specialist agent.

        Args:
            agent_name: Name of specialist agent
            request: Request to delegate

        Returns:
            Specialist agent response

        Note: This is a template - actual implementation would
              use the agent orchestration system
        """
        self.logger.info(
            f"Delegating to specialist: {agent_name} action={request.get('action')}"
        )

        # Include agent context in delegation
        request["context"] = request.get("context", {})
        request["context"]["delegated_from"] = self.config["name"]
        request["context"]["delegation_reason"] = self._get_delegation_reason(
            agent_name
        )

        # Template for delegation
        # In production, this would call the actual specialist agent
        return {
            "status": "delegated",
            "specialist": agent_name,
            "recommendation": "Implement specialist's solution",
            "secure_implementation": "# Specialist-approved code",
        }

    def _get_delegation_reason(self, agent_name: str) -> str:
        """Get reason for delegation to specific agent.

        Args:
            agent_name: Name of the specialist agent

        Returns:
            Reason for delegation
        """
        reasons = {
            "security-reviewer": "Security expertise required",
            "architect-reviewer": "Architecture/complexity review required",
            "data-specialist": "Data handling expertise required",
        }
        return reasons.get(agent_name, "Specialist expertise required")

    def get_system_prompt(self) -> str:
        """Get the agent's system prompt.

        Returns:
            System prompt string
        """
        return self.prompts.get("system", "")
