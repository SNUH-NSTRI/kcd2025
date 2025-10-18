"""
ClinicalTrials.gov API Client for fetching clinical trial data.

API Documentation: https://clinicaltrials.gov/data-api/api
"""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime


class ClinicalTrialsClient:
    """Client for interacting with ClinicalTrials.gov API v2."""

    BASE_URL = "https://clinicaltrials.gov/api/v2"

    def __init__(self, timeout: int = 30):
        """Initialize the client with optional timeout."""
        self.timeout = timeout

    async def search_studies(
        self,
        query: Optional[str] = None,
        condition: Optional[str] = None,
        intervention: Optional[str] = None,
        sponsor: Optional[str] = None,
        status: Optional[List[str]] = None,
        phase: Optional[List[str]] = None,
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for clinical trials using various filters.

        Args:
            query: General search query across all fields
            condition: Disease or condition name
            intervention: Treatment or intervention name
            sponsor: Sponsor organization name
            status: List of recruitment statuses (e.g., ["RECRUITING", "COMPLETED"])
            phase: List of trial phases (e.g., ["PHASE3", "PHASE4"])
            page_size: Number of results per page (max 100)
            page_token: Token for pagination

        Returns:
            Dictionary containing studies and pagination info
        """
        params = {
            "format": "json",
            "pageSize": min(page_size, 100),
        }

        # Build query expression
        query_parts = []
        if query:
            query_parts.append(query)
        if condition:
            query_parts.append(f"AREA[Condition]{condition}")
        if intervention:
            query_parts.append(f"AREA[Intervention]{intervention}")
        if sponsor:
            query_parts.append(f"AREA[Sponsor]{sponsor}")

        if query_parts:
            params["query.term"] = " AND ".join(query_parts)

        # Add filters
        filter_parts = []
        if status:
            status_filter = ",".join(status)
            filter_parts.append(f"overallStatus:{status_filter}")
        if phase:
            phase_filter = ",".join(phase)
            filter_parts.append(f"phase:{phase_filter}")

        if filter_parts:
            params["filter.advanced"] = " AND ".join(filter_parts)

        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.BASE_URL}/studies", params=params)
            response.raise_for_status()
            return response.json()

    async def get_study_details(self, nct_id: str) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific study by NCT ID.

        Args:
            nct_id: NCT identifier (e.g., "NCT03389555")

        Returns:
            Dictionary containing full study details
        """
        params = {"format": "json"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.BASE_URL}/studies/{nct_id}", params=params
            )
            response.raise_for_status()
            return response.json()

    def parse_study_summary(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a study record into simplified summary format.

        Args:
            study: Raw study data from API

        Returns:
            Simplified study summary dictionary
        """
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        eligibility = protocol.get("eligibilityModule", {})
        arms = protocol.get("armsInterventionsModule", {})
        conditions = protocol.get("conditionsModule", {})
        interventions = arms.get("interventions", [])

        return {
            "nctId": identification.get("nctId"),
            "briefTitle": identification.get("briefTitle"),
            "officialTitle": identification.get("officialTitle"),
            "overallStatus": status.get("overallStatus"),
            "phase": design.get("phases", ["N/A"])[0] if design.get("phases") else "N/A",
            "studyType": design.get("studyType"),
            "enrollment": status.get("enrollmentInfo", {}).get("count"),
            "startDate": status.get("startDateStruct", {}).get("date"),
            "completionDate": status.get("completionDateStruct", {}).get("date"),
            "conditions": conditions.get("conditions", []),
            "interventions": [
                {
                    "type": iv.get("type"),
                    "name": iv.get("name"),
                    "description": iv.get("description"),
                }
                for iv in interventions
            ],
            "sponsor": {
                "lead": protocol.get("sponsorCollaboratorsModule", {})
                .get("leadSponsor", {})
                .get("name"),
                "collaborators": [
                    c.get("name")
                    for c in protocol.get("sponsorCollaboratorsModule", {}).get(
                        "collaborators", []
                    )
                ],
            },
            "summary": protocol.get("descriptionModule", {}).get("briefSummary"),
            "eligibilityCriteria": eligibility.get("eligibilityCriteria"),
            "sex": eligibility.get("sex"),
            "minimumAge": eligibility.get("minimumAge"),
            "maximumAge": eligibility.get("maximumAge"),
        }

    def parse_study_detail(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a study record into detailed format with all information.

        Args:
            study: Raw study data from API

        Returns:
            Detailed study dictionary
        """
        summary = self.parse_study_summary(study)

        protocol = study.get("protocolSection", {})
        design = protocol.get("designModule", {})
        arms_module = protocol.get("armsInterventionsModule", {})
        outcomes = protocol.get("outcomesModule", {})
        eligibility = protocol.get("eligibilityModule", {})
        description = protocol.get("descriptionModule", {})
        locations_module = protocol.get("contactsLocationsModule", {})

        summary.update(
            {
                "description": description.get("detailedDescription"),
                "arms": [
                    {
                        "label": arm.get("label"),
                        "type": arm.get("type"),
                        "description": arm.get("description"),
                        "interventionNames": arm.get("interventionNames", []),
                    }
                    for arm in arms_module.get("armGroups", [])
                ],
                "primaryOutcomes": [
                    {
                        "measure": outcome.get("measure"),
                        "description": outcome.get("description"),
                        "timeFrame": outcome.get("timeFrame"),
                    }
                    for outcome in outcomes.get("primaryOutcomes", [])
                ],
                "secondaryOutcomes": [
                    {
                        "measure": outcome.get("measure"),
                        "description": outcome.get("description"),
                        "timeFrame": outcome.get("timeFrame"),
                    }
                    for outcome in outcomes.get("secondaryOutcomes", [])
                ],
                "studyDesign": {
                    "allocation": design.get("designInfo", {}).get("allocation"),
                    "interventionModel": design.get("designInfo", {}).get(
                        "interventionModel"
                    ),
                    "masking": design.get("designInfo", {})
                    .get("maskingInfo", {})
                    .get("masking"),
                    "primaryPurpose": design.get("designInfo", {}).get(
                        "primaryPurpose"
                    ),
                },
                "locations": [
                    {
                        "facility": loc.get("facility"),
                        "city": loc.get("city"),
                        "state": loc.get("state"),
                        "country": loc.get("country"),
                        "status": loc.get("status"),
                    }
                    for loc in locations_module.get("locations", [])
                ],
            }
        )

        return summary
