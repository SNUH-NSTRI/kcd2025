"""
CorrectionManager: Manages human corrections and example selection.

This module handles:
- Saving user corrections to disk
- Maintaining the central index.json
- Selecting relevant examples using hybrid strategy
- Quality scoring to filter low-quality corrections
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from filelock import FileLock


class CorrectionManager:
    """
    Manages correction storage and example selection for HITL learning.

    Uses file-based storage with index.json as the single source of truth.
    Implements atomic writes with filelock for concurrency safety.
    """

    def __init__(self, corrections_dir: str):
        """
        Initialize the correction manager.

        Args:
            corrections_dir: Path to workspace/corrections directory
        """
        self.corrections_dir = Path(corrections_dir)
        self.data_dir = self.corrections_dir / "data"
        self.seed_dir = self.corrections_dir / "seed_examples"
        self.index_path = self.corrections_dir / "index.json"
        self.lock_path = self.corrections_dir / "index.lock"

        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.seed_dir.mkdir(parents=True, exist_ok=True)

        # Load or create index
        self.index = self._load_or_create_index()

    def _load_or_create_index(self) -> Dict[str, Any]:
        """
        Load existing index or create a new one if it doesn't exist.

        Returns:
            Index dictionary
        """
        if not self.index_path.exists():
            # Create empty index structure
            empty_index = {
                "trials": {},
                "by_condition": {},
                "by_keyword": {},
                "recent": [],
            }

            # Write to disk
            with open(self.index_path, "w") as f:
                json.dump(empty_index, f, indent=2)

            return empty_index

        # Load existing index
        with open(self.index_path, "r") as f:
            return json.load(f)

    @staticmethod
    def _calculate_quality_score(correction: Dict[str, Any]) -> float:
        """
        Calculate quality score for a correction.

        Scoring rules:
        - Seed curator: 1.0 (perfect)
        - Normal user: 0.75 (base)
        - Penalty for > 10 changes: -0.2
        - Penalty for empty inclusion: -0.5
        - Penalty for very short text (< 5 chars): -0.3

        Args:
            correction: Correction data dictionary

        Returns:
            Quality score between 0.0 and 1.0
        """
        # Check if this is a seed example
        corrected_by = correction.get("corrected_by", "")
        if corrected_by == "seed_curator":
            return 1.0

        # Start with base score for user corrections
        score = 0.75

        # Get extraction data
        extraction = correction.get("extraction", {})
        human_corrected = extraction.get("human_corrected", {})
        changes = extraction.get("changes", [])

        # Penalty for too many changes (> 10)
        if len(changes) > 10:
            score -= 0.2

        # Penalty for empty inclusion
        inclusion = human_corrected.get("inclusion", [])
        if len(inclusion) == 0:
            score -= 0.5

        # Penalty for very short original_text
        all_criteria = inclusion + human_corrected.get("exclusion", [])
        if all_criteria:
            avg_text_length = sum(
                len(c.get("original_text", "")) for c in all_criteria
            ) / len(all_criteria)
            if avg_text_length < 5:
                score -= 0.3

        # Clamp between 0.0 and 1.0
        return max(0.0, min(1.0, score))

    def save_correction(self, correction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a correction and update the index.

        Args:
            correction_data: Dictionary containing:
                - nct_id: NCT trial identifier
                - corrected_by: User email
                - timestamp: ISO format timestamp
                - extraction: Dict with original_ai_output, human_corrected, changes

        Returns:
            Dictionary with success status and version number
        """
        nct_id = correction_data["nct_id"]
        trial_file = self.data_dir / f"{nct_id}.json"

        # Use file lock for thread-safe operations
        with FileLock(str(self.lock_path)):
            # Load existing data or create new
            if trial_file.exists():
                with open(trial_file, "r") as f:
                    trial_data = json.load(f)
            else:
                trial_data = {
                    "nct_id": nct_id,
                    "versions": {},
                }

            # Determine next version number
            existing_versions = list(trial_data["versions"].keys())
            if existing_versions:
                last_version = max(int(v.replace("v", "")) for v in existing_versions)
                new_version = f"v{last_version + 1}"
            else:
                new_version = "v1"

            # Calculate quality score
            quality_score = self._calculate_quality_score(correction_data)

            # Add new version
            trial_data["versions"][new_version] = {
                "corrected_by": correction_data["corrected_by"],
                "timestamp": correction_data["timestamp"],
                "quality_score": quality_score,
                "extraction": correction_data["extraction"],
                "metadata": correction_data.get("metadata", {}),
            }

            # Write trial data atomically
            temp_file = trial_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(trial_data, f, indent=2)
            temp_file.replace(trial_file)

            # Update index
            index = self._load_or_create_index()
            metadata = correction_data.get("metadata", {})
            condition = metadata.get("condition", "")
            keywords = metadata.get("keywords", [])

            if nct_id not in index["trials"]:
                index["trials"][nct_id] = {
                    "latest_version": new_version,
                    "correction_count": 1,
                    "condition": condition,
                    "keywords": keywords,
                }
            else:
                index["trials"][nct_id]["latest_version"] = new_version
                index["trials"][nct_id]["correction_count"] += 1
                index["trials"][nct_id]["condition"] = condition
                index["trials"][nct_id]["keywords"] = keywords

            # Update by_condition index
            if condition:
                if condition not in index["by_condition"]:
                    index["by_condition"][condition] = []
                if nct_id not in index["by_condition"][condition]:
                    index["by_condition"][condition].append(nct_id)

            # Update by_keyword index
            for keyword in keywords:
                if keyword not in index["by_keyword"]:
                    index["by_keyword"][keyword] = []
                if nct_id not in index["by_keyword"][keyword]:
                    index["by_keyword"][keyword].append(nct_id)

            # Update recent list
            if nct_id in index["recent"]:
                index["recent"].remove(nct_id)
            index["recent"].insert(0, nct_id)
            # Keep only last 50
            index["recent"] = index["recent"][:50]

            # Write index atomically
            temp_index = self.index_path.with_suffix(".tmp")
            with open(temp_index, "w") as f:
                json.dump(index, f, indent=2)
            temp_index.replace(self.index_path)

            return {
                "success": True,
                "version": new_version,
            }

    def select_examples(
        self, study_metadata: Dict[str, Any], num: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Select relevant examples using hybrid strategy.

        Priority:
        1. Same condition
        2. Keyword overlap
        3. Recent corrections

        Args:
            study_metadata: Metadata for the study needing extraction
            num: Number of examples to select

        Returns:
            List of correction examples
        """
        # Load index
        index = self._load_or_create_index()

        # Get all user corrections
        user_corrections = []
        for nct_id in index["trials"]:
            trial_file = self.data_dir / f"{nct_id}.json"
            if trial_file.exists():
                with open(trial_file, "r") as f:
                    trial_data = json.load(f)

                # Get latest version
                latest_version = index["trials"][nct_id]["latest_version"]
                if latest_version in trial_data["versions"]:
                    version_data = trial_data["versions"][latest_version]

                    # Filter by quality score >= 0.7
                    if version_data.get("quality_score", 0.0) >= 0.7:
                        user_corrections.append({
                            "nct_id": nct_id,
                            "corrected_by": version_data["corrected_by"],
                            "extraction": version_data["extraction"],
                            "metadata": version_data.get("metadata", {}),
                            "quality_score": version_data["quality_score"],
                        })

        # Cold start: No user corrections, load seed examples
        if len(user_corrections) == 0:
            return self._load_seed_examples(num)

        # Hybrid selection strategy
        condition = study_metadata.get("condition", "")
        keywords = set(study_metadata.get("keywords", []))

        # 1. Prioritize condition match
        condition_matches = [
            c for c in user_corrections
            if c["metadata"].get("condition", "") == condition
        ]

        # 2. Prioritize keyword overlap
        keyword_matches = []
        for correction in user_corrections:
            correction_keywords = set(correction["metadata"].get("keywords", []))
            overlap = len(keywords & correction_keywords)
            if overlap > 0:
                keyword_matches.append((overlap, correction))

        # Sort by overlap count (descending)
        keyword_matches.sort(key=lambda x: x[0], reverse=True)
        keyword_corrections = [c for _, c in keyword_matches]

        # 3. Recent fallback
        recent_nct_ids = index.get("recent", [])
        recent_corrections = [
            c for c in user_corrections
            if c["nct_id"] in recent_nct_ids
        ]
        # Sort by recency
        recent_corrections.sort(
            key=lambda c: recent_nct_ids.index(c["nct_id"])
        )

        # Combine with priority (avoid duplicates)
        selected = []
        seen_nct_ids = set()

        # Add condition matches first
        for correction in condition_matches:
            if len(selected) >= num:
                break
            if correction["nct_id"] not in seen_nct_ids:
                selected.append(correction)
                seen_nct_ids.add(correction["nct_id"])

        # Add keyword matches
        for correction in keyword_corrections:
            if len(selected) >= num:
                break
            if correction["nct_id"] not in seen_nct_ids:
                selected.append(correction)
                seen_nct_ids.add(correction["nct_id"])

        # Add recent corrections
        for correction in recent_corrections:
            if len(selected) >= num:
                break
            if correction["nct_id"] not in seen_nct_ids:
                selected.append(correction)
                seen_nct_ids.add(correction["nct_id"])

        return selected

    def _load_seed_examples(self, num: int) -> List[Dict[str, Any]]:
        """
        Load seed examples from seed_examples/ directory.

        Args:
            num: Number of seed examples to load

        Returns:
            List of seed examples (up to num examples)
        """
        seed_files = list(self.seed_dir.glob("*.json"))

        examples = []
        for seed_file in seed_files[:num]:
            with open(seed_file, "r") as f:
                seed_data = json.load(f)
                examples.append(seed_data)

        return examples
