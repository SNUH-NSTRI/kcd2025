"""Multi-Agent System Package.

This package provides a registry of intelligent agents for different
analytical tasks in the RWE Clinical Trial Emulation platform.

Available Agents:
- StatisticianAgent: PSM + Survival Analysis with LLM interpretation

Usage:
    from agents import get_agent, list_agents

    agent = get_agent("statistician")
    result = await agent.run(nct_id="NCT03389555", medication="hydrocortisone")
"""

from __future__ import annotations

from typing import Dict, Optional

from agents.base import BaseAgent, AgentResult, AgentStatus

# Agent registry will be populated as agents are imported
_AGENT_REGISTRY: Dict[str, type[BaseAgent]] = {}


def register_agent(agent_class: type[BaseAgent]) -> type[BaseAgent]:
    """Decorator to register an agent class.

    Args:
        agent_class: Agent class to register

    Returns:
        Same agent class (passthrough)
    """
    # Create instance to get name
    instance = agent_class()
    _AGENT_REGISTRY[instance.name] = agent_class
    return agent_class


def get_agent(agent_name: str) -> Optional[BaseAgent]:
    """Get an agent instance by name.

    Args:
        agent_name: Name of the agent (e.g., "statistician")

    Returns:
        Instance of the requested agent, or None if not found
    """
    agent_class = _AGENT_REGISTRY.get(agent_name)
    if agent_class:
        return agent_class()
    return None


def list_agents() -> list[Dict[str, str]]:
    """List all registered agents.

    Returns:
        List of dicts with agent metadata (name, description, version)
    """
    agents = []
    for agent_class in _AGENT_REGISTRY.values():
        instance = agent_class()
        agents.append(instance.get_metadata())
    return agents


# Import agents to register them
# Note: Import order matters - base classes first
try:
    from agents.statistician import StatisticianAgent
except ImportError:
    # Allow package to load even if statistician dependencies not installed
    pass


__all__ = [
    "BaseAgent",
    "AgentResult",
    "AgentStatus",
    "register_agent",
    "get_agent",
    "list_agents",
]
