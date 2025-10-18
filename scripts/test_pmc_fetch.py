#!/usr/bin/env python3
"""
Test script for PMC paper fetching functionality.

Usage:
    PYTHONPATH=backend/src ./venv/bin/python scripts/test_pmc_fetch.py
"""

import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from agents.trialist_hybrid.pmc_fetcher import PMCFetcher


def main():
    print("=" * 70)
    print("PMC Paper Fetcher - Test Script")
    print("=" * 70)

    # Initialize fetcher
    workspace_root = Path(__file__).parent.parent / "workspace"
    fetcher = PMCFetcher(workspace_root=workspace_root)

    # Test NCT ID
    nct_id = "NCT03389555"

    print(f"\n🔍 Searching PubMed for papers mentioning {nct_id}...")

    # Fetch and save
    result = fetcher.fetch_and_save(
        nct_id=nct_id,
        max_results=1,
        sort_by="pub_date",
        append=True
    )

    print(f"\n📊 Results:")
    print(f"   NCT ID: {result['nct_id']}")
    print(f"   Papers found: {result['papers_found']}")

    if result['papers_found'] > 0:
        print(f"   Corpus saved to: {result['corpus_path']}")

        print(f"\n📄 Most Recent Paper:")
        paper = result['papers'][0]
        print(f"   Title: {paper['title']}")
        print(f"   Authors: {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}")
        print(f"   Journal: {paper['journal']}")
        print(f"   Published: {paper['pub_date']}")
        print(f"   DOI: {paper['doi']}")
        print(f"   URL: {paper['url']}")

        print(f"\n📝 Abstract Preview:")
        abstract = paper['abstract']
        print(f"   {abstract[:200]}..." if len(abstract) > 200 else f"   {abstract}")
    else:
        print("\n⚠️  No papers found in PubMed mentioning this NCT ID")

    print("\n" + "=" * 70)
    print("✅ Test completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
