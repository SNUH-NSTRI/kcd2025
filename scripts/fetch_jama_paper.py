#!/usr/bin/env python3
"""
Fetch JAMA paper as markdown using Jina Reader API.

Usage:
    ./venv/bin/python scripts/fetch_jama_paper.py <NCT_ID> <JAMA_URL>

Example:
    ./venv/bin/python scripts/fetch_jama_paper.py NCT03389555 https://jamanetwork.com/journals/jama/fullarticle/2812345
"""

import sys
import requests
from pathlib import Path


def fetch_jama_paper(jama_url: str, nct_id: str, output_path: Path | None = None) -> str:
    """
    Fetch JAMA paper as markdown using Jina Reader API.

    Args:
        jama_url: Full JAMA article URL
        output_path: Optional path to save markdown file

    Returns:
        Markdown content as string
    """
    # Jina Reader API endpoint
    jina_url = f"https://r.jina.ai/{jama_url}"

    print(f"🔍 Fetching paper from: {jama_url}")
    print(f"📡 Using Jina Reader API: {jina_url}")

    try:
        response = requests.get(jina_url, timeout=30)
        response.raise_for_status()

        markdown_content = response.text

        print(f"✅ Successfully fetched paper ({len(markdown_content)} characters)")

        # Save to file if output_path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown_content, encoding='utf-8')
            print(f"💾 Saved to: {output_path}")

        return markdown_content

    except requests.RequestException as e:
        print(f"❌ Failed to fetch paper: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print("Usage: python fetch_jama_paper.py <NCT_ID> <JAMA_URL>")
        print("\nExample:")
        print("  python fetch_jama_paper.py NCT03389555 https://jamanetwork.com/journals/jama/fullarticle/2812345")
        sys.exit(1)

    nct_id = sys.argv[1]
    jama_url = sys.argv[2]

    # Extract article ID from URL for filename
    article_id = jama_url.split('/')[-1]
    output_dir = Path(__file__).parent.parent / "project" / nct_id / "lit"
    output_path = output_dir / f"jama_{article_id}.md"

    # Fetch and save
    markdown_content = fetch_jama_paper(jama_url, nct_id, output_path)

    # Print preview
    print("\n" + "="*70)
    print("📄 Preview (first 500 characters):")
    print("="*70)
    print(markdown_content[:500])
    print("...")
    print("="*70)


if __name__ == "__main__":
    main()
