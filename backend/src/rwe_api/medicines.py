"""
Medicine data management for RWE API.
Loads and manages medicine variants from YAML configuration.
"""

import yaml
from pathlib import Path
from pydantic import BaseModel
from typing import List


class Medicine(BaseModel):
    """Medicine variant model with parent-child relationship."""
    parent: str
    variant: str
    display: str


# Global medicine data storage
medicines_list: List[Medicine] = []
valid_medicine_variants: set[str] = set()


def load_medicines_from_yaml(yaml_path: str | Path) -> List[Medicine]:
    """
    Loads and flattens medicine data from the YAML file.

    Args:
        yaml_path: Path to medicines_variants.yaml file

    Returns:
        List of Medicine objects with parent, variant, and display fields
    """
    flat_list = []

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

        for parent, variants in data.get('medications', {}).items():
            for variant in variants:
                flat_list.append(
                    Medicine(
                        parent=parent,
                        variant=variant,
                        display=f"{parent} - {variant}"
                    )
                )

    return flat_list


def initialize_medicines(yaml_path: str | Path) -> None:
    """
    Initialize global medicine data on application startup.

    Args:
        yaml_path: Path to medicines_variants.yaml file
    """
    global medicines_list, valid_medicine_variants

    medicines_list.clear()
    valid_medicine_variants.clear()

    loaded = load_medicines_from_yaml(yaml_path)
    medicines_list.extend(loaded)
    valid_medicine_variants.update(med.variant for med in loaded)

    print(f"✅ Loaded {len(medicines_list)} medicine variants from {len(set(m.parent for m in medicines_list))} parent families")


def get_valid_medicine_variants() -> set[str]:
    """
    Returns a set of all valid medicine variant names.
    Used for O(1) validation lookups.
    """
    return valid_medicine_variants


def search_medicines(query: str, limit: int = 20) -> List[Medicine]:
    """
    Search medicines by case-insensitive substring match.

    Args:
        query: Search query string
        limit: Maximum number of results to return

    Returns:
        List of matching Medicine objects
    """
    if not query:
        return []

    query_lower = query.lower()
    results = [
        med for med in medicines_list
        if query_lower in med.display.lower()
    ]

    return results[:limit]
