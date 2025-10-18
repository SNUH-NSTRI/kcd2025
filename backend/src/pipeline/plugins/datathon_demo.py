"""
Datathon Demo Plugin: Bypass Search-lit and Trialist for Fast Demos

This plugin loads pre-prepared data for datathon demonstrations:
- Pre-fetched ClinicalTrials.gov data (bypasses search-lit)
- Pre-parsed trial schema (bypasses trialist)
- Pre-written SQL queries for MIMIC-IV extraction

Usage:
    - Set DEMO_MODE=true in .env
    - Provide NCT ID and fixtures in fixtures/datathon/{NCT_ID}/
    - Execute demo pipeline via /api/pipeline/demo/run-all
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping, Sequence

from .. import models
from ..context import PipelineContext

logger = logging.getLogger(__name__)


class DatathonDemoLoader:
    """
    Loads pre-prepared data for datathon demonstrations.

    This class bypasses time-consuming steps (search-lit, trialist) by loading
    pre-saved results from fixtures directory.
    """

    def __init__(self, fixtures_root: Path | str = "data/fixtures/datathon"):
        """
        Initialize demo loader.

        Args:
            fixtures_root: Root directory containing demo fixtures
        """
        self.fixtures_root = Path(fixtures_root)
        logger.info(f"DatathonDemoLoader initialized with root: {self.fixtures_root}")

    def is_demo_available(self, nct_id: str) -> bool:
        """
        Check if demo fixtures are available for given NCT ID.

        Args:
            nct_id: NCT ID (e.g., NCT03389555)

        Returns:
            True if fixtures exist, False otherwise
        """
        nct_dir = self.fixtures_root / nct_id
        required_files = ["corpus.json", "schema.json", "cohort_query.sql"]

        if not nct_dir.exists():
            return False

        for filename in required_files:
            if not (nct_dir / filename).exists():
                logger.warning(f"Missing fixture: {nct_dir / filename}")
                return False

        return True

    def load_prebuilt_corpus(
        self, nct_id: str, ctx: PipelineContext | None = None
    ) -> models.LiteratureCorpus:
        """
        Load pre-fetched literature corpus from fixtures.

        This bypasses the search-lit stage by loading saved ClinicalTrials.gov data.

        Args:
            nct_id: NCT ID (e.g., NCT03389555)
            ctx: Optional pipeline context (for logging)

        Returns:
            LiteratureCorpus with pre-fetched documents

        Raises:
            FileNotFoundError: If corpus.json not found
        """
        corpus_file = self.fixtures_root / nct_id / "corpus.json"

        if not corpus_file.exists():
            raise FileNotFoundError(
                f"Demo corpus not found: {corpus_file}. "
                f"Please create fixtures for {nct_id}."
            )

        logger.info(f"📂 Loading pre-built corpus from: {corpus_file}")

        with corpus_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Convert JSON to LiteratureCorpus
        documents = []
        for doc_data in data.get("documents", []):
            doc = models.LiteratureDocument(
                source=doc_data["source"],
                identifier=doc_data["identifier"],
                title=doc_data["title"],
                abstract=doc_data.get("abstract"),
                full_text=doc_data.get("full_text"),
                fetched_at=doc_data["fetched_at"],  # Keep as string for now
                url=doc_data.get("url"),
                metadata=doc_data.get("metadata", {})
            )
            documents.append(doc)

        corpus = models.LiteratureCorpus(
            schema_version=data.get("schema_version", "lit.v1"),
            documents=documents
        )

        logger.info(f"✅ Loaded {len(documents)} documents from demo corpus")
        return corpus

    def load_prebuilt_schema(
        self, nct_id: str, ctx: PipelineContext | None = None
    ) -> models.TrialSchema:
        """
        Load pre-parsed trial schema from fixtures.

        This bypasses the trialist stage by loading saved parsing results.

        Args:
            nct_id: NCT ID (e.g., NCT03389555)
            ctx: Optional pipeline context (for logging)

        Returns:
            TrialSchema with pre-parsed criteria and features

        Raises:
            FileNotFoundError: If schema.json not found
        """
        schema_file = self.fixtures_root / nct_id / "schema.json"

        if not schema_file.exists():
            raise FileNotFoundError(
                f"Demo schema not found: {schema_file}. "
                f"Please create fixtures for {nct_id}."
            )

        logger.info(f"📂 Loading pre-built schema from: {schema_file}")

        with schema_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Convert JSON to TrialSchema
        inclusion = []
        for crit_data in data.get("inclusion", []):
            criterion = models.TrialCriterion(
                id=crit_data["id"],
                description=crit_data["description"],
                category=crit_data["category"],
                kind=crit_data["kind"],
                value=crit_data["value"],
                entities=None  # Simplified for demo
            )
            inclusion.append(criterion)

        exclusion = []
        for crit_data in data.get("exclusion", []):
            criterion = models.TrialCriterion(
                id=crit_data["id"],
                description=crit_data["description"],
                category=crit_data["category"],
                kind=crit_data["kind"],
                value=crit_data["value"],
                entities=None
            )
            exclusion.append(criterion)

        features = []
        for feat_data in data.get("features", []):
            feature = models.TrialFeature(
                name=feat_data["name"],
                source=feat_data["source"],
                unit=feat_data.get("unit"),
                time_window=tuple(feat_data["time_window"]) if feat_data.get("time_window") else None,
                metadata=feat_data.get("metadata"),
                entities=None
            )
            features.append(feature)

        schema = models.TrialSchema(
            schema_version=data.get("schema_version", "trial.v1"),
            disease_code=data.get("disease_code", ""),
            inclusion=inclusion,
            exclusion=exclusion,
            features=features,
            provenance=data.get("provenance", {"source": "demo_fixtures"})
        )

        logger.info(
            f"✅ Loaded schema: {len(inclusion)} inclusion, "
            f"{len(exclusion)} exclusion, {len(features)} features"
        )
        return schema

    def load_prebuilt_sql(self, nct_id: str) -> str:
        """
        Load pre-written SQL query for MIMIC-IV cohort extraction.

        Args:
            nct_id: NCT ID (e.g., NCT03389555)

        Returns:
            SQL query string for MIMIC-IV

        Raises:
            FileNotFoundError: If cohort_query.sql not found
        """
        sql_file = self.fixtures_root / nct_id / "cohort_query.sql"

        if not sql_file.exists():
            raise FileNotFoundError(
                f"Demo SQL not found: {sql_file}. "
                f"Please create SQL query for {nct_id}."
            )

        logger.info(f"📂 Loading pre-built SQL from: {sql_file}")

        with sql_file.open("r", encoding="utf-8") as f:
            sql = f.read()

        logger.info(f"✅ Loaded SQL query ({len(sql)} characters)")
        return sql

    def sql_to_filter_spec(
        self, sql: str, nct_id: str, schema: models.TrialSchema
    ) -> models.FilterSpec:
        """
        Convert SQL query to FilterSpec format.

        This is a simplified conversion for demo purposes.
        The actual filtering will be done by executing the SQL.

        Args:
            sql: SQL query string
            nct_id: NCT ID for lineage tracking
            schema: Trial schema (for reference)

        Returns:
            FilterSpec with SQL embedded in metadata
        """
        # Create minimal FilterSpec that carries the SQL
        filter_spec = models.FilterSpec(
            schema_version="filter.v1",
            ehr_source="mimic-iv",
            variable_map=[],  # Not needed for SQL mode
            inclusion_filters=[],  # SQL handles this
            exclusion_filters=[],  # SQL handles this
            lineage={
                "source": "demo_fixtures",
                "nct_id": nct_id,
                "sql_query": sql,
                "mode": "sql_direct"
            }
        )

        logger.info("✅ Created FilterSpec with embedded SQL")
        return filter_spec


__all__ = ["DatathonDemoLoader"]
