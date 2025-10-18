"""
NCT-based caching system for Trialist Hybrid Pipeline.

Caches validated mappings to avoid redundant LLM calls.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from agents.trialist_hybrid.models import PipelineOutput


class CacheStatus:
    """Cache status constants."""
    DRAFT = "draft"  # Initial state, not validated
    VALIDATED = "validated"  # Manually verified as accurate
    STALE = "stale"  # MIMIC version changed, needs re-validation


class TrialistCache:
    """
    Manages caching for Trialist Hybrid Pipeline results.

    Cache Strategy:
    1. Store pipeline results by NCT ID
    2. Track validation status (draft/validated/stale)
    3. Reuse validated mappings automatically
    4. Invalidate on MIMIC version change
    """

    def __init__(self, workspace_root: Path, mimic_version: str = "3.1"):
        """
        Initialize cache manager.

        Args:
            workspace_root: Root directory for project data
            mimic_version: MIMIC-IV version (for invalidation)
        """
        self.workspace_root = Path(workspace_root)
        self.mimic_version = mimic_version

    def _get_cache_dir(self, nct_id: str) -> Path:
        """Get cache directory for NCT ID."""
        return self.workspace_root / nct_id / "trialist_hybrid"

    def _get_cache_metadata_path(self, nct_id: str) -> Path:
        """Get cache metadata file path."""
        return self._get_cache_dir(nct_id) / "cache_metadata.json"

    def _get_validated_mapping_path(self, nct_id: str) -> Path:
        """Get validated mapping file path."""
        return self._get_cache_dir(nct_id) / "validated_mapping.json"

    def _compute_criteria_hash(self, eligibility_criteria: str) -> str:
        """
        Compute hash of eligibility criteria text.

        Used to detect if criteria changed for same NCT ID.
        """
        return hashlib.sha256(eligibility_criteria.encode()).hexdigest()[:16]

    def get_cache_status(self, nct_id: str) -> Optional[str]:
        """
        Get current cache status for NCT ID.

        Returns:
            CacheStatus constant or None if no cache exists
        """
        metadata_path = self._get_cache_metadata_path(nct_id)
        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            # Check MIMIC version compatibility
            if metadata.get("mimic_version") != self.mimic_version:
                return CacheStatus.STALE

            return metadata.get("cache_status", CacheStatus.DRAFT)

        except Exception as e:
            print(f"Error reading cache metadata: {e}")
            return None

    def get_cached_result(self, nct_id: str, eligibility_criteria: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached pipeline result if valid.

        Args:
            nct_id: NCT trial identifier
            eligibility_criteria: Raw criteria text (for hash verification)

        Returns:
            Cached result dict or None if cache invalid/missing
        """
        # Check cache status
        status = self.get_cache_status(nct_id)
        if status != CacheStatus.VALIDATED:
            return None

        # Verify criteria hash
        metadata_path = self._get_cache_metadata_path(nct_id)
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        current_hash = self._compute_criteria_hash(eligibility_criteria)
        if metadata.get("criteria_hash") != current_hash:
            # Criteria changed, cache invalid
            return None

        # Load cached result
        cached_path = self._get_validated_mapping_path(nct_id)
        if not cached_path.exists():
            return None

        try:
            with open(cached_path, "r") as f:
                result = json.load(f)

            # Update reuse count
            metadata["reuse_count"] = metadata.get("reuse_count", 0) + 1
            metadata["last_used_at"] = datetime.utcnow().isoformat()
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            return result

        except Exception as e:
            print(f"Error loading cached result: {e}")
            return None

    def save_draft_result(
        self,
        nct_id: str,
        eligibility_criteria: str,
        pipeline_result: PipelineOutput
    ) -> None:
        """
        Save pipeline result as draft (unvalidated).

        Args:
            nct_id: NCT trial identifier
            eligibility_criteria: Raw criteria text
            pipeline_result: Pipeline output to cache
        """
        cache_dir = self._get_cache_dir(nct_id)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Save result
        result_path = self._get_validated_mapping_path(nct_id)
        with open(result_path, "w") as f:
            json.dump(pipeline_result.model_dump(), f, indent=2)

        # Save metadata
        metadata = {
            "nct_id": nct_id,
            "cache_version": "1.0",
            "cache_status": CacheStatus.DRAFT,
            "created_at": datetime.utcnow().isoformat(),
            "validated_at": None,
            "validated_by": None,
            "validation_notes": None,
            "total_criteria": pipeline_result.summary.total_criteria,
            "accuracy_score": pipeline_result.summary.avg_confidence,
            "mimic_version": self.mimic_version,
            "pipeline_version": "2.0",
            "criteria_hash": self._compute_criteria_hash(eligibility_criteria),
            "reuse_count": 0,
            "last_used_at": None,
        }

        metadata_path = self._get_cache_metadata_path(nct_id)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def validate_cache(
        self,
        nct_id: str,
        validated_by: str,
        validation_notes: Optional[str] = None
    ) -> bool:
        """
        Mark cache as validated (manually verified).

        Args:
            nct_id: NCT trial identifier
            validated_by: User/email who validated
            validation_notes: Optional validation comments

        Returns:
            True if validation successful, False otherwise
        """
        metadata_path = self._get_cache_metadata_path(nct_id)
        if not metadata_path.exists():
            return False

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            # Update validation status
            metadata["cache_status"] = CacheStatus.VALIDATED
            metadata["validated_at"] = datetime.utcnow().isoformat()
            metadata["validated_by"] = validated_by
            metadata["validation_notes"] = validation_notes

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            return True

        except Exception as e:
            print(f"Error validating cache: {e}")
            return False

    def invalidate_cache(self, nct_id: str, reason: str = "User request") -> bool:
        """
        Mark cache as stale (needs re-validation).

        Args:
            nct_id: NCT trial identifier
            reason: Reason for invalidation

        Returns:
            True if invalidation successful
        """
        metadata_path = self._get_cache_metadata_path(nct_id)
        if not metadata_path.exists():
            return False

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            metadata["cache_status"] = CacheStatus.STALE
            metadata["invalidated_at"] = datetime.utcnow().isoformat()
            metadata["invalidation_reason"] = reason

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            return True

        except Exception as e:
            print(f"Error invalidating cache: {e}")
            return False

    def delete_cache(self, nct_id: str) -> bool:
        """
        Completely remove cache for NCT ID.

        Args:
            nct_id: NCT trial identifier

        Returns:
            True if deletion successful
        """
        try:
            cache_dir = self._get_cache_dir(nct_id)
            if not cache_dir.exists():
                return False

            # Remove cache files
            validated_path = self._get_validated_mapping_path(nct_id)
            metadata_path = self._get_cache_metadata_path(nct_id)

            if validated_path.exists():
                validated_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

            return True

        except Exception as e:
            print(f"Error deleting cache: {e}")
            return False

    def list_cached_ncts(self) -> list[Dict[str, Any]]:
        """
        List all NCT IDs with cached results.

        Returns:
            List of cache metadata dicts
        """
        cached = []

        for nct_dir in self.workspace_root.iterdir():
            if not nct_dir.is_dir():
                continue

            metadata_path = self._get_cache_metadata_path(nct_dir.name)
            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                cached.append(metadata)
            except Exception:
                continue

        return cached
