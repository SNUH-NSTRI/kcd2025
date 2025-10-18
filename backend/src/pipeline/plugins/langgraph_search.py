from __future__ import annotations

import datetime as dt
import logging
import re
from typing import List, Sequence

from .. import models
from ..context import PipelineContext

LOGGER = logging.getLogger("rwe.langgraph.search")


class LangGraphLiteratureFetcher:
    """
    Literature fetcher that retrieves structured records from clinicaltrials.gov.
    """

    def __init__(self, default_source: str = "clinicaltrials") -> None:
        self.default_source = default_source

    def run(
        self,
        params: models.SearchLitParams,
        ctx: PipelineContext,
    ) -> models.LiteratureCorpus:
        _ = ctx  # clinicaltrials.gov fetch does not require pipeline context

        requested_sources = [src.lower() for src in (params.sources or (self.default_source,))]
        if not requested_sources:
            requested_sources = [self.default_source]

        unsupported: List[str] = []
        clinicaltrials_requested = False
        for source_key in requested_sources:
            if source_key == "clinicaltrials":
                clinicaltrials_requested = True
            elif source_key == "pubmed":
                LOGGER.info(
                    "Skipping PubMed source for search agent; only clinicaltrials.gov structured data is retrieved."
                )
            else:
                unsupported.append(source_key)

        if unsupported:
            LOGGER.warning(
                "Ignoring unsupported literature sources %s; only clinicaltrials.gov is supported.",
                unsupported,
            )

        if not clinicaltrials_requested:
            LOGGER.info(
                "Falling back to clinicaltrials.gov because no supported sources were requested."
            )

        docs = self._fetch_clinical_trials(params)
        per_source: dict[str, List[models.LiteratureDocument]] = {"clinicaltrials": docs}
        sources = ["clinicaltrials"]

        collected = [doc for key in sources for doc in per_source.get(key, [])]
        if not collected:
            raise ValueError("No clinicaltrials.gov studies retrieved for the given query.")

        trimmed = self._limit_results_round_robin(per_source, sources, params.max_records)
        LOGGER.info("Retrieved %d documents from literature sources.", len(trimmed))
        return models.LiteratureCorpus(schema_version="lit.v1", documents=trimmed)

    @staticmethod
    def _limit_results_round_robin(
        per_source: dict[str, List[models.LiteratureDocument]],
        ordered_sources: Sequence[str],
        max_records: int | None,
    ) -> List[models.LiteratureDocument]:
        if not max_records:
            return [doc for source in ordered_sources for doc in per_source.get(source, [])]

        results: List[models.LiteratureDocument] = []
        index = 0
        while len(results) < max_records:
            added = False
            for source in ordered_sources:
                docs = per_source.get(source, [])
                if index < len(docs):
                    results.append(docs[index])
                    added = True
                    if len(results) >= max_records:
                        break
            if not added:
                break
            index += 1
        return results

    def _fetch_clinical_trials(self, params: models.SearchLitParams) -> List[models.LiteratureDocument]:
        try:
            import requests
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "The requests package is required for clinicaltrials.gov fetching."
            ) from exc

        api_url = "https://clinicaltrials.gov/api/v2/studies"

        raw_keywords = params.keywords or []
        nct_ids: List[str] = []
        free_keywords: List[str] = []
        for keyword in raw_keywords:
            candidate = (keyword or "").strip()
            if not candidate:
                continue
            if re.fullmatch(r"(?i)NCT\d{8}", candidate):
                nct_ids.append(candidate.upper())
            else:
                free_keywords.append(candidate)

        query = None
        if params.disease_code or free_keywords:
            query = self._compose_query(params.disease_code, free_keywords)

        now = dt.datetime.now(dt.timezone.utc)
        collected: List[models.LiteratureDocument] = []
        seen: set[str] = set()

        if query:
            page_size = params.max_records or 10
            resp = requests.get(
                api_url,
                params={"query.term": query, "pageSize": page_size},
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
            studies = payload.get("studies", [])
            for study in studies:
                doc = self._study_to_document(
                    study,
                    now,
                    metadata_overrides={
                        "query": query,
                        "search_mode": "query",
                    },
                    fetch_papers=params.fetch_papers,
                )
                if doc.identifier in seen:
                    continue
                seen.add(doc.identifier)
                collected.append(doc)

        for nct_id in nct_ids:
            try:
                resp = requests.get(f"{api_url}/{nct_id}", timeout=10)
                resp.raise_for_status()
            except Exception as exc:
                LOGGER.warning("Failed to fetch NCT %s from clinicaltrials.gov: %s", nct_id, exc)
                continue
            study = resp.json()
            doc = self._study_to_document(
                study,
                now,
                metadata_overrides={
                    "lookup_term": nct_id,
                    "search_mode": "nct-id",
                },
                fetch_papers=params.fetch_papers,
            )
            if doc.identifier in seen:
                continue
            seen.add(doc.identifier)
            collected.append(doc)

        if params.require_full_text:
            LOGGER.info(
                "clinicaltrials.gov does not provide open-access PDFs; returning structured metadata only despite --require-full-text."
            )
        return collected

    @staticmethod
    def _compose_query(disease_code: str, keywords: Sequence[str]) -> str:
        parts: List[str] = []
        disease = (disease_code or "").strip()
        if disease:
            parts.append(disease)

        for keyword in keywords:
            cleaned = (keyword or "").strip()
            if cleaned:
                parts.append(cleaned)

        if not parts:
            raise ValueError(
                "At least one disease code, drug/intervention keyword, or NCT ID is required to query clinicaltrials.gov."
            )
        return " ".join(parts)

    @staticmethod
    def _get_publication_ids(study: dict) -> List[tuple[str, str]]:
        """
        Extract publication identifiers (DOIs, PMIDs) from ClinicalTrials.gov study.

        Args:
            study: Study data from ClinicalTrials.gov API

        Returns:
            List of (type, id) tuples, e.g., [("doi", "10.1056/NEJMoa..."), ("pmid", "12345")]
        """
        ids: List[tuple[str, str]] = []
        try:
            references = study.get("protocolSection", {}).get("referencesModule", {}).get("references", [])
            for ref in references:
                if not isinstance(ref, dict):
                    continue
                # Extract DOI (preferred for Unpaywall)
                if doi := ref.get("doi"):
                    ids.append(("doi", doi))
                # Extract PMID (can be converted to DOI if needed)
                elif pmid := ref.get("pmid"):
                    ids.append(("pmid", pmid))
        except Exception as exc:
            LOGGER.warning("Could not parse publication references: %s", exc)
        return ids

    @staticmethod
    def _get_pmcid_from_pmid(pmid: str) -> str | None:
        """
        Convert PMID to PMCID using NCBI ID Converter API.

        Args:
            pmid: PubMed ID

        Returns:
            PMCID string or None if not available
        """
        try:
            import requests
        except ImportError:
            return None

        try:
            idconv_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={pmid}&format=json"
            resp = requests.get(idconv_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            records = data.get("records", [])
            if records and "pmcid" in records[0]:
                pmcid = records[0]["pmcid"]
                LOGGER.info(f"Converted PMID {pmid} to PMCID {pmcid}")
                return pmcid
            return None
        except Exception as exc:
            LOGGER.warning(f"Failed to convert PMID {pmid} to PMCID: {exc}")
            return None

    @staticmethod
    def _fetch_paper_from_pmc(pmcid: str) -> str | None:
        """
        Fetch full-text paper from PubMed Central (PMC) in markdown format.

        Args:
            pmcid: PMC ID (e.g., 'PMC9948395')

        Returns:
            Markdown formatted text of the paper, or None if not available
        """
        try:
            import requests
            import xml.etree.ElementTree as ET
        except ImportError as exc:
            LOGGER.warning("Required dependencies not available for PMC fetching: %s", exc)
            return None

        try:
            # Remove PMC prefix if present
            pmc_number = pmcid.replace("PMC", "")

            # Fetch XML from PMC
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
            fetch_params = {"db": "pmc", "id": pmc_number, "retmode": "xml"}

            LOGGER.info(f"Fetching full text from PMC: {pmcid}")
            resp = requests.get(f"{base_url}/efetch.fcgi", params=fetch_params, timeout=30)
            resp.raise_for_status()

            # Parse XML
            root = ET.fromstring(resp.content)

            markdown_parts: List[str] = []

            # Extract title
            title_elem = root.find(".//article-title")
            if title_elem is not None:
                title = "".join(title_elem.itertext()).strip()
                markdown_parts.append(f"# {title}\n")

            # Extract abstract
            abstract_elem = root.find(".//abstract")
            if abstract_elem is not None:
                markdown_parts.append("## Abstract\n")
                abstract_parts = []

                for sec in abstract_elem.findall(".//sec"):
                    sec_title_elem = sec.find("title")
                    sec_title = "".join(sec_title_elem.itertext()).strip() if sec_title_elem is not None else ""
                    sec_text = []
                    for p in sec.findall(".//p"):
                        p_text = "".join(p.itertext()).strip()
                        if p_text:
                            sec_text.append(p_text)
                    if sec_title:
                        abstract_parts.append(f"**{sec_title}**: " + " ".join(sec_text))
                    else:
                        abstract_parts.extend(sec_text)

                # Fallback: get all paragraphs if no sections
                if not abstract_parts:
                    for p in abstract_elem.findall(".//p"):
                        p_text = "".join(p.itertext()).strip()
                        if p_text:
                            abstract_parts.append(p_text)

                markdown_parts.append("\n\n".join(abstract_parts) + "\n")

            # Extract body sections
            body_elem = root.find(".//body")
            if body_elem is not None:
                for sec in body_elem.findall(".//sec"):
                    title_elem = sec.find("title")
                    sec_title = "".join(title_elem.itertext()).strip() if title_elem is not None else "Untitled Section"
                    markdown_parts.append(f"\n## {sec_title}\n")

                    paragraphs = []
                    for p in sec.findall(".//p"):
                        p_text = "".join(p.itertext()).strip()
                        if p_text:
                            paragraphs.append(p_text)

                    if paragraphs:
                        markdown_parts.append("\n\n".join(paragraphs) + "\n")

            full_text = "\n".join(markdown_parts)
            LOGGER.info(f"Successfully extracted {len(full_text)} characters from PMC {pmcid}")
            return full_text

        except requests.RequestException as exc:
            LOGGER.warning(f"Failed to fetch paper from PMC {pmcid}: {exc}")
            return None
        except Exception as exc:
            LOGGER.warning(f"Error processing PMC paper {pmcid}: {exc}")
            return None

    @staticmethod
    def _study_to_document(
        study: dict,
        retrieved_at: dt.datetime,
        metadata_overrides: dict[str, object] | None = None,
        fetch_papers: bool = False,
    ) -> models.LiteratureDocument:
        protocol = study.get("protocolSection", {})
        id_module = protocol.get("identificationModule", {})
        desc_module = protocol.get("descriptionModule", {})
        identifier = id_module.get("nctId")
        title = id_module.get("officialTitle") or id_module.get("briefTitle") or identifier
        summary = desc_module.get("briefSummary")
        detail = desc_module.get("detailedDescription")

        # Extract publication IDs
        publication_ids = LangGraphLiteratureFetcher._get_publication_ids(study)

        # Fetch papers if requested (PMIDs only - converted to PMCIDs)
        papers_text: List[str] = []
        if fetch_papers:
            for id_type, id_value in publication_ids:
                if id_type == "pmid":
                    # Convert PMID to PMCID
                    pmcid = LangGraphLiteratureFetcher._get_pmcid_from_pmid(id_value)
                    if pmcid:
                        # Fetch full text from PMC
                        paper_text = LangGraphLiteratureFetcher._fetch_paper_from_pmc(pmcid)
                        if paper_text:
                            papers_text.append(f"---\n\n# Paper (PMID: {id_value}, PMCID: {pmcid})\n\n{paper_text}")
                elif id_type == "doi":
                    LOGGER.debug(f"DOI {id_value} found, but only PMID-based fetching is currently supported")

        # 전체 study 데이터를 metadata에 저장 (ClinicalTrials.gov API 응답 전체)
        metadata = {
            "nct_id": identifier,
            "retrieved_at": retrieved_at.isoformat(),
            "full_study_data": study,  # 전체 study 객체 저장
            "publication_ids": publication_ids,  # Store extracted publication IDs
            # 자주 사용되는 필드들을 최상위에 배치 (빠른 접근용)
            "phase": protocol.get("designModule", {}).get("phases"),
            "conditions": protocol.get("conditionsModule", {}).get("conditions"),
            "status": protocol.get("statusModule", {}).get("overallStatus"),
            "arms_interventions": protocol.get("armsInterventionsModule", {}),
            "eligibility": protocol.get("eligibilityModule", {}),
            "outcomes": protocol.get("outcomesModule", {}),
            "sponsors": protocol.get("sponsorCollaboratorsModule", {}),
            "contacts_locations": protocol.get("contactsLocationsModule", {}),
            "design": protocol.get("designModule", {}),
        }
        if metadata_overrides:
            metadata.update(metadata_overrides)

        # Combine trial data with papers
        full_text_parts = [summary, detail]
        if papers_text:
            full_text_parts.append("\n\n---\n# Related Publications\n\n" + "\n\n---\n\n".join(papers_text))

        return models.LiteratureDocument(
            source="clinicaltrials",
            identifier=identifier or title or "unknown-study",
            title=title or "Clinical trial record",
            abstract=summary,
            full_text="\n\n".join(filter(None, full_text_parts)),
            fetched_at=retrieved_at,
            url=f"https://clinicaltrials.gov/study/{identifier}" if identifier else None,
            metadata=metadata,
        )


__all__ = ["LangGraphLiteratureFetcher"]
