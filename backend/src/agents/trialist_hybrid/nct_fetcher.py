"""
NCT Data Fetcher for Trialist Hybrid Pipeline.

Fetches clinical trial data from ClinicalTrials.gov and extracts eligibility criteria.
"""

import datetime as dt
import json
import logging
import re
from pathlib import Path
from typing import Optional

import requests

LOGGER = logging.getLogger(__name__)


class NCTFetcher:
    """Fetch and process NCT data from ClinicalTrials.gov."""

    API_URL = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(self, workspace_root: Path):
        """
        Initialize NCT fetcher.

        Args:
            workspace_root: Root directory for storing NCT data (e.g., ./project)
        """
        self.workspace_root = Path(workspace_root)

    def fetch_and_save(self, nct_id: str) -> dict:
        """
        Fetch NCT data and save to workspace.

        Args:
            nct_id: NCT ID (e.g., "NCT03389555")

        Returns:
            dict with keys:
                - nct_id: str
                - eligibility_criteria: str (raw text)
                - corpus_path: Path to saved corpus.json
                - metadata_path: Path to saved metadata.json

        Raises:
            ValueError: If NCT ID format is invalid
            RuntimeError: If fetch fails
        """
        # Validate NCT ID format
        if not re.fullmatch(r"NCT\d{8}", nct_id, re.IGNORECASE):
            raise ValueError(f"Invalid NCT ID format: {nct_id}. Expected NCT######## (8 digits)")

        nct_id = nct_id.upper()
        LOGGER.info(f"Fetching NCT data for {nct_id}...")

        # Fetch from ClinicalTrials.gov
        try:
            response = requests.get(f"{self.API_URL}/{nct_id}", timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch {nct_id} from ClinicalTrials.gov: {e}")

        study_data = response.json()

        # Extract eligibility criteria
        eligibility_text = self._extract_eligibility(study_data)
        if not eligibility_text:
            LOGGER.warning(f"No eligibility criteria found for {nct_id}")

        # Create project directory structure
        project_dir = self.workspace_root / nct_id
        lit_dir = project_dir / "lit"
        lit_dir.mkdir(parents=True, exist_ok=True)

        # Save corpus.json (same format as existing projects)
        corpus = self._create_corpus(study_data, nct_id)
        corpus_path = lit_dir / "corpus.json"
        with open(corpus_path, "w") as f:
            json.dump(corpus, f, indent=2)
        LOGGER.info(f"Saved corpus to {corpus_path}")

        # Save metadata.json
        metadata = self._create_metadata(study_data, nct_id)
        metadata_path = project_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        LOGGER.info(f"Saved metadata to {metadata_path}")

        return {
            "nct_id": nct_id,
            "eligibility_criteria": eligibility_text,
            "corpus_path": str(corpus_path),
            "metadata_path": str(metadata_path),
        }

    def _extract_eligibility(self, study_data: dict) -> str:
        """
        Extract eligibility criteria text from study data.

        Args:
            study_data: Raw ClinicalTrials.gov API response

        Returns:
            Formatted eligibility criteria string with Inclusion and Exclusion sections
        """
        protocol = study_data.get("protocolSection", {})
        eligibility_module = protocol.get("eligibilityModule", {})

        # Get raw criteria text
        criteria_text = eligibility_module.get("eligibilityCriteria", "")

        if not criteria_text:
            return ""

        # Clean up text
        criteria_text = criteria_text.strip()

        # Return as-is (already contains "Inclusion Criteria:" and "Exclusion Criteria:" headers)
        return criteria_text

    def _create_corpus(self, study_data: dict, nct_id: str) -> dict:
        """
        Create corpus.json in the same format as existing projects.

        Args:
            study_data: Raw ClinicalTrials.gov API response
            nct_id: NCT ID

        Returns:
            Corpus dictionary
        """
        protocol = study_data.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        description = protocol.get("descriptionModule", {})

        title = identification.get("officialTitle") or identification.get("briefTitle", "")
        brief_summary = description.get("briefSummary", "")
        detailed_description = description.get("detailedDescription", "")

        # Combine abstract and full text
        abstract = brief_summary
        full_text = f"{brief_summary}\n\n{detailed_description}".strip()

        now = dt.datetime.now(dt.timezone.utc)

        return {
            "schema_version": "lit.v1",
            "documents": [
                {
                    "source": "clinicaltrials",
                    "identifier": nct_id,
                    "title": title,
                    "abstract": abstract,
                    "full_text": full_text,
                    "fetched_at": now.isoformat(),
                    "url": f"https://clinicaltrials.gov/study/{nct_id}",
                    "metadata": {
                        "nct_id": nct_id,
                        "retrieved_at": now.isoformat(),
                        "full_study_data": study_data,
                    },
                }
            ],
        }

    def _create_metadata(self, study_data: dict, nct_id: str) -> dict:
        """
        Create metadata.json for the project.

        Args:
            study_data: Raw ClinicalTrials.gov API response
            nct_id: NCT ID

        Returns:
            Metadata dictionary
        """
        protocol = study_data.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})

        title = identification.get("officialTitle") or identification.get("briefTitle", "")
        now = dt.datetime.now(dt.timezone.utc)

        return {
            "study_id": nct_id,
            "name": title,
            "nct_id": nct_id,
            "research_question": "",  # Can be filled in later
            "medicine_family": None,
            "medicine_generic": None,
            "medicine_brand": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }


def fetch_nct_eligibility(nct_id: str, workspace_root: Optional[Path] = None) -> dict:
    """
    Convenience function to fetch NCT eligibility criteria.

    Args:
        nct_id: NCT ID (e.g., "NCT03389555")
        workspace_root: Workspace directory (defaults to ./project)

    Returns:
        dict with:
            - nct_id: str
            - eligibility_criteria: str
            - corpus_path: str
            - metadata_path: str

    Example:
        >>> result = fetch_nct_eligibility("NCT03389555")
        >>> print(result["eligibility_criteria"])
        Inclusion Criteria:
        1. Adult patient (age ≥ 18 years)
        ...
    """
    if workspace_root is None:
        workspace_root = Path.cwd() / "project"

    fetcher = NCTFetcher(workspace_root)
    return fetcher.fetch_and_save(nct_id)
