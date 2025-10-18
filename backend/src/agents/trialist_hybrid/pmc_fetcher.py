"""
PMC (PubMed Central) Paper Fetcher for Clinical Trials.

Fetches recent research papers from PubMed Central that reference a given NCT ID
using NCBI E-utilities API.
"""

import datetime as dt
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

import requests

LOGGER = logging.getLogger(__name__)


class PMCFetcher:
    """Fetch and process PMC papers related to clinical trials."""

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    # NCBI recommends 3 requests/sec without API key, 10 requests/sec with key
    REQUEST_DELAY = 0.34  # ~3 requests/sec

    def __init__(self, workspace_root: Path, email: Optional[str] = None):
        """
        Initialize PMC fetcher.

        Args:
            workspace_root: Root directory for storing project data (e.g., ./project)
            email: Optional email for NCBI API (recommended for higher rate limits)
        """
        self.workspace_root = Path(workspace_root)
        self.email = email
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Enforce NCBI API rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def search_by_nct(
        self,
        nct_id: str,
        max_results: int = 5,
        sort_by: str = "pub_date"
    ) -> List[str]:
        """
        Search PubMed for papers mentioning the NCT ID.

        Args:
            nct_id: NCT ID (e.g., "NCT03389555")
            max_results: Maximum number of PMIDs to return
            sort_by: Sort order ("pub_date" for most recent first, "relevance" for best match)

        Returns:
            List of PMIDs (PubMed IDs) as strings

        Raises:
            RuntimeError: If search fails
        """
        self._rate_limit()

        # Build search query - search for NCT ID in all fields
        query = f"{nct_id}[ALL]"

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "sort": sort_by,
            "retmode": "json",
        }

        if self.email:
            params["email"] = self.email

        try:
            LOGGER.info(f"Searching PubMed for papers mentioning {nct_id}...")
            response = requests.get(self.ESEARCH_URL, params=params, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"PubMed search failed for {nct_id}: {e}")

        data = response.json()
        pmid_list = data.get("esearchresult", {}).get("idlist", [])

        LOGGER.info(f"Found {len(pmid_list)} papers for {nct_id}")
        return pmid_list

    def fetch_paper_details(self, pmids: List[str]) -> List[Dict]:
        """
        Fetch detailed metadata for papers by PMID.

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of paper metadata dictionaries with keys:
                - pmid: str
                - pmc_id: Optional[str] (PMC ID if available)
                - doi: Optional[str]
                - title: str
                - abstract: str
                - authors: List[str]
                - journal: str
                - pub_date: str (YYYY-MM-DD format)
                - url: str (PubMed URL)

        Raises:
            RuntimeError: If fetch fails
        """
        if not pmids:
            return []

        self._rate_limit()

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }

        if self.email:
            params["email"] = self.email

        try:
            LOGGER.info(f"Fetching details for {len(pmids)} papers...")
            response = requests.get(self.EFETCH_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"PubMed fetch failed: {e}")

        # Parse XML response
        papers = self._parse_pubmed_xml(response.text, pmids)
        return papers

    def _parse_pubmed_xml(self, xml_text: str, pmids: List[str]) -> List[Dict]:
        """
        Parse PubMed XML response to extract paper metadata.

        Args:
            xml_text: XML response from NCBI Efetch
            pmids: List of PMIDs for fallback

        Returns:
            List of paper metadata dictionaries
        """
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            LOGGER.error("xml.etree.ElementTree not available")
            return []

        papers = []

        try:
            root = ET.fromstring(xml_text)
            articles = root.findall(".//PubmedArticle")

            for article in articles:
                try:
                    # Extract PMID
                    pmid_elem = article.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else None

                    # Extract PMC ID
                    pmc_id = None
                    article_ids = article.findall(".//ArticleId")
                    for aid in article_ids:
                        if aid.get("IdType") == "pmc":
                            pmc_id = aid.text
                            break

                    # Extract DOI
                    doi = None
                    for aid in article_ids:
                        if aid.get("IdType") == "doi":
                            doi = aid.text
                            break

                    # Extract title
                    title_elem = article.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None else "No title"

                    # Extract abstract
                    abstract_texts = article.findall(".//AbstractText")
                    abstract = " ".join(
                        a.text for a in abstract_texts if a.text
                    ) if abstract_texts else ""

                    # Extract authors
                    author_list = article.findall(".//Author")
                    authors = []
                    for author in author_list:
                        lastname = author.find("LastName")
                        forename = author.find("ForeName")
                        if lastname is not None:
                            name = lastname.text
                            if forename is not None:
                                name = f"{forename.text} {name}"
                            authors.append(name)

                    # Extract journal
                    journal_elem = article.find(".//Journal/Title")
                    journal = journal_elem.text if journal_elem is not None else ""

                    # Extract publication date
                    pub_date_elem = article.find(".//PubDate")
                    pub_date = self._extract_pub_date(pub_date_elem)

                    paper = {
                        "pmid": pmid,
                        "pmc_id": pmc_id,
                        "doi": doi,
                        "title": title,
                        "abstract": abstract,
                        "authors": authors,
                        "journal": journal,
                        "pub_date": pub_date,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    }

                    papers.append(paper)

                except Exception as e:
                    LOGGER.warning(f"Failed to parse article: {e}")
                    continue

        except Exception as e:
            LOGGER.error(f"Failed to parse PubMed XML: {e}")

        return papers

    def _extract_pub_date(self, pub_date_elem) -> str:
        """
        Extract publication date from PubDate XML element.

        Args:
            pub_date_elem: XML element containing publication date

        Returns:
            Date string in YYYY-MM-DD format, or empty string if unavailable
        """
        if pub_date_elem is None:
            return ""

        year = pub_date_elem.find("Year")
        month = pub_date_elem.find("Month")
        day = pub_date_elem.find("Day")

        year_str = year.text if year is not None else ""
        month_str = month.text if month is not None else "01"
        day_str = day.text if day is not None else "01"

        # Convert month name to number if necessary
        month_map = {
            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
            "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
            "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
        }

        if month_str in month_map:
            month_str = month_map[month_str]
        elif not month_str.isdigit():
            month_str = "01"

        try:
            return f"{year_str}-{month_str.zfill(2)}-{day_str.zfill(2)}"
        except:
            return year_str if year_str else ""

    def save_to_corpus(
        self,
        nct_id: str,
        papers: List[Dict],
        append: bool = True
    ) -> Path:
        """
        Save PMC papers to corpus.json in the project directory.

        Args:
            nct_id: NCT ID for the project
            papers: List of paper metadata dictionaries
            append: If True, append to existing corpus; if False, overwrite

        Returns:
            Path to the updated corpus.json file

        Raises:
            RuntimeError: If save fails
        """
        project_dir = self.workspace_root / nct_id
        lit_dir = project_dir / "lit"
        lit_dir.mkdir(parents=True, exist_ok=True)

        corpus_path = lit_dir / "corpus.json"

        # Load existing corpus if appending
        existing_documents = []
        if append and corpus_path.exists():
            try:
                with open(corpus_path, "r") as f:
                    corpus_data = json.load(f)
                    existing_documents = corpus_data.get("documents", [])
                    LOGGER.info(f"Loaded {len(existing_documents)} existing documents from corpus")
            except Exception as e:
                LOGGER.warning(f"Failed to load existing corpus: {e}")

        # Convert papers to corpus document format
        now = dt.datetime.now(dt.timezone.utc)
        new_documents = []

        for paper in papers:
            doc = {
                "source": "pmc",
                "identifier": paper.get("pmid", ""),
                "title": paper.get("title", ""),
                "abstract": paper.get("abstract", ""),
                "full_text": paper.get("abstract", ""),  # Use abstract as full text
                "fetched_at": now.isoformat(),
                "url": paper.get("url", ""),
                "metadata": {
                    "pmid": paper.get("pmid"),
                    "pmc_id": paper.get("pmc_id"),
                    "doi": paper.get("doi"),
                    "authors": paper.get("authors", []),
                    "journal": paper.get("journal", ""),
                    "pub_date": paper.get("pub_date", ""),
                    "retrieved_at": now.isoformat(),
                },
            }
            new_documents.append(doc)

        # Combine documents
        all_documents = existing_documents + new_documents

        # Create corpus structure
        corpus = {
            "schema_version": "lit.v1",
            "documents": all_documents,
        }

        # Save to file
        try:
            with open(corpus_path, "w") as f:
                json.dump(corpus, f, indent=2)
            LOGGER.info(f"Saved {len(papers)} PMC papers to {corpus_path}")
            return corpus_path
        except Exception as e:
            raise RuntimeError(f"Failed to save corpus: {e}")

    def fetch_and_save(
        self,
        nct_id: str,
        max_results: int = 1,
        sort_by: str = "pub_date",
        append: bool = True
    ) -> Dict:
        """
        Complete workflow: search PMC, fetch papers, and save to corpus.

        Args:
            nct_id: NCT ID (e.g., "NCT03389555")
            max_results: Maximum number of papers to fetch (default: 1 for most recent)
            sort_by: Sort order ("pub_date" for most recent, "relevance" for best match)
            append: If True, append to existing corpus; if False, overwrite

        Returns:
            dict with keys:
                - nct_id: str
                - papers_found: int
                - papers: List[Dict] (paper metadata)
                - corpus_path: str (path to corpus.json)

        Example:
            >>> fetcher = PMCFetcher(workspace_root=Path("./project"))
            >>> result = fetcher.fetch_and_save("NCT03389555", max_results=1)
            >>> print(result["papers"][0]["title"])
        """
        LOGGER.info(f"Starting PMC fetch for {nct_id}...")

        # Step 1: Search PubMed for papers
        pmids = self.search_by_nct(nct_id, max_results=max_results, sort_by=sort_by)

        if not pmids:
            LOGGER.warning(f"No PMC papers found for {nct_id}")
            return {
                "nct_id": nct_id,
                "papers_found": 0,
                "papers": [],
                "corpus_path": None,
            }

        # Step 2: Fetch paper details
        papers = self.fetch_paper_details(pmids)

        # Step 3: Save to corpus
        corpus_path = self.save_to_corpus(nct_id, papers, append=append)

        LOGGER.info(f"✅ Successfully fetched and saved {len(papers)} papers for {nct_id}")

        return {
            "nct_id": nct_id,
            "papers_found": len(papers),
            "papers": papers,
            "corpus_path": str(corpus_path),
        }
