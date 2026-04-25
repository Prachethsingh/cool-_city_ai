"""
agents/base_agent.py – Abstract base class for all CoolCity AI agents.
"""

import abc
import json
import time
from typing import Any, Dict, Optional


class AgentResult:
    """Standardised output from any agent."""

    def __init__(
        self,
        agent_name: str,
        success: bool,
        data: Dict[str, Any],
        message: str = "",
        error: str = "",
        elapsed_ms: int = 0,
    ):
        self.agent_name = agent_name
        self.success = success
        self.data = data
        self.message = message
        self.error = error
        self.elapsed_ms = elapsed_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
        }

    def __repr__(self):
        return f"<AgentResult agent={self.agent_name} success={self.success}>"


class BaseAgent(abc.ABC):
    """
    Base class every CoolCity AI agent must inherit from.

    Subclasses implement:
        _run(self, **kwargs) -> AgentResult
    """

    name: str = "BaseAgent"
    description: str = ""

    def run(self, **kwargs) -> AgentResult:
        """
        Public entry-point. Times the call and wraps errors gracefully.
        """
        start = time.time()
        try:
            result = self._run(**kwargs)
        except Exception as exc:
            elapsed = int((time.time() - start) * 1000)
            result = AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                error=str(exc),
                elapsed_ms=elapsed,
            )
        result.elapsed_ms = int((time.time() - start) * 1000)
        self._log(result)
        return result

    @abc.abstractmethod
    def _run(self, **kwargs) -> AgentResult:
        """Implement agent logic here. Must return an AgentResult."""

    def _log(self, result: AgentResult):
        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {self.name} ({result.elapsed_ms} ms) - {result.message or result.error}")

    def _ok(self, data: Dict, message: str = "") -> AgentResult:
        return AgentResult(self.name, success=True, data=data, message=message)

    def _fail(self, error: str, data: Dict = None) -> AgentResult:
        return AgentResult(self.name, success=False, data=data or {}, error=error)
