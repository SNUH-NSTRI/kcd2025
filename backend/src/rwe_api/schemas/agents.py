"""Pydantic schemas for Multi-Agent System API.

This module defines the API contract for agent execution endpoints.
These schemas ensure type safety and validation for all agent requests/responses.
"""

from __future__ import annotations

from typing import Optional, Any, Dict, List
from enum import Enum
from pydantic import BaseModel, Field, validator
import re


class AgentStatus(str, Enum):
    """Agent execution status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRunRequest(BaseModel):
    """Request to run a specific agent.

    Attributes:
        agent_name: Name of the agent to run (e.g., "statistician")
        nct_id: NCT trial identifier (format: NCT########)
        medication: Medication name (will be sanitized for file paths)
        config_overrides: Optional configuration overrides for the agent
    """
    agent_name: str = Field(..., description="Agent identifier (e.g., 'statistician')")
    nct_id: str = Field(..., description="NCT trial ID (e.g., 'NCT03389555')")
    medication: str = Field(..., description="Medication name (e.g., 'hydrocortisone na succ.')")
    config_overrides: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional configuration overrides"
    )

    @validator('nct_id')
    def validate_nct_id(cls, v):
        """Validate NCT ID format."""
        if not v or not v.startswith("NCT"):
            raise ValueError(f"NCT ID must start with 'NCT', got: {v}")
        if not re.match(r'^NCT\d{8}$', v):
            raise ValueError(f"NCT ID must be in format NCT######## (8 digits), got: {v}")
        return v

    @validator('medication')
    def validate_medication(cls, v):
        """Validate medication name is not empty."""
        if not v or not v.strip():
            raise ValueError("Medication name cannot be empty")
        return v.strip()

    @validator('agent_name')
    def validate_agent_name(cls, v):
        """Validate agent name is alphanumeric."""
        if not v or not v.strip():
            raise ValueError("Agent name cannot be empty")
        if not re.match(r'^[a-z_]+$', v):
            raise ValueError(f"Agent name must be lowercase alphanumeric with underscores, got: {v}")
        return v.strip()


class AgentRunResponse(BaseModel):
    """Response after submitting an agent execution request.

    Attributes:
        job_id: Unique identifier for tracking this job
        agent_name: Name of the agent being executed
        status: Current job status (typically "pending" initially)
        message: Human-readable status message
    """
    job_id: str = Field(..., description="Unique job identifier for status polling")
    agent_name: str = Field(..., description="Name of the agent")
    status: AgentStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Human-readable message")


class MatchingMethodComparison(BaseModel):
    """Comparison results for a single matching method."""
    method_name: str = Field(..., description="Method name (psm, psm_caliper, mahalanobis, iptw)")
    n_matched: int = Field(..., description="Number of matched pairs (or total for IPTW)")
    mean_smd: float = Field(..., description="Mean standardized mean difference across covariates")
    balanced_pct: float = Field(..., description="Percentage of covariates with SMD < 0.1")
    smd_details: Optional[Dict[str, float]] = Field(None, description="SMD values for each covariate")


class JobStatusResponse(BaseModel):
    """Response for job status check.

    Attributes:
        job_id: The job identifier
        agent_name: Name of the agent
        status: Current execution status
        progress: Optional progress information (e.g., "Running Node 2/4")
        result: Optional result data when status is COMPLETED
        error: Optional error message when status is FAILED
        created_at: Job creation timestamp
        updated_at: Last update timestamp
        method_comparisons: Optional list of method comparison results (for statistician agent)
        selected_method: Optional selected matching method (for statistician agent)
        method_reasoning: Optional LLM reasoning for method selection
    """
    job_id: str
    agent_name: str
    status: AgentStatus
    progress: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    method_comparisons: Optional[List[MatchingMethodComparison]] = None
    selected_method: Optional[str] = None
    method_reasoning: Optional[str] = None
    updated_at: Optional[str] = None


class AgentMetadata(BaseModel):
    """Metadata about an available agent.

    Attributes:
        name: Unique agent identifier
        description: Human-readable description
        version: Semantic version string
        status: Whether agent is enabled/disabled
    """
    name: str
    description: str
    version: str
    status: str = "enabled"


class AgentListResponse(BaseModel):
    """Response listing all available agents.

    Attributes:
        agents: List of agent metadata
        total: Total number of agents
    """
    agents: List[AgentMetadata]
    total: int


class AgentResultFile(BaseModel):
    """Metadata about an output file generated by an agent.

    Attributes:
        filename: Name of the file
        path: Relative path from output directory
        size_bytes: File size in bytes
        mime_type: MIME type of the file
    """
    filename: str
    path: str
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None


class AgentResult(BaseModel):
    """Detailed result from a completed agent execution.

    Attributes:
        agent_name: Name of the agent
        status: Execution status
        output_dir: Directory where results were saved
        files: List of generated files
        summary: High-level summary of results
        metadata: Additional agent-specific metadata
    """
    agent_name: str
    status: AgentStatus
    output_dir: str
    files: List[AgentResultFile] = []
    summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# ============================================================================
# Hybrid Trialist Schemas
# ============================================================================

class TrialistHybridRequest(BaseModel):
    """Request to parse clinical trial criteria using hybrid trialist.
    
    Attributes:
        raw_criteria: Raw trial criteria text (inclusion/exclusion)
        nct_id: Optional NCT trial identifier for result storage
    """
    raw_criteria: str = Field(..., description="Raw clinical trial criteria text", min_length=1)
    nct_id: Optional[str] = Field(default=None, description="Optional NCT ID for result storage")

    @validator('nct_id')
    def validate_nct_id_optional(cls, v):
        """Validate NCT ID format if provided."""
        if v and not re.match(r'^NCT\d{8}$', v):
            raise ValueError(f"NCT ID must be in format NCT######## (8 digits), got: {v}")
        return v


class TrialistHybridResponse(BaseModel):
    """Response from hybrid trialist parsing.

    Contains all 3 stage outputs and summary statistics.
    """
    extraction: Dict[str, Any] = Field(..., description="Stage 1: Extraction results")
    mappings: List[Dict[str, Any]] = Field(..., description="Stage 2: Mapping results")
    validations: List[Dict[str, Any]] = Field(..., description="Stage 3: Validation results")
    summary: Dict[str, Any] = Field(..., description="Pipeline summary statistics")
    workspace_path: Optional[str] = Field(default=None, description="Path where results were saved")


class TrialistHybridNctRequest(BaseModel):
    """Request to parse clinical trial criteria from NCT ID."""
    nct_id: str = Field(..., description="NCT ID to fetch from ClinicalTrials.gov", min_length=11, max_length=11)
    include_pmc: bool = Field(default=False, description="Whether to fetch PMC papers mentioning this NCT")
    max_pmc_results: int = Field(default=1, description="Max PMC papers to fetch (if include_pmc=True)", ge=1, le=20)

    @validator('nct_id')
    def validate_nct_id(cls, v):
        if not re.match(r'^NCT\d{8}$', v, re.IGNORECASE):
            raise ValueError(f"NCT ID must be in format NCT######## (8 digits), got: {v}")
        return v.upper()


class TrialistHybridNctResponse(BaseModel):
    """Response from NCT-based hybrid trialist parsing."""
    nct_id: str = Field(..., description="NCT ID that was fetched")
    eligibility_criteria: str = Field(..., description="Raw eligibility criteria text")
    extraction: Dict[str, Any] = Field(..., description="Stage 1: Extraction results")
    mappings: List[Dict[str, Any]] = Field(..., description="Stage 2: Mapping results")
    validations: List[Dict[str, Any]] = Field(..., description="Stage 3: Validation results")
    summary: Dict[str, Any] = Field(..., description="Pipeline summary statistics")
    workspace_path: Optional[str] = Field(default=None, description="Path where results were saved")
    corpus_path: Optional[str] = Field(default=None, description="Path to saved corpus.json")
    metadata_path: Optional[str] = Field(default=None, description="Path to saved metadata.json")
    pmc_papers: Optional[List[PMCPaperMetadata]] = Field(default=None, description="PMC papers if include_pmc was True")
    pmc_papers_found: Optional[int] = Field(default=None, description="Number of PMC papers found")


# ============================================================================
# PMC Paper Fetcher Schemas
# ============================================================================

class PMCPaperMetadata(BaseModel):
    """Metadata for a single PMC paper."""
    pmid: Optional[str] = Field(None, description="PubMed ID")
    pmc_id: Optional[str] = Field(None, description="PMC ID (e.g., PMC1234567)")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(default="", description="Paper abstract")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    journal: str = Field(default="", description="Journal name")
    pub_date: str = Field(default="", description="Publication date (YYYY-MM-DD)")
    url: str = Field(..., description="PubMed URL")


class PMCSearchRequest(BaseModel):
    """Request to search PMC for papers mentioning an NCT ID."""
    nct_id: str = Field(..., description="NCT ID to search for (e.g., NCT03389555)")
    max_results: int = Field(default=1, description="Maximum papers to return (default: 1)", ge=1, le=20)
    sort_by: str = Field(default="pub_date", description="Sort order: 'pub_date' or 'relevance'")

    @validator('nct_id')
    def validate_nct_id(cls, v):
        if not re.match(r'^NCT\d{8}$', v, re.IGNORECASE):
            raise ValueError(f"NCT ID must be in format NCT######## (8 digits), got: {v}")
        return v.upper()

    @validator('sort_by')
    def validate_sort_by(cls, v):
        if v not in ["pub_date", "relevance"]:
            raise ValueError(f"sort_by must be 'pub_date' or 'relevance', got: {v}")
        return v


class PMCSearchResponse(BaseModel):
    """Response from PMC paper search."""
    nct_id: str = Field(..., description="NCT ID that was searched")
    papers_found: int = Field(..., description="Number of papers found")
    papers: List[PMCPaperMetadata] = Field(..., description="List of paper metadata")
    corpus_path: Optional[str] = Field(None, description="Path to corpus.json if saved")
