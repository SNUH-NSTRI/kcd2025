"""Service for study management and background processing."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from rwe_api.schemas.studies import (
    CreateStudyRequest,
    StudyMetadata,
    StudyProgressStep,
    StudyStatus,
)
from rwe_api.services.pipeline_service import PipelineService


class StudyService:
    """Service for managing studies and their processing pipeline."""

    def __init__(self, workspace_root: Path, pipeline_service: PipelineService):
        """Initialize study service.

        Args:
            workspace_root: Root directory for workspace
            pipeline_service: Pipeline service for executing stages
        """
        self.workspace_root = workspace_root
        self.pipeline_service = pipeline_service
        self.logger = logging.getLogger("rwe_api.study_service")

    def _get_study_dir(self, study_id: str) -> Path:
        """Get study directory path."""
        return self.workspace_root / study_id

    def _get_metadata_path(self, study_id: str) -> Path:
        """Get study metadata file path."""
        return self._get_study_dir(study_id) / "metadata.json"

    def _get_status_path(self, study_id: str) -> Path:
        """Get study status file path."""
        return self._get_study_dir(study_id) / "status.json"

    async def create_study(self, request: CreateStudyRequest) -> str:
        """Create a new study and start background processing.

        Args:
            request: Study creation request

        Returns:
            Study ID (uses existing NCT directory if available)
        """
        # IMPORTANT: Use existing NCT directory if it exists, don't create new timestamped ones
        nct_dir = self.workspace_root / request.nct_id

        if nct_dir.exists():
            # Use existing NCT directory
            study_id = request.nct_id
            self.logger.info(f"Using existing NCT directory: {study_id}")
        else:
            # Only create if NCT directory doesn't exist (should be rare)
            study_id = request.nct_id
            nct_dir.mkdir(parents=True, exist_ok=True)
            (nct_dir / "lit").mkdir(exist_ok=True)
            (nct_dir / "schema").mkdir(exist_ok=True)
            self.logger.info(f"Created new NCT directory: {study_id}")

        # Save metadata
        metadata = StudyMetadata(
            study_id=study_id,
            name=request.name,
            nct_id=request.nct_id,
            research_question=request.research_question,
            medicine_family=request.medicine_family,
            medicine_generic=request.medicine_generic,
            medicine_brand=request.medicine_brand,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        with open(self._get_metadata_path(study_id), "w") as f:
            json.dump(metadata.model_dump(), f, indent=2)

        # Initialize status
        status = StudyStatus(
            study_id=study_id,
            overall_status="created",
            current_step=None,
            steps=[
                StudyProgressStep(
                    step="corpus",
                    label="Fetching trial from ClinicalTrials.gov",
                    status="pending",
                ),
                StudyProgressStep(
                    step="schema_parsing",
                    label="Analyzing eligibility criteria with LLM",
                    status="pending",
                ),
                StudyProgressStep(
                    step="schema_structure",
                    label="Structuring inclusion/exclusion rules",
                    status="pending",
                ),
                StudyProgressStep(
                    step="schema_mapping",
                    label="Mapping to MIMIC-IV features",
                    status="pending",
                ),
            ],
            created_at=metadata.created_at,
            updated_at=metadata.updated_at,
        )

        await self._save_status(study_id, status)

        # Start background processing (non-blocking)
        asyncio.create_task(self._process_study_pipeline(study_id, request.nct_id))

        return study_id

    async def _save_status(self, study_id: str, status: StudyStatus) -> None:
        """Save status to file."""
        status.updated_at = datetime.now().isoformat()
        with open(self._get_status_path(study_id), "w") as f:
            json.dump(status.model_dump(), f, indent=2)

    async def _update_step_status(
        self,
        study_id: str,
        step_name: str,
        new_status: str,
        error: str | None = None,
    ) -> None:
        """Update a specific step's status."""
        status = await self.get_study_status(study_id)

        for step in status.steps:
            if step.step == step_name:
                step.status = new_status
                if new_status == "in_progress":
                    step.started_at = datetime.now().isoformat()
                    status.current_step = step_name
                elif new_status in ("done", "failed"):
                    step.completed_at = datetime.now().isoformat()
                    if error:
                        step.error = error
                break

        # Update overall status
        if any(step.status == "failed" for step in status.steps):
            status.overall_status = "failed"
            status.error = f"Step {step_name} failed"
        elif all(step.status == "done" for step in status.steps):
            status.overall_status = "completed"
            status.current_step = None
        else:
            status.overall_status = "processing"

        await self._save_status(study_id, status)

    async def _process_study_pipeline(self, study_id: str, nct_id: str) -> None:
        """Process study pipeline - ONLY loads cached data, no LLM processing.

        Args:
            study_id: Study identifier
            nct_id: NCT ID to check for cached data
        """
        try:
            self.logger.info(f"Checking cached data for study {study_id}")

            # Check if schema.json exists (cached)
            schema_path = self._get_study_dir(study_id) / "schema" / "schema.json"
            corpus_path = self._get_study_dir(study_id) / "lit" / "corpus.json"

            # Step 1: Check corpus
            await self._update_step_status(study_id, "corpus", "in_progress")
            if corpus_path.exists():
                await self._update_step_status(study_id, "corpus", "done")
                self.logger.info(f"Found cached corpus for {study_id}")
            else:
                error_msg = f"No cached corpus found. Please prepare corpus.json manually."
                self.logger.error(error_msg)
                await self._update_step_status(study_id, "corpus", "failed", error_msg)
                return

            # Step 2-4: Check schema (NO LLM PROCESSING)
            await self._update_step_status(study_id, "schema_parsing", "in_progress")
            await self._update_step_status(study_id, "schema_structure", "in_progress")
            await self._update_step_status(study_id, "schema_mapping", "in_progress")

            if schema_path.exists():
                # Schema exists - mark all steps as done
                await self._update_step_status(study_id, "schema_parsing", "done")
                await self._update_step_status(study_id, "schema_structure", "done")
                await self._update_step_status(study_id, "schema_mapping", "done")
                self.logger.info(f"Found cached schema for {study_id}")
            else:
                # Schema doesn't exist - fail with helpful message
                error_msg = (
                    f"No cached schema found for {study_id}. "
                    f"Please create schema.json manually based on SQL/CSV files. "
                    f"See NCT03389555/schema/schema.json as example."
                )
                self.logger.error(error_msg)
                await self._update_step_status(study_id, "schema_parsing", "failed", error_msg)
                await self._update_step_status(study_id, "schema_structure", "failed", error_msg)
                await self._update_step_status(study_id, "schema_mapping", "failed", error_msg)
                return

            self.logger.info(f"All cached data loaded successfully for {study_id}")

        except Exception as e:
            self.logger.error(f"Unexpected error loading cached data for {study_id}: {e}")
            status = await self.get_study_status(study_id)
            status.overall_status = "failed"
            status.error = f"Unexpected error: {str(e)}"
            await self._save_status(study_id, status)

    async def get_study_status(self, study_id: str) -> StudyStatus:
        """Get current study status.

        Args:
            study_id: Study identifier

        Returns:
            Current study status

        Raises:
            FileNotFoundError: If study doesn't exist
        """
        status_path = self._get_status_path(study_id)
        if not status_path.exists():
            raise FileNotFoundError(f"Study {study_id} not found")

        with open(status_path) as f:
            data = json.load(f)
            return StudyStatus(**data)

    async def get_corpus(self, study_id: str) -> dict[str, Any]:
        """Get study corpus data.

        Args:
            study_id: Study identifier

        Returns:
            Corpus data

        Raises:
            FileNotFoundError: If corpus doesn't exist
        """
        corpus_path = self._get_study_dir(study_id) / "lit" / "corpus.json"
        if not corpus_path.exists():
            raise FileNotFoundError(f"Corpus not found for study {study_id}")

        with open(corpus_path) as f:
            return json.load(f)

    async def get_schema(self, study_id: str) -> dict[str, Any]:
        """Get study schema data and transform to frontend format.

        Args:
            study_id: Study identifier

        Returns:
            Schema data in frontend-compatible format

        Raises:
            FileNotFoundError: If schema doesn't exist
        """
        schema_path = self._get_study_dir(study_id) / "schema" / "schema.json"
        trial_schema_path = self._get_study_dir(study_id) / "schema" / "trial_schema.json"

        # 1. Check if transformed schema.json already exists (cached)
        if schema_path.exists():
            self.logger.info(f"Loading cached schema for {study_id}")
            with open(schema_path) as f:
                return json.load(f)

        # 2. If not cached, transform trial_schema.json and save it
        if trial_schema_path.exists():
            self.logger.info(f"Transforming trial_schema.json for {study_id}")
            with open(trial_schema_path) as f:
                trialist_schema = json.load(f)

            # Transform to frontend format
            transformed_schema = self._transform_trialist_to_frontend(trialist_schema)

            # Cache the transformed result
            with open(schema_path, "w") as f:
                json.dump(transformed_schema, f, indent=2)
            self.logger.info(f"Cached transformed schema to {schema_path}")

            return transformed_schema

        # 3. No schema found
        raise FileNotFoundError(f"Schema not found for study {study_id}")

    def _transform_trialist_to_frontend(self, trialist_schema: dict[str, Any]) -> dict[str, Any]:
        """Transform Trialist v1 schema to frontend format.

        Args:
            trialist_schema: Schema in Trialist v1 format

        Returns:
            Schema in frontend format
        """
        def extract_entities_summary(criterion: dict) -> str:
            """Extract a human-readable summary from entities."""
            entities = criterion.get("entities", [])
            if not entities:
                return ""

            # Group entities by domain
            concepts = [e["text"] for e in entities if e.get("type") == "concept"]
            values = [e["text"] for e in entities if e.get("type") == "value"]
            temporals = [e["text"] for e in entities if e.get("type") == "temporal"]

            summary_parts = []
            if concepts:
                summary_parts.append(", ".join(concepts[:3]))  # First 3 concepts
            if values:
                summary_parts.append(f"({', '.join(values[:2])})")
            if temporals:
                summary_parts.append(f"[{', '.join(temporals[:2])}]")

            return " ".join(summary_parts) if summary_parts else "See entities for details"

        # Transform inclusion criteria
        inclusion = []
        for criterion in trialist_schema.get("inclusion", []):
            entities = criterion.get("entities", [])

            # Try to extract structured value from entities
            value_entity = next((e for e in entities if e.get("type") == "value"), None)

            inclusion.append({
                "id": criterion["id"],
                "description": criterion["description"],
                "category": criterion.get("category", "clinical"),
                "kind": criterion.get("kind", "threshold"),
                "value": {
                    "field": extract_entities_summary(criterion),
                    "op": value_entity.get("operator", "contains") if value_entity else "contains",
                    "value": value_entity.get("numeric_value", criterion["description"]) if value_entity else criterion["description"]
                },
                "entities": entities  # Include raw entities for detailed view
            })

        # Transform exclusion criteria
        exclusion = []
        for criterion in trialist_schema.get("exclusion", []):
            entities = criterion.get("entities", [])
            value_entity = next((e for e in entities if e.get("type") == "value"), None)

            exclusion.append({
                "id": criterion["id"],
                "description": criterion["description"],
                "category": criterion.get("category", "clinical"),
                "kind": criterion.get("kind", "threshold"),
                "value": {
                    "field": extract_entities_summary(criterion),
                    "op": value_entity.get("operator", "contains") if value_entity else "contains",
                    "value": value_entity.get("numeric_value", criterion["description"]) if value_entity else criterion["description"]
                },
                "entities": entities
            })

        # Transform features (if available, otherwise empty)
        features = []
        if trialist_schema.get("features"):
            for feature in trialist_schema["features"]:
                features.append({
                    "name": feature.get("name", "unknown"),
                    "source": feature.get("source", "derived"),
                    "unit": feature.get("unit"),
                    "timeWindow": feature.get("timeWindow"),
                    "metadata": feature.get("metadata", {})
                })

        return {
            "schemaVersion": trialist_schema.get("schema_version", "trialist.v1"),
            "diseaseCode": trialist_schema.get("disease_code"),
            "inclusion": inclusion,
            "exclusion": exclusion,
            "features": features,
            "provenance": {
                "source": "trialist-ner",
                "nctId": trialist_schema.get("nct_id", "unknown"),
                "generatedAt": datetime.now().isoformat(),
                "version": "1.0",
                "method": "LLM-based NER with entity extraction",
                "notes": "Transformed from Trialist v1 format"
            }
        }

    async def retry_parsing(self, study_id: str) -> None:
        """Retry schema parsing for a failed study.

        Args:
            study_id: Study identifier
        """
        status = await self.get_study_status(study_id)
        metadata_path = self._get_metadata_path(study_id)

        if not metadata_path.exists():
            raise FileNotFoundError(f"Study {study_id} not found")

        with open(metadata_path) as f:
            metadata = StudyMetadata(**json.load(f))

        # Reset parsing steps
        for step in status.steps:
            if step.step in ("schema_parsing", "schema_structure", "schema_mapping"):
                step.status = "pending"
                step.started_at = None
                step.completed_at = None
                step.error = None

        status.overall_status = "processing"
        status.error = None
        await self._save_status(study_id, status)

        # Restart parsing pipeline
        asyncio.create_task(self._process_study_pipeline(study_id, metadata.nct_id))
