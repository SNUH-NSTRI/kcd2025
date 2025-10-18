"""
Shared criteria-level caching system.

Caches individual criterion mappings (not entire NCT trials).
Example: "Age >= 18" → hosp.patients mapping is reused across all NCTs.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class SharedCriterionCache:
    """
    Global cache for criterion-level MIMIC-IV mappings.

    Cache Key: Hash of normalized criterion text
    Cache Value: MIMIC-IV mapping (table, columns, itemids, etc.)

    Example:
    - "Age >= 18 years" → hosp.patients mapping
    - "Lactate > 2 mmol/L" → hosp.labevents, itemid=50813
    - "Pregnant" → hosp.diagnoses_icd, ICD codes
    """

    def __init__(self, cache_dir: Path):
        """
        Initialize shared cache.

        Args:
            cache_dir: Directory to store shared cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.cache_dir / "shared_criteria_cache.json"
        self.metadata_file = self.cache_dir / "cache_metadata.json"

        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load cache: {e}")
                self.cache = {}
        else:
            self.cache = {}

        # Load metadata
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    self.metadata = json.load(f)
            except Exception:
                self.metadata = self._init_metadata()
        else:
            self.metadata = self._init_metadata()

    def _init_metadata(self) -> Dict[str, Any]:
        """Initialize cache metadata."""
        return {
            "version": "1.0",
            "mimic_version": "3.1",
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": None,
            "total_entries": 0,
            "hit_count": 0,
            "miss_count": 0,
            "hit_rate": 0.0
        }

    def _save_cache(self) -> None:
        """Persist cache to disk."""
        try:
            # Save cache data
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)

            # Update metadata
            self.metadata["last_updated"] = datetime.utcnow().isoformat()
            self.metadata["total_entries"] = len(self.cache)
            total = self.metadata["hit_count"] + self.metadata["miss_count"]
            self.metadata["hit_rate"] = (
                self.metadata["hit_count"] / total if total > 0 else 0.0
            )

            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)

        except Exception as e:
            print(f"Error saving cache: {e}")

    def _normalize_criterion(self, criterion_text: str) -> str:
        """
        Normalize criterion text for consistent hashing.

        Removes extra spaces, lowercases, etc.
        """
        normalized = criterion_text.lower().strip()
        normalized = " ".join(normalized.split())  # Remove multiple spaces
        return normalized

    def _compute_cache_key(self, criterion_text: str) -> str:
        """
        Compute cache key from criterion text.

        Uses SHA256 hash of normalized text.
        """
        normalized = self._normalize_criterion(criterion_text)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def get(self, criterion_text: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached mapping for criterion.

        Args:
            criterion_text: Criterion text to look up

        Returns:
            Cached mapping dict or None if not found
        """
        cache_key = self._compute_cache_key(criterion_text)

        if cache_key in self.cache:
            # Cache hit
            entry = self.cache[cache_key]
            entry["hit_count"] = entry.get("hit_count", 0) + 1
            entry["last_used"] = datetime.utcnow().isoformat()

            self.metadata["hit_count"] += 1
            self._save_cache()

            return entry["mapping"]
        else:
            # Cache miss
            self.metadata["miss_count"] += 1
            return None

    def set(
        self,
        criterion_text: str,
        mapping: Dict[str, Any],
        validated: bool = False,
        source_nct: Optional[str] = None
    ) -> None:
        """
        Store criterion mapping in cache.

        Args:
            criterion_text: Original criterion text
            mapping: MIMIC-IV mapping dict
            validated: Whether mapping is manually verified
            source_nct: NCT ID where this mapping was first used
        """
        cache_key = self._compute_cache_key(criterion_text)

        entry = {
            "criterion_text": criterion_text,
            "normalized_text": self._normalize_criterion(criterion_text),
            "mapping": mapping,
            "validated": validated,
            "source_nct": source_nct,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": datetime.utcnow().isoformat(),
            "hit_count": 0
        }

        self.cache[cache_key] = entry
        self._save_cache()

    def bulk_set(self, criteria_mappings: List[Dict[str, Any]]) -> int:
        """
        Bulk insert multiple criterion mappings.

        Args:
            criteria_mappings: List of dicts with keys:
                - criterion_text
                - mapping
                - validated (optional)
                - source_nct (optional)

        Returns:
            Number of entries added
        """
        count = 0
        for item in criteria_mappings:
            self.set(
                criterion_text=item["criterion_text"],
                mapping=item["mapping"],
                validated=item.get("validated", False),
                source_nct=item.get("source_nct")
            )
            count += 1

        return count

    def validate(self, criterion_text: str, validated_by: str) -> bool:
        """
        Mark cached mapping as validated.

        Args:
            criterion_text: Criterion to validate
            validated_by: User/email who validated

        Returns:
            True if validation successful
        """
        cache_key = self._compute_cache_key(criterion_text)

        if cache_key not in self.cache:
            return False

        self.cache[cache_key]["validated"] = True
        self.cache[cache_key]["validated_at"] = datetime.utcnow().isoformat()
        self.cache[cache_key]["validated_by"] = validated_by

        self._save_cache()
        return True

    def delete(self, criterion_text: str) -> bool:
        """
        Remove criterion from cache.

        Args:
            criterion_text: Criterion to delete

        Returns:
            True if deletion successful
        """
        cache_key = self._compute_cache_key(criterion_text)

        if cache_key in self.cache:
            del self.cache[cache_key]
            self._save_cache()
            return True

        return False

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search cache for similar criteria.

        Args:
            query: Search query
            limit: Max results to return

        Returns:
            List of matching cache entries
        """
        normalized_query = self._normalize_criterion(query)
        results = []

        for entry in self.cache.values():
            if normalized_query in entry["normalized_text"]:
                results.append({
                    "criterion_text": entry["criterion_text"],
                    "mapping": entry["mapping"],
                    "validated": entry.get("validated", False),
                    "hit_count": entry.get("hit_count", 0)
                })

        # Sort by hit count (most popular first)
        results.sort(key=lambda x: x["hit_count"], reverse=True)
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Cache metadata with stats
        """
        # Refresh stats
        self.metadata["total_entries"] = len(self.cache)
        total = self.metadata["hit_count"] + self.metadata["miss_count"]
        self.metadata["hit_rate"] = (
            self.metadata["hit_count"] / total if total > 0 else 0.0
        )

        # Add popular criteria
        popular = sorted(
            self.cache.values(),
            key=lambda x: x.get("hit_count", 0),
            reverse=True
        )[:10]

        return {
            **self.metadata,
            "popular_criteria": [
                {
                    "text": entry["criterion_text"],
                    "hit_count": entry.get("hit_count", 0),
                    "validated": entry.get("validated", False)
                }
                for entry in popular
            ]
        }

    def clear(self) -> None:
        """Clear entire cache."""
        self.cache = {}
        self.metadata = self._init_metadata()
        self._save_cache()

    def export_validated_only(self, output_path: Path) -> int:
        """
        Export only validated mappings to file.

        Args:
            output_path: Path to save validated mappings

        Returns:
            Number of validated entries exported
        """
        validated = {
            key: entry
            for key, entry in self.cache.items()
            if entry.get("validated", False)
        }

        with open(output_path, "w") as f:
            json.dump(validated, f, indent=2)

        return len(validated)
