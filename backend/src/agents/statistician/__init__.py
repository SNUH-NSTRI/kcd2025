"""Statistician Agent package.

This package provides automated PSM (Propensity Score Matching) + Survival Analysis
using LangGraph workflow orchestration and LLM-powered parameter recommendation.

Main exports:
    - StatisticianAgent: BaseAgent implementation
    - create_statistician_graph: LangGraph workflow factory
    - PSMSurvivalWorkflow: Statistical analysis orchestrator

Usage:
    >>> from agents.statistician import StatisticianAgent
    >>> agent = StatisticianAgent()
    >>> result = await agent.run(nct_id="NCT03389555", medication="hydrocortisone")
"""

from agents.statistician.agent import StatisticianAgent
from agents.statistician.graph import (
    StatisticianState,
    create_statistician_graph,
    load_prompt_templates,
)
from agents.statistician.workflow import PSMSurvivalWorkflow

__all__ = [
    "StatisticianAgent",
    "StatisticianState",
    "create_statistician_graph",
    "load_prompt_templates",
    "PSMSurvivalWorkflow",
]
