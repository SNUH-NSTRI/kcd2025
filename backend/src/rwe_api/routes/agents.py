"""Multi-Agent System API endpoints.

This module provides REST API endpoints for executing and monitoring
intelligent agents in the RWE Clinical Trial Emulation platform.

Available Agents:
- StatisticianAgent: PSM + Survival Analysis with LLM interpretation

Endpoints:
- POST /api/agents/{agent_name}/run - Submit agent execution request
- GET /api/agents/jobs/{job_id}/status - Check job status
- GET /api/agents - List available agents
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from rwe_api.config import settings  # Centralized config
from rwe_api.schemas.agents import (
    AgentRunRequest,
    AgentRunResponse,
    JobStatusResponse,
    AgentListResponse,
    AgentMetadata,
    AgentStatus,
    TrialistHybridRequest,
    TrialistHybridResponse,
    TrialistHybridNctRequest,
    TrialistHybridNctResponse,
    PMCSearchRequest,
    PMCSearchResponse,
    PMCPaperMetadata,
)

# Import agent system
try:
    from agents import get_agent, list_agents
    from agents.base import AgentResult
    AGENTS_AVAILABLE = True
except ImportError as e:
    AGENTS_AVAILABLE = False
    AGENT_IMPORT_ERROR = str(e)

router = APIRouter()

_job_store: Dict[str, Dict[str, Any]] = {}

# Use centralized config (ALWAYS loads .env)
WORKSPACE_ROOT = settings.WORKSPACE_ROOT


@router.get("/", response_model=AgentListResponse)
async def list_available_agents():
    """List all available agents.

    Returns:
        AgentListResponse with agent metadata
    """
    if not AGENTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail=f"Agent system not available: {AGENT_IMPORT_ERROR}"
        )

    agents_list = list_agents()
    agents_metadata = [
        AgentMetadata(
            name=agent["name"],
            description=agent["description"],
            version=agent["version"]
        )
        for agent in agents_list
    ]

    return AgentListResponse(
        agents=agents_metadata,
        total=len(agents_metadata)
    )


@router.post("/{agent_name}/run", response_model=AgentRunResponse)
async def run_agent(
    agent_name: str,
    request: AgentRunRequest,
    background_tasks: BackgroundTasks
):
    """Execute an agent with given parameters.

    This endpoint submits an agent execution request and returns immediately
    with a job ID. The actual execution happens in the background.

    Args:
        agent_name: Name of the agent to run (e.g., "statistician")
        request: Agent execution parameters (NCT ID, medication, etc.)
        background_tasks: FastAPI background tasks manager

    Returns:
        AgentRunResponse with job_id for status polling

    Raises:
        HTTPException 404: If agent not found
        HTTPException 400: If input validation fails
        HTTPException 503: If agent system unavailable
    """
    if not AGENTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail=f"Agent system not available: {AGENT_IMPORT_ERROR}"
        )

    # Validate agent name matches request
    if agent_name != request.agent_name:
        raise HTTPException(
            status_code=400,
            detail=f"Agent name mismatch: URL has '{agent_name}' but request has '{request.agent_name}'"
        )

    # Get agent instance
    agent = get_agent(agent_name)
    if agent is None:
        available = [a["name"] for a in list_agents()]
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available agents: {', '.join(available)}"
        )

    # Validate inputs
    is_valid, error_msg = await agent.validate_inputs(
        nct_id=request.nct_id,
        medication=request.medication,
        workspace_root=WORKSPACE_ROOT
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {error_msg}"
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Initialize job in store
    _job_store[job_id] = {
        "job_id": job_id,
        "agent_name": agent_name,
        "status": AgentStatus.PENDING,
        "progress": None,
        "result": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "request": request.dict()
    }

    # Submit background task
    background_tasks.add_task(
        execute_agent_task,
        job_id=job_id,
        agent_name=agent_name,
        nct_id=request.nct_id,
        medication=request.medication,
        config_overrides=request.config_overrides
    )

    return AgentRunResponse(
        job_id=job_id,
        agent_name=agent_name,
        status=AgentStatus.PENDING,
        message=f"Agent '{agent_name}' execution submitted successfully"
    )


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the current status of an agent execution job.

    Args:
        job_id: Unique job identifier from run_agent response

    Returns:
        JobStatusResponse with current status and results (if completed)

    Raises:
        HTTPException 404: If job not found
    """
    if job_id not in _job_store:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found"
        )

    job_data = _job_store[job_id]

    return JobStatusResponse(
        job_id=job_data["job_id"],
        agent_name=job_data["agent_name"],
        status=job_data["status"],
        progress=job_data.get("progress"),
        result=job_data.get("result"),
        error=job_data.get("error"),
        created_at=job_data.get("created_at"),
        updated_at=job_data.get("updated_at")
    )


