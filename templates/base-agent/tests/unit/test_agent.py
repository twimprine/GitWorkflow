"""Unit tests for the base agent."""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, mock_open
from src.agent import Agent


class TestAgent:
    """Test suite for Agent class."""

    @pytest.fixture
    def mock_config(self):
        """Provide mock configuration."""
        return {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test agent",
            "capabilities": ["test"],
            "requirements": {"python": ">=3.8"},
            "performance": {
                "timeout": 30,
                "max_memory": "512MB",
                "max_concurrent": 10
            }
        }

    @pytest.fixture
    def agent(self, mock_config):
        """Create agent instance with mock config."""
        mock_file = mock_open(read_data=json.dumps(mock_config))
        with patch("builtins.open", mock_file):
            return Agent("config.json")

    def test_agent_initialization(self, agent, mock_config):
        """Test agent initializes correctly."""
        assert agent.config["name"] == mock_config["name"]
        assert agent.config["version"] == mock_config["version"]

    def test_load_config(self, mock_config):
        """Test configuration loading."""
        mock_file = mock_open(read_data=json.dumps(mock_config))
        with patch("builtins.open", mock_file):
            agent = Agent("config.json")
            assert agent.config == mock_config

    @pytest.mark.asyncio
    async def test_execute_success(self, agent):
        """Test successful request execution."""
        request = {
            "action": "example",
            "parameters": {"test": "value"},
            "context": {"request_id": "test-123"}
        }

        response = await agent.execute(request)

        assert response["status"] == "success"
        assert "data" in response
        assert response["metadata"]["request_id"] == "test-123"
        assert response["metadata"]["agent_version"] == "1.0.0"
        assert "execution_time" in response["metadata"]

    @pytest.mark.asyncio
    async def test_execute_missing_action(self, agent):
        """Test execution with missing action."""
        request = {
            "parameters": {"test": "value"}
        }

        response = await agent.execute(request)

        assert response["status"] == "failure"
        assert len(response["errors"]) > 0
        assert "missing 'action'" in response["errors"][0]["message"]

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, agent):
        """Test execution with unknown action."""
        request = {
            "action": "unknown",
            "parameters": {}
        }

        response = await agent.execute(request)

        assert response["status"] == "failure"
        assert len(response["errors"]) > 0
        assert "Unknown action" in response["errors"][0]["message"]

    @pytest.mark.asyncio
    async def test_execute_parallel(self, agent):
        """Test parallel request execution."""
        requests = [
            {"action": "example", "parameters": {"id": 1}},
            {"action": "example", "parameters": {"id": 2}},
            {"action": "example", "parameters": {"id": 3}}
        ]

        responses = await agent.execute_parallel(requests)

        assert len(responses) == 3
        assert all(r["status"] == "success" for r in responses)

    def test_validate_request_valid(self, agent):
        """Test request validation with valid request."""
        request = {
            "action": "test",
            "parameters": {"key": "value"}
        }
        # Should not raise
        agent._validate_request(request)

    def test_validate_request_missing_action(self, agent):
        """Test request validation with missing action."""
        request = {"parameters": {}}

        with pytest.raises(ValueError) as exc_info:
            agent._validate_request(request)

        assert "missing 'action'" in str(exc_info.value)

    def test_validate_request_no_parameters(self, agent):
        """Test request validation creates empty parameters."""
        request = {"action": "test"}
        agent._validate_request(request)
        assert request["parameters"] == {}

    @pytest.mark.asyncio
    async def test_handle_example(self, agent):
        """Test example handler."""
        result = await agent._handle_example({"test": "params"})

        assert "message" in result
        assert result["parameters"] == {"test": "params"}

    @pytest.mark.asyncio
    async def test_health_check(self, agent):
        """Test health check endpoint."""
        health = await agent.health_check()

        assert health["status"] == "healthy"
        assert health["agent"] == "test-agent"
        assert health["version"] == "1.0.0"
        assert "timestamp" in health

    def test_get_metrics(self, agent):
        """Test metrics endpoint."""
        metrics = agent.get_metrics()

        assert metrics["agent"] == "test-agent"
        assert metrics["version"] == "1.0.0"
        assert "uptime" in metrics
        assert "requests_processed" in metrics
        assert "errors" in metrics
        assert "avg_response_time" in metrics

    @pytest.mark.asyncio
    async def test_execute_with_exception(self, agent):
        """Test execution handles exceptions properly."""
        with patch.object(agent, "_validate_request", side_effect=Exception("Test error")):
            request = {"action": "test", "parameters": {}}
            response = await agent.execute(request)

            assert response["status"] == "failure"
            assert "Test error" in response["errors"][0]["message"]
            assert response["errors"][0]["code"] == "EXECUTION_ERROR"

    @pytest.mark.asyncio
    async def test_execute_without_request_id(self, agent):
        """Test execution without request ID uses 'unknown'."""
        request = {"action": "example", "parameters": {}}
        response = await agent.execute(request)

        assert response["metadata"]["request_id"] == "unknown"