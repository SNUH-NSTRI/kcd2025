"""Pipeline execution endpoints."""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from rwe_api.config import settings  # Centralized config
from rwe_api.schemas.pipeline import (
    SearchLitRequest,
    ParseTrialsRequest,
    MapToEHRRequest,
    FilterCohortRequest,
    AnalyzeRequest,
    WriteReportRequest,
    RunAllRequest,
    StimulaRequest,
    PipelineResponse,
    SearchLitResponse,
    ParseTrialsResponse,
    MapToEHRResponse,
    FilterCohortResponse,
    AnalyzeResponse,
    WriteReportResponse,
    StimulaResponse,
    RunAllResponse,
    CTSearchRequest,
    CTSearchResponse,
    CTDetailResponse,
    TrialistRunRequest,
    TrialistRunResponse,
    RelatedPaper,
)
from rwe_api.schemas.models import (
    LiteratureCorpus,
    TrialSchema,
    FilterSpec,
    CohortResult,
    AnalysisMetrics,
    ReportBundle,
)
from rwe_api.services import PipelineService
from pipeline.clients.clinicaltrials_client import ClinicalTrialsClient

router = APIRouter()

# Use centralized config (ALWAYS loads .env)
pipeline_service = PipelineService(settings.WORKSPACE_ROOT)
ct_client = ClinicalTrialsClient()


@router.post("/search-lit", response_model=SearchLitResponse)
async def search_literature(request: SearchLitRequest):
    """Execute literature search stage.

    Fetches a single clinical trial from ClinicalTrials.gov by NCT ID.
    This endpoint is specifically designed to retrieve ONE trial's complete data.

    Args:
        request: Contains project_id and nct_id (e.g., NCT03389555)

    Returns:
        SearchLitResponse with the trial data

    Example:
        POST /api/pipeline/search-lit
        {
            "project_id": "my_project",
            "nct_id": "NCT03389555"
        }
    """
    try:
        corpus = await pipeline_service.search_literature(
            project_id=request.project_id,
            nct_id=request.nct_id,
        )
        # Convert dataclass to Pydantic model
        corpus_dict = asdict(corpus)
        corpus_pydantic = LiteratureCorpus(**corpus_dict)

        return SearchLitResponse(
            status="success",
            message=f"Literature search completed: {len(corpus.documents)} documents",
            corpus=corpus_pydantic,
            document_count=len(corpus.documents),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse-trials", response_model=ParseTrialsResponse)
async def parse_trials(request: ParseTrialsRequest):
    """Execute trial parsing stage."""
    try:
        schema = await pipeline_service.parse_trials(
            project_id=request.project_id,
            llm_provider=request.llm_provider,
            prompt_template=request.prompt_template,
            impl=request.impl,
        )
        # Convert dataclass to Pydantic model
        schema_dict = asdict(schema)
        schema_pydantic = TrialSchema(**schema_dict)
        
        return ParseTrialsResponse(
            status="success",
            message=f"Trial parsing completed: {len(schema.inclusion)} inclusion criteria",
            schema=schema_pydantic,
            inclusion_count=len(schema.inclusion),
            exclusion_count=len(schema.exclusion),
            feature_count=len(schema.features),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/map-to-ehr", response_model=MapToEHRResponse)
async def map_to_ehr(request: MapToEHRRequest):
    """Execute EHR mapping stage."""
    try:
        spec = await pipeline_service.map_to_ehr(
            project_id=request.project_id,
            ehr_source=request.ehr_source,
            dictionary=request.dictionary,
            output_format=request.output_format,
            impl=request.impl,
        )
        # Convert dataclass to Pydantic model
        spec_dict = asdict(spec)
        spec_pydantic = FilterSpec(**spec_dict)
        
        return MapToEHRResponse(
            status="success",
            message=f"EHR mapping completed: {len(spec.variable_map)} variables mapped",
            filter_spec=spec_pydantic,
            variable_map_count=len(spec.variable_map),
            inclusion_filters_count=len(spec.inclusion_filters),
            exclusion_filters_count=len(spec.exclusion_filters),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/filter-cohort", response_model=FilterCohortResponse)
async def filter_cohort(request: FilterCohortRequest):
    """Execute cohort filtering stage."""
    try:
        cohort = await pipeline_service.filter_cohort(
            project_id=request.project_id,
            input_uri=request.input_uri,
            sample_size=request.sample_size,
            dry_run=request.dry_run,
            impl=request.impl,
        )
        # Convert dataclass to Pydantic model
        cohort_dict = asdict(cohort)
        cohort_pydantic = CohortResult(**cohort_dict)
        
        total_subjects = cohort.summary.get("total_subjects", 0)
        return FilterCohortResponse(
            status="success",
            message=f"Cohort filtering completed: {total_subjects} subjects",
            cohort=cohort_pydantic,
            total_subjects=total_subjects,
            summary=cohort.summary,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_outcomes(request: AnalyzeRequest):
    """Execute outcome analysis stage."""
    try:
        analysis = await pipeline_service.analyze_outcomes(
            project_id=request.project_id,
            treatment_column=request.treatment_column,
            outcome_column=request.outcome_column,
            estimators=request.estimators,
            impl=request.impl,
        )
        # Convert dataclass to Pydantic model
        analysis_dict = asdict(analysis)
        analysis_pydantic = AnalysisMetrics(**analysis_dict)
        
        return AnalyzeResponse(
            status="success",
            message="Outcome analysis completed",
            analysis=analysis_pydantic,
            outcome_count=len(list(analysis.outcomes)),
            metrics_summary=analysis.metrics,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write-report", response_model=WriteReportResponse)
async def write_report(request: WriteReportRequest):
    """Execute report generation stage."""
    try:
        bundle = await pipeline_service.write_report(
            project_id=request.project_id,
            template=request.template,
            format=request.format,
            hil_review=request.hil_review,
            impl=request.impl,
        )
        # Convert dataclass to Pydantic model
        bundle_dict = asdict(bundle)
        bundle_pydantic = ReportBundle(**bundle_dict)
        
        return WriteReportResponse(
            status="success",
            message=f"Report generated: {len(bundle.figures)} figures",
            report=bundle_pydantic,
            report_path=str(bundle.document_path) if bundle.document_path else None,
            figure_count=len(bundle.figures),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stimula", response_model=StimulaResponse)
async def run_stimula(request: StimulaRequest):
    """Execute what-if simulation."""
    try:
        result = await pipeline_service.run_stimula(
            project_id=request.project_id,
            vary=request.vary,
            max_variations=request.max_variations,
            subject_id=request.subject_id,
        )
        return StimulaResponse(
            status="success",
            message=f"Stimula completed: {result['scenario_count']} scenarios",
            scenario_count=result["scenario_count"],
            baseline_subjects=result["baseline_subjects"],
            scenarios=result.get("scenarios", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-all", response_model=RunAllResponse)
async def run_all_pipeline(request: RunAllRequest, background_tasks: BackgroundTasks):
    """Execute full pipeline (all stages)."""
    try:
        result = await pipeline_service.run_all(
            project_id=request.project_id,
            disease_code=request.disease_code,
            keywords=request.keywords,
            sources=request.sources,
            estimators=request.estimators,
            template=request.template,
            max_records=request.max_records,
            require_full_text=request.require_full_text,
            llm_provider=request.llm_provider,
            prompt_template=request.prompt_template,
            ehr_source=request.ehr_source,
            dictionary=request.dictionary,
            filters_format=request.filters_format,
            input_uri=request.input_uri,
            sample_size=request.sample_size,
            treatment_column=request.treatment_column,
            outcome_column=request.outcome_column,
            report_format=request.report_format,
        )
        return RunAllResponse(
            status="success",
            message="Full pipeline completed successfully",
            stages=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse-trials-enhanced", response_model=ParseTrialsResponse)
async def parse_trials_enhanced(request: ParseTrialsRequest):
    """Execute enhanced trial parsing with Trialist Agent (force trialist implementation)."""
    try:
        schema = await pipeline_service.parse_trials(
            project_id=request.project_id,
            llm_provider=request.llm_provider or "gpt-4o-mini",
            prompt_template=request.prompt_template or "trialist-ner-prompt.txt",
            impl="trialist",  # Force trialist implementation
        )
        
        # Convert dataclass to Pydantic model
        schema_dict = asdict(schema)
        schema_pydantic = TrialSchema(**schema_dict)
        
        return ParseTrialsResponse(
            status="success",
            message=f"Enhanced Trialist parsing completed: {len(schema.inclusion)} inclusion criteria with domain classification",
            schema=schema_pydantic,
            inclusion_count=len(schema.inclusion),
            exclusion_count=len(schema.exclusion),
            feature_count=len(schema.features),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trialist/info")
async def get_trialist_info():
    """Get Trialist Agent configuration and capabilities."""
    return {
        "status": "available",
        "version": "1.0.0",
        "capabilities": {
            "enhanced_ner": True,
            "domain_classification": True,
            "standardization": "placeholder",
            "cdm_mapping": "placeholder"
        },
        "domains": [
            "Demographic", "Condition", "Device", "Procedure",
            "Drug", "Measurement", "Observation", "Visit",
            "Negation_cue", "Temporal", "Quantity", "Value"
        ],
        "vocabularies": {
            "Condition": "ICD-10-CM",
            "Drug": "RxNorm",
            "Measurement": "LOINC",
            "Procedure": "CPT4",
            "Device": "SNOMED CT",
            "Observation": "SNOMED CT",
            "Visit": "SNOMED CT"
        },
        "stages": [
            {
                "name": "Enhanced NER",
                "description": "12-domain entity classification with granularity and inference",
                "status": "implemented"
            },
            {
                "name": "Standardization",
                "description": "UMLS/OHDSI concept normalization",
                "status": "placeholder"
            },
            {
                "name": "CDM Mapping",
                "description": "OMOP vocabulary mapping",
                "status": "placeholder"
            }
        ]
    }


# ============================================================================
# DATATHON DEMO ENDPOINTS
# ============================================================================


class DemoRunRequest(BaseModel):
    """Request for demo pipeline execution (bypasses search-lit and trialist)."""
    project_id: str
    nct_id: str
    sample_size: int | None = None
    treatment_column: str = "on_arnI"
    outcome_column: str = "mortality_30d"
    estimators: list[str] = ["statistician"]


class DemoRunResponse(BaseModel):
    """Response from demo pipeline execution."""
    status: str
    message: str
    stages: dict
    execution_time_ms: float


@router.post("/demo/run-all", response_model=DemoRunResponse)
async def run_demo_pipeline(request: DemoRunRequest):
    """
    Execute complete pipeline in DEMO MODE (for datathon).

    This endpoint bypasses time-consuming stages:
    - ❌ Search-lit (uses pre-fetched corpus.json)
    - ❌ Trialist (uses pre-parsed schema.json)
    - ✅ Filter Cohort (executes pre-written SQL on MIMIC-IV)
    - ✅ Statistician (runs actual statistical analysis)

    Required fixtures in `fixtures/datathon/{NCT_ID}/`:
    - corpus.json (pre-fetched trial data)
    - schema.json (pre-parsed trial criteria)
    - cohort_query.sql (SQL for MIMIC-IV extraction)

    Example:
        POST /api/pipeline/demo/run-all
        {
            "project_id": "demo_001",
            "nct_id": "NCT03389555",
            "sample_size": 100,
            "treatment_column": "on_arnI",
            "outcome_column": "mortality_30d"
        }
    """
    import time
    start_time = time.time()

    try:
        stages = {}

        # Stage 1: Load pre-built corpus (bypasses search-lit)
        try:
            corpus = await pipeline_service.demo_loader.load_prebuilt_corpus(
                request.nct_id
            )
            stages["search_lit"] = {
                "status": "bypassed",
                "source": "pre-built fixtures",
                "document_count": len(corpus.documents)
            }
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to load demo corpus: {str(e)}"
            )

        # Stage 2: Load pre-built schema (bypasses trialist)
        try:
            ctx = pipeline_service._create_context(request.project_id)
            schema = await pipeline_service.demo_loader.load_prebuilt_schema(
                request.nct_id,
                ctx
            )
            stages["parse_trials"] = {
                "status": "bypassed",
                "source": "pre-built fixtures",
                "inclusion_count": len(schema.inclusion),
                "exclusion_count": len(schema.exclusion),
                "feature_count": len(schema.features)
            }
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to load demo schema: {str(e)}"
            )

        # Stage 3: Execute SQL on MIMIC-IV (ACTUAL EXECUTION)
        try:
            cohort = await pipeline_service.filter_cohort_demo(
                project_id=request.project_id,
                nct_id=request.nct_id,
                sample_size=request.sample_size,
                dry_run=False
            )
            stages["filter_cohort"] = {
                "status": "executed",
                "source": "mimic-iv (SQL)",
                "total_subjects": cohort.summary.get("total_subjects", 0),
                "summary": cohort.summary
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract cohort: {str(e)}"
            )

        # Stage 4: Run Statistician (ACTUAL EXECUTION)
        try:
            analysis = await pipeline_service.analyze_outcomes(
                project_id=request.project_id,
                treatment_column=request.treatment_column,
                outcome_column=request.outcome_column,
                estimators=request.estimators,
                impl="statistician"  # Force statistician implementation
            )
            stages["analyze"] = {
                "status": "executed",
                "source": "statistician plugin",
                "outcome_count": len(list(analysis.outcomes)),
                "metrics_summary": analysis.metrics.get("summary", {})
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to analyze outcomes: {str(e)}"
            )

        execution_time_ms = (time.time() - start_time) * 1000

        return DemoRunResponse(
            status="success",
            message=f"Demo pipeline completed in {execution_time_ms:.0f}ms",
            stages=stages,
            execution_time_ms=execution_time_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CLINICALTRIALS.GOV SEARCH ENDPOINTS
# ============================================================================


class CTSearchRequest(BaseModel):
    """Request for ClinicalTrials.gov search."""
    query: str | None = None
    condition: str | None = None
    intervention: str | None = None
    sponsor: str | None = None
    status: list[str] | None = None
    phase: list[str] | None = None
    page_size: int = 20
    page_token: str | None = None


class CTSearchResponse(BaseModel):
    """Response from ClinicalTrials.gov search."""
    status: str
    message: str
    studies: list[dict]
    total_count: int
    next_page_token: str | None


class CTDetailResponse(BaseModel):
    """Response for single trial details."""
    status: str
    message: str
    study: dict


@router.post("/clinicaltrials/search", response_model=CTSearchResponse)
async def search_clinical_trials(request: CTSearchRequest):
    """
    Search ClinicalTrials.gov database with various filters.

    This endpoint provides direct access to ClinicalTrials.gov API v2
    for searching and discovering clinical trials.

    Args:
        request: Search parameters including query, filters, and pagination

    Returns:
        List of matching trials with summary information

    Example:
        POST /api/pipeline/clinicaltrials/search
        {
            "condition": "heart failure",
            "status": ["RECRUITING"],
            "phase": ["PHASE3"],
            "page_size": 20
        }
    """
    try:
        result = await ct_client.search_studies(
            query=request.query,
            condition=request.condition,
            intervention=request.intervention,
            sponsor=request.sponsor,
            status=request.status,
            phase=request.phase,
            page_size=request.page_size,
            page_token=request.page_token,
        )

        # Parse studies to simplified format
        studies = []
        for study_data in result.get("studies", []):
            try:
                parsed = ct_client.parse_study_summary(study_data)
                studies.append(parsed)
            except Exception as e:
                print(f"Warning: Failed to parse study {study_data.get('protocolSection', {}).get('identificationModule', {}).get('nctId')}: {e}")
                continue

        total_count = result.get("totalCount", len(studies))
        next_token = result.get("nextPageToken")

        return CTSearchResponse(
            status="success",
            message=f"Found {total_count} trials",
            studies=studies,
            total_count=total_count,
            next_page_token=next_token,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clinicaltrials/{nct_id}", response_model=CTDetailResponse)
async def get_trial_details(nct_id: str):
    """
    Get detailed information for a specific clinical trial by NCT ID.

    Args:
        nct_id: NCT identifier (e.g., NCT03389555)

    Returns:
        Complete trial details including eligibility, outcomes, and design

    Example:
        GET /api/pipeline/clinicaltrials/NCT03389555
    """
    try:
        result = await ct_client.get_study_details(nct_id)

        # API v2 returns study data directly (not wrapped in studies array)
        if not result or "protocolSection" not in result:
            raise HTTPException(status_code=404, detail=f"Trial {nct_id} not found")

        parsed = ct_client.parse_study_detail(result)

        return CTDetailResponse(
            status="success",
            message=f"Retrieved details for {nct_id}",
            study=parsed,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# TRIALIST AGENT ENDPOINT
# ============================================================================


@router.post("/trialist/run", response_model=TrialistRunResponse)
async def run_trialist_workflow(request: TrialistRunRequest):
    """
    Execute complete Trialist Agent workflow for a given NCT ID.

    This endpoint performs the following steps:
    1. **Literature Search** - Fetch NCT data from ClinicalTrials.gov + PMC papers
    2. **Trial Parsing** - Parse criteria using Trialist parser (3-stage NER/standardization/CDM)
    3. **EHR Mapping** - Generate MIMIC-IV SQL query from parsed criteria

    Args:
        request: TrialistRunRequest with NCT ID and options

    Returns:
        TrialistRunResponse with:
        - Trial data (ClinicalTrials.gov structured data)
        - Parsed schema (enhanced with OMOP concepts)
        - EHR mapping (MIMIC-IV SQL query)
        - Related papers (full-text markdown from PMC)

    Example:
        POST /api/pipeline/trialist/run
        {
            "project_id": "my_study",
            "nct_id": "NCT03389555",
            "fetch_papers": true,
            "generate_sql": true
        }
    """
    import time
    from rwe_api.schemas.pipeline import TrialistRunRequest, TrialistRunResponse, RelatedPaper

    start_time = time.time()
    stages_completed: list[str] = []

    try:
        # Stage 1: Literature Search (with paper fetching)
        try:
            corpus = await pipeline_service.search_literature(
                project_id=request.project_id,
                nct_id=request.nct_id,
            )
            stages_completed.append("search_lit")

            # Extract trial data
            if not corpus.documents:
                raise HTTPException(status_code=404, detail=f"No data found for {request.nct_id}")

            trial_doc = corpus.documents[0]
            trial_data = {
                "nct_id": trial_doc.identifier,
                "title": trial_doc.title,
                "url": trial_doc.url,
                "fetched_at": trial_doc.fetched_at.isoformat() if trial_doc.fetched_at else None,
            }

            # Extract related papers if requested
            related_papers: list[RelatedPaper] = []
            if request.fetch_papers and trial_doc.metadata:
                publication_ids = trial_doc.metadata.get("publication_ids", [])

                for id_type, id_value in publication_ids:
                    if id_type == "pmid":
                        # Check if paper was fetched (PMC markdown in full_text)
                        if trial_doc.full_text and f"PMID: {id_value}" in trial_doc.full_text:
                            # Extract PMCID from full_text
                            import re
                            pmcid_match = re.search(r'PMCID: (PMC\d+)', trial_doc.full_text)
                            pmcid = pmcid_match.group(1) if pmcid_match else None

                            # Get preview (first 500 chars after the paper header)
                            paper_start = trial_doc.full_text.find(f"# Paper (PMID: {id_value}")
                            if paper_start != -1:
                                preview_start = paper_start + 200  # Skip header
                                preview = trial_doc.full_text[preview_start:preview_start + 500]
                            else:
                                preview = None

                            related_papers.append(RelatedPaper(
                                pmid=id_value,
                                pmcid=pmcid,
                                status="full_text_retrieved",
                                full_text_preview=preview,
                                url=f"https://pubmed.ncbi.nlm.nih.gov/{id_value}/"
                            ))
                        else:
                            # Paper not available in PMC
                            related_papers.append(RelatedPaper(
                                pmid=id_value,
                                status="not_in_pmc",
                                url=f"https://pubmed.ncbi.nlm.nih.gov/{id_value}/"
                            ))

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Literature search failed: {str(e)}")

        # Stage 2: Trial Parsing (using Trialist parser)
        parsed_schema = None
        try:
            schema = await pipeline_service.parse_trials(
                project_id=request.project_id,
                impl="trialist"  # Force Trialist implementation
            )
            stages_completed.append("parse_trials")

            # Convert to dict for response
            from dataclasses import asdict
            parsed_schema = asdict(schema)

        except Exception as e:
            # Non-fatal: continue without parsed schema
            logger.warning(f"Trial parsing failed: {e}")

        # Stage 3: EHR Mapping (generate MIMIC SQL)
        ehr_mapping = None
        if request.generate_sql and parsed_schema:
            try:
                filter_spec = await pipeline_service.map_to_ehr(
                    project_id=request.project_id,
                    ehr_source="mimic-iv",
                    impl="trialist-mimic"  # Use Trialist MIMIC mapper
                )
                stages_completed.append("map_to_ehr")

                # Extract SQL from filter_spec
                from dataclasses import asdict
                filter_spec_dict = asdict(filter_spec)
                sql_query = filter_spec_dict.get("metadata", {}).get("sql_query", "")

                ehr_mapping = {
                    "ehr_source": "mimic-iv",
                    "generated_sql": sql_query,
                    "variable_map": filter_spec_dict.get("variable_map", {})
                }

            except Exception as e:
                # Non-fatal: continue without EHR mapping
                logger.warning(f"EHR mapping failed: {e}")

        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000

        # Build response
        return TrialistRunResponse(
            status="success" if len(stages_completed) == 3 else "partial",
            message=f"Trialist workflow completed: {len(stages_completed)}/3 stages successful",
            nct_id=request.nct_id,
            trial_data=trial_data,
            parsed_schema=parsed_schema,
            ehr_mapping=ehr_mapping,
            related_papers=related_papers,
            execution_time_ms=execution_time_ms,
            stages_completed=stages_completed
        )

    except HTTPException:
        raise
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        raise HTTPException(
            status_code=500,
            detail=f"Trialist workflow failed: {str(e)}"
        )