async def execute_agent_task(
    job_id: str,
    agent_name: str,
    nct_id: str,
    medication: str,
    config_overrides: Dict[str, Any] = None
):
    """Background task to execute an agent.

    This function runs in a FastAPI background task and updates
    the job status in the job store.

    Args:
        job_id: Job identifier for tracking
        agent_name: Name of the agent to execute
        nct_id: NCT trial identifier
        medication: Medication name
        config_overrides: Optional configuration overrides
    """
    # Define progress callback
    def update_progress(message: str):
        """Update job progress in store."""
        _job_store[job_id]["progress"] = message
        _job_store[job_id]["updated_at"] = datetime.utcnow().isoformat()

    try:
        # Update status to processing
        _job_store[job_id]["status"] = AgentStatus.PROCESSING
        update_progress("Starting agent...")

        # Get agent
        agent = get_agent(agent_name)
        if agent is None:
            raise ValueError(f"Agent '{agent_name}' not found")

        # Execute agent with progress callback
        result: AgentResult = await agent.run(
            nct_id=nct_id,
            medication=medication,
            workspace_root=WORKSPACE_ROOT,
            config_overrides=config_overrides,
            progress_callback=update_progress
        )

        # Update job with results
        _job_store[job_id]["status"] = result.status
        _job_store[job_id]["result"] = {
            "output_dir": result.output_dir,
            "result_data": result.result_data,
            "metadata": result.metadata,
            # Add 'output' alias for frontend compatibility
            "output": result.result_data
        }
        
        # NEW: Add multi-method matching results to job store
        if result.result_data:
            _job_store[job_id]["method_comparisons"] = result.result_data.get("method_comparisons")
            _job_store[job_id]["selected_method"] = result.result_data.get("selected_method")
            _job_store[job_id]["method_reasoning"] = result.result_data.get("method_reasoning")
        
        _job_store[job_id]["progress"] = "Completed"
        _job_store[job_id]["updated_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        # Update job with error
        _job_store[job_id]["status"] = AgentStatus.FAILED
        _job_store[job_id]["error"] = str(e)
        _job_store[job_id]["progress"] = "Failed"
        _job_store[job_id]["updated_at"] = datetime.utcnow().isoformat()

        # Log error (in production, use proper logging)
        print(f"❌ Agent execution failed for job {job_id}: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# Hybrid Trialist Endpoint (Synchronous - for frontend testing)
# ============================================================================

@router.post("/trialist/parse-hybrid", response_model=TrialistHybridResponse)
async def parse_hybrid_trialist(request: TrialistHybridRequest):
    """
    Parse clinical trial criteria using Hybrid Trialist pipeline.
    
    This endpoint executes all 3 stages synchronously:
    1. Stage 1: Extraction (LLM with Function Calling)
    2. Stage 2: Mapping to MIMIC-IV (LLM with schema validation)
    3. Stage 3: Validation & SQL Generation (Deterministic)
    
    Returns complete results including extraction, mappings, validations, and summary.
    
    Example request:
    ```json
    {
        "raw_criteria": "Inclusion: Age >= 18 years. Lactate > 2 mmol/L.",
        "nct_id": "NCT03389555"
    }
    ```
    """
    import os
    import json
    from pathlib import Path
    
    # Import pipeline
    try:
        from agents.trialist_hybrid.pipeline import TrialistHybridPipeline
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Trialist Hybrid pipeline not available. Check backend installation."
        )
    
    # Get API key and schema path
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENROUTER_API_KEY not configured"
        )
    
    schema_path = Path(__file__).parent.parent.parent / "agents" / "trialist_hybrid" / "prompts" / "mimic_schema.json"
    if not schema_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"MIMIC schema not found at {schema_path}"
        )
    
    try:
        # Initialize pipeline
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=str(schema_path)
        )
        
        # Execute pipeline
        result = pipeline.run(request.raw_criteria)
        
        # Save results to workspace if NCT ID provided
        workspace_path = None
        if request.nct_id:
            nct_dir = WORKSPACE_ROOT / request.nct_id / "trialist_hybrid"
            nct_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = nct_dir / "pipeline_output.json"
            with open(output_file, "w") as f:
                json.dump(result.model_dump(), f, indent=2)
            
            workspace_path = str(output_file)
        
        # Convert to response format
        return TrialistHybridResponse(
            extraction=result.extraction.model_dump(),
            mappings=[m.model_dump() for m in result.mappings],
            validations=[v.model_dump() for v in result.validations],
            summary=result.summary.model_dump(),
            workspace_path=workspace_path
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@router.post("/trialist/parse-from-nct", response_model=TrialistHybridNctResponse)
async def parse_hybrid_trialist_from_nct(request: TrialistHybridNctRequest):
    """
    Fetch NCT data from ClinicalTrials.gov and parse using Hybrid Trialist pipeline.
    
    This endpoint:
    1. Fetches study data from ClinicalTrials.gov API
    2. Extracts eligibility criteria (Inclusion/Exclusion)
    3. Saves corpus.json and metadata.json to project/{NCT}/
    4. Executes 3-stage Trialist Hybrid pipeline
    5. Returns complete results with workspace paths
    
    Example request:
    ```json
    {
        "nct_id": "NCT03389555"
    }
    ```
    
    Returns:
    - nct_id: NCT ID that was fetched
    - eligibility_criteria: Raw eligibility text
    - extraction: Stage 1 results
    - mappings: Stage 2 results  
    - validations: Stage 3 results (SQL queries)
    - summary: Pipeline statistics
    - workspace_path: Path to pipeline_output.json
    - corpus_path: Path to corpus.json
    - metadata_path: Path to metadata.json
    """
    import os
    import json
    from pathlib import Path
    
    # Import required modules
    try:
        from agents.trialist_hybrid.pipeline import TrialistHybridPipeline
        from agents.trialist_hybrid.nct_fetcher import NCTFetcher
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Trialist Hybrid modules not available: {str(e)}"
        )
    
    # Get API key and schema path
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENROUTER_API_KEY not configured"
        )
    
    schema_path = Path(__file__).parent.parent.parent / "agents" / "trialist_hybrid" / "prompts" / "mimic_schema.json"
    if not schema_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"MIMIC schema not found at {schema_path}"
        )
    
    try:
        # Step 1: Fetch NCT data from ClinicalTrials.gov
        fetcher = NCTFetcher(workspace_root=WORKSPACE_ROOT)
        nct_data = fetcher.fetch_and_save(request.nct_id)

        eligibility_criteria = nct_data["eligibility_criteria"]
        if not eligibility_criteria:
            raise HTTPException(
                status_code=404,
                detail=f"No eligibility criteria found for {request.nct_id}"
            )

        # Step 2: Initialize Trialist Hybrid pipeline
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=str(schema_path)
        )

        # Step 3: Execute pipeline on eligibility criteria
        result = pipeline.run(eligibility_criteria)

        # Step 4: Save pipeline output to workspace
        nct_dir = WORKSPACE_ROOT / request.nct_id / "trialist_hybrid"
        nct_dir.mkdir(parents=True, exist_ok=True)

        output_file = nct_dir / "pipeline_output.json"
        with open(output_file, "w") as f:
            json.dump(result.model_dump(), f, indent=2)

        workspace_path = str(output_file)

        # Step 5: Optionally fetch PMC papers
        pmc_papers = None
        pmc_papers_found = None

        if request.include_pmc:
            try:
                from agents.trialist_hybrid.pmc_fetcher import PMCFetcher

                pmc_fetcher = PMCFetcher(workspace_root=WORKSPACE_ROOT)
                pmc_result = pmc_fetcher.fetch_and_save(
                    nct_id=request.nct_id,
                    max_results=request.max_pmc_results,
                    sort_by="pub_date",
                    append=True
                )

                pmc_papers_found = pmc_result["papers_found"]
                pmc_papers = [
                    PMCPaperMetadata(
                        pmid=paper.get("pmid"),
                        pmc_id=paper.get("pmc_id"),
                        doi=paper.get("doi"),
                        title=paper.get("title", ""),
                        abstract=paper.get("abstract", ""),
                        authors=paper.get("authors", []),
                        journal=paper.get("journal", ""),
                        pub_date=paper.get("pub_date", ""),
                        url=paper.get("url", ""),
                    )
                    for paper in pmc_result["papers"]
                ]
            except Exception as e:
                # Log error but don't fail the entire request
                import traceback
                traceback.print_exc()
                print(f"⚠️  PMC fetch failed (non-blocking): {e}")

        # Convert to response format
        return TrialistHybridNctResponse(
            nct_id=request.nct_id,
            eligibility_criteria=eligibility_criteria,
            extraction=result.extraction.model_dump(),
            mappings=[m.model_dump() for m in result.mappings],
            validations=[v.model_dump() for v in result.validations],
            summary=result.summary.model_dump(),
            workspace_path=workspace_path,
            corpus_path=nct_data["corpus_path"],
            metadata_path=nct_data["metadata_path"],
            pmc_papers=pmc_papers,
            pmc_papers_found=pmc_papers_found,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"NCT fetch and parse failed: {str(e)}"
        )


@router.get("/trialist/test-nct-fetch")
async def test_nct_fetch():
    """Test NCT fetcher import."""
    try:
        from agents.trialist_hybrid.nct_fetcher import NCTFetcher
        return {"status": "success", "message": "NCTFetcher imported successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e), "type": type(e).__name__}


# ============================================================================
# PMC Paper Search Endpoint
# ============================================================================

@router.post("/trialist/pmc-search", response_model=PMCSearchResponse)
async def search_pmc_papers(request: PMCSearchRequest):
    """
    Search PubMed Central for papers mentioning the given NCT ID.

    This endpoint:
    1. Searches PubMed for papers referencing the NCT ID
    2. Fetches detailed metadata (title, abstract, authors, DOI, etc.)
    3. Saves papers to corpus.json in project/{NCT}/lit/
    4. Returns paper metadata

    By default, returns the most recent paper (max_results=1, sort_by='pub_date').

    Example request:
    ```json
    {
        "nct_id": "NCT03389555",
        "max_results": 1,
        "sort_by": "pub_date"
    }
    ```

    Returns:
    - nct_id: NCT ID that was searched
    - papers_found: Number of papers found
    - papers: List of paper metadata (title, authors, abstract, DOI, etc.)
    - corpus_path: Path to corpus.json if papers were saved
    """
    try:
        from agents.trialist_hybrid.pmc_fetcher import PMCFetcher
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"PMC fetcher module not available: {str(e)}"
        )

    try:
        # Initialize fetcher
        fetcher = PMCFetcher(workspace_root=WORKSPACE_ROOT)

        # Execute search and save
        result = fetcher.fetch_and_save(
            nct_id=request.nct_id,
            max_results=request.max_results,
            sort_by=request.sort_by,
            append=True  # Append to existing corpus
        )

        # Convert papers to Pydantic models
        papers = [
            PMCPaperMetadata(
                pmid=paper.get("pmid"),
                pmc_id=paper.get("pmc_id"),
                doi=paper.get("doi"),
                title=paper.get("title", ""),
                abstract=paper.get("abstract", ""),
                authors=paper.get("authors", []),
                journal=paper.get("journal", ""),
                pub_date=paper.get("pub_date", ""),
                url=paper.get("url", ""),
            )
            for paper in result["papers"]
        ]

        return PMCSearchResponse(
            nct_id=result["nct_id"],
            papers_found=result["papers_found"],
            papers=papers,
            corpus_path=result["corpus_path"],
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"PMC search failed: {str(e)}"
        )
