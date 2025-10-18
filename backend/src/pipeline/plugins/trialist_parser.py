"""
Trialist Parser Implementation

Advanced clinical trial parser with 3-stage processing:
1. Enhanced NER with domain classification
2. Component standardization with UMLS/OHDSI
3. CDM mapping to OMOP vocabularies
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, TypedDict, Tuple
from string import Template

from .. import models
from ..context import PipelineContext
from ..trialist_models import (
    EnhancedNamedEntity,
    EnhancedTrialCriterion,
    EnhancedTrialFeature,
    EnhancedTrialSchema,
    TemporalRelation,
    ProcessingStageInfo,
    TrialistParams,
    TrialistNERParams,
    TrialistStandardizationParams,
    TrialistCDMParams,
    DOMAIN_TAXONOMY,
    DEFAULT_VOCABULARIES,
    TEMPORAL_PATTERNS
)
from ..value_extractor import extract_value_components
from ..temporal_normalizer import extract_temporal_components
from ..intelligent_mapper import IntelligentMimicMapper

# Enhanced prompt template for domain-aware NER with criterion-level structure
TRIALIST_NER_PROMPT = Template("""\
Annotate clinical concepts from the given text using the following rules:

1. Annotate concepts with the domains 'Demographic', 'Condition', 'Device', 'Procedure', 'Drug', 'Measurement', 'Observation', 'Visit', 'Value', 'Negation_cue', 'Temporal', and 'Quantity'. If you cannot annotate with the given domains, you can name a new one (e.g., Drug_cycle, Visit, Provider, etc.).

2. Split the concepts as detailed as possible. Each concept can be annotated only once with a single domain.

3. Normalize clinical abbreviations and acronyms and attach them behind the original abbreviation with parentheses.

4. **IMPORTANT OUTPUT STRUCTURE**: Return your response as a single JSON object with three top-level keys: inclusion, exclusion, and outcome. Each key should contain an array of criterion objects (NOT flat concept arrays).

   Each criterion object must have:
   - "id": unique identifier (e.g., "inc_1", "exc_1", "outcome_1")
   - "original": the original full text of this specific criterion
   - "entities": array of annotated concepts with {"concept": "text", "domain": "category"}

5. Each numbered item in the eligibility criteria should become a separate criterion object. Do NOT mix multiple criteria into one.

**CORRECT OUTPUT EXAMPLE:**

For eligibility criteria like:
- Inclusion Criteria:
  1. Adult patient (age ≥ 18 years)
  2. Suspected or confirmed infection

- Exclusion Criteria:
  1. Known kidney stones within the past 1 year
  2. End stage renal disease (ESRD) requiring dialysis

The output should be:

```json
{
  "inclusion": [
    {
      "id": "inc_1",
      "original": "Adult patient (age ≥ 18 years)",
      "entities": [
        { "concept": "Adult", "domain": "Demographic" },
        { "concept": "age", "domain": "Demographic" },
        { "concept": "≥ 18 years", "domain": "Value" }
      ]
    },
    {
      "id": "inc_2",
      "original": "Suspected or confirmed infection",
      "entities": [
        { "concept": "Suspected infection", "domain": "Condition" },
        { "concept": "confirmed infection", "domain": "Condition" }
      ]
    }
  ],
  "exclusion": [
    {
      "id": "exc_1",
      "original": "Known kidney stones within the past 1 year",
      "entities": [
        { "concept": "Known kidney stones", "domain": "Condition" },
        { "concept": "within the past 1 year", "domain": "Temporal" }
      ]
    },
    {
      "id": "exc_2",
      "original": "End stage renal disease (ESRD) requiring dialysis",
      "entities": [
        { "concept": "End stage renal disease (ESRD)", "domain": "Condition" },
        { "concept": "requiring dialysis", "domain": "Procedure" }
      ]
    }
  ],
  "outcome": [
    {
      "id": "outcome_1",
      "original": "Sequential Organ Failure Assessment (SOFA) Score at Baseline and 72 Hours",
      "entities": [
        { "concept": "Sequential Organ Failure Assessment (SOFA) Score", "domain": "Measurement" },
        { "concept": "Baseline", "domain": "Temporal" },
        { "concept": "72 Hours", "domain": "Temporal" }
      ]
    }
  ]
}
```

**Following is information for each domain:**

1. **Condition** is events of a Person suggesting the presence of a disease or medical condition stated as a diagnosis, a sign, or a symptom, which is either observed by a Provider or reported by the patient.

2. **Drugs** include prescription and over-the-counter medicines, vaccines, and large-molecule biologic therapies. Radiological devices ingested or applied locally do not count as Drugs.

3. **Procedure** is records of activities or processes ordered by, or carried out by, a healthcare provider on the patient with a diagnostic or therapeutic purpose. Lab tests are not a procedure; if something is observed with an expected resulting amount and unit then it should be a measurement.

4. **Devices** include implantable objects (e.g. pacemakers, stents, artificial joints), medical equipment and supplies (e.g. bandages, crutches, syringes), other instruments used in medical procedures (e.g. sutures, defibrillators) and material used in clinical care (e.g. adhesives, body material, dental material, surgical material).

5. **Measurement** contains both orders and results of such Measurements as laboratory tests, vital signs, quantitative findings from pathology reports, etc.

6. **Observation** captures clinical facts about a Person obtained in the context of examination, questioning or a procedure. Any data that cannot be represented by any other domains, such as social and lifestyle facts, medical history, family history, etc. are recorded here. Observations differ from Measurements in that they do not require a standardized test or some other activity to generate a clinical fact. Typical observations are medical history, family history, the stated need for certain treatment, social circumstances, lifestyle choices, healthcare utilization patterns, etc.

7. **Demographic** can include factors of a patient such as age, gender, race, ethnicity, education level, income, occupation, geographic location, marital status, and family size. Age term can be demographic but the specific age criteria should be annotated as value. Demographic term only includes the above factors; the word 'patient' or 'patients' should not be annotated.

8. Some demographic factors are not explicitly included in the text, such as 'patients who are at least 18 years old' or 'less than 18 years old'. In such cases, the factor 'age' should be additionally annotated.

9. **Negation_cue** includes all information that negates clinical concepts.

10. **Value** is the numeric value or string test result of a clinical concept. Typical values can be the results of Measurements such as Lab tests, vital signs, and quantitative findings from pathology reports. It can also be the dosage of drugs, the frequency of drugs, positive/negative of a Gene test or lab test, the duration of drugs, or numeric criteria of age, weight, height, etc. The relational operator such as "<", ">", ">=", "<=" should be recognized as part of the VALUE information.

---

**ENHANCED ANNOTATION GUIDELINES (Phase 1-3):**

**11. VALUE EXTRACTION - Extract Operators, Numbers, and Units:**

When annotating Value entities, ALWAYS include:
- The complete relational operator (>, <, ≥, ≤, =, between)
- The numeric value or range
- The unit of measurement (original format)

Examples:
- "HbA1c > 7.0%" → annotate as "HbA1c > 7.0%" (domain: Measurement with Value)
- "age ≥ 18 years" → annotate "age" (domain: Demographic) and "≥ 18 years" (domain: Value)
- "eGFR between 30 and 60 mL/min" → annotate with operator "between" and range [30, 60]
- "systolic blood pressure < 140 mmHg" → annotate complete value with operator and unit

**12. TEMPORAL NORMALIZATION - Recognize Time Durations and Reference Points:**

When annotating Temporal entities, identify:
- Duration patterns: "3 months", "24 hours", "1 year", "30 days"
- Reference points: "enrollment", "admission", "baseline", "discharge", "surgery", "diagnosis"
- Temporal relationships: "within", "before", "after", "during"

Examples:
- "within the past 3 months" → annotate as "within the past 3 months" (domain: Temporal)
  * Duration: "3 months" → will be converted to ISO 8601: P3M
- "at least 24 hours before surgery" → annotate "24 hours" (Temporal) and "before surgery" (Temporal)
  * Duration: "24 hours" → ISO: PT24H, Reference: "surgery"
- "No myocardial infarction within 1 year before enrollment" → temporal with duration P1Y, reference "enrollment"

**13. MULTI-CONCEPT SPLITTING - Separate Compound Concepts:**

When criteria contain multiple concepts connected by logical operators, annotate each separately:

Examples:
- "diabetes mellitus or hypertension" →
  * { "concept": "diabetes mellitus", "domain": "Condition" }
  * { "concept": "hypertension", "domain": "Condition" }
  * Mark logical operator: OR

- "age ≥ 18 years and ≤ 65 years" →
  * { "concept": "age", "domain": "Demographic" }
  * { "concept": "≥ 18 years", "domain": "Value" }
  * { "concept": "≤ 65 years", "domain": "Value" }
  * Mark logical operator: AND

- "fever, cough, or shortness of breath" →
  * { "concept": "fever", "domain": "Condition" }
  * { "concept": "cough", "domain": "Condition" }
  * { "concept": "shortness of breath", "domain": "Condition" }
  * Mark logical operator: OR

**14. CONCEPT INFERENCE - Infer Omitted Concepts:**

Some criteria omit explicit concepts that should be inferred:

Examples:
- "< 18 years" (missing concept: age)
  * { "concept": "age", "domain": "Demographic" } [INFERRED]
  * { "concept": "< 18 years", "domain": "Value" }

- "pregnant women" (implies gender)
  * { "concept": "pregnant", "domain": "Condition" }
  * { "concept": "female", "domain": "Demographic" } [INFERRED from pregnant]

- "prostate cancer" (implies gender)
  * { "concept": "prostate cancer", "domain": "Condition" }
  * { "concept": "male", "domain": "Demographic" } [INFERRED from prostate]

- "< 140 mmHg" (measurement context missing)
  * { "concept": "blood pressure", "domain": "Measurement" } [INFERRED from mmHg unit]
  * { "concept": "< 140 mmHg", "domain": "Value" }

**15. COMPLETE EXAMPLE WITH ALL ENHANCEMENTS:**

Input criterion: "Adult patients (age ≥ 18 and ≤ 65 years) with HbA1c > 7.0% and no history of myocardial infarction within 3 months before enrollment"

Annotated output:
```json
{
  "id": "inc_1",
  "original": "Adult patients (age ≥ 18 and ≤ 65 years) with HbA1c > 7.0% and no history of myocardial infarction within 3 months before enrollment",
  "entities": [
    { "concept": "Adult", "domain": "Demographic" },
    { "concept": "age", "domain": "Demographic" },
    { "concept": "≥ 18 years", "domain": "Value" },
    { "concept": "≤ 65 years", "domain": "Value" },
    { "concept": "HbA1c > 7.0%", "domain": "Measurement" },
    { "concept": "no", "domain": "Negation_cue" },
    { "concept": "history of myocardial infarction", "domain": "Condition" },
    { "concept": "within 3 months before enrollment", "domain": "Temporal" }
  ]
}
```

**Key enhancements in this example:**
- Value extraction: "≥ 18 years", "≤ 65 years", "> 7.0%" (with operators and units)
- Multi-concept splitting: Two separate age values with AND operator
- Temporal normalization: "3 months" → P3M, reference point: "enrollment"
- Negation recognition: "no" negates the myocardial infarction history

---

[Clinical Text]
$text_content

[Annotation]
Provide the JSON object only with no extra commentary. Apply ALL enhanced annotation guidelines (value extraction, temporal normalization, multi-concept splitting, and concept inference).
""")


class TrialistParseState(TypedDict, total=False):
    """State for Trialist parsing workflow."""
    documents: List[models.LiteratureDocument]
    document_context: str
    inclusion_criteria_items: List[str]
    exclusion_criteria_items: List[str]
    
    # Stage 1: NER
    ner_results: List[Dict[str, Any]]
    ner_entities: List[EnhancedNamedEntity]
    
    # Stage 2: Standardization
    standardized_entities: List[EnhancedNamedEntity]
    temporal_relations: List[TemporalRelation]
    
    # Stage 3: CDM Mapping
    cdm_entities: List[EnhancedNamedEntity]
    
    # Final results
    enhanced_schema: Dict[str, Any]
    processing_stages: List[ProcessingStageInfo]


def _build_llm_chain(model_name: Optional[str] = None, temperature: float = 0.0):
    """Build LLM chain for processing using OpenRouter."""
    try:
        from langchain_openai import ChatOpenAI
        from rwe_api.config import settings
    except Exception as exc:
        raise RuntimeError(
            "langchain-openai package is required. Install via `pip install langchain-openai`."
        ) from exc

    if model_name is None:
        model_name = "openai/gpt-4o-mini"  # OpenRouter model format

    # Use OpenRouter API with settings
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not set. Please set it in backend/.env file."
        )

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def _build_openai_client_for_enrichment():
    """Build OpenAI-compatible client for enrichment tasks using OpenRouter.

    This client is used for Stage 4 enrichment (ICD mapping, MIMIC mapping).
    Uses OpenRouter API with OpenAI client library for compatibility.
    """
    try:
        from openai import OpenAI
        from rwe_api.config import settings
    except Exception as exc:
        raise RuntimeError(
            "openai package is required. Install via `pip install openai`."
        ) from exc

    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not set. Please set it in backend/.env file."
        )

    # Use OpenRouter with OpenAI client library
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )


class TrialistParser:
    """
    Trialist Parser implementing 3-stage clinical trial processing.
    """

    def __init__(
        self,
        llm: Any | None = None,
        model_name: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        self.llm = llm or _build_llm_chain(model_name=model_name, temperature=temperature)
        self.enrichment_client = _build_openai_client_for_enrichment()
        self.graph = self._build_graph()
        self.current_context = None  # Store context for stage output saving

    def _build_graph(self):
        """Build LangGraph workflow."""
        try:
            from langgraph.graph import END, START, StateGraph
        except Exception as exc:
            raise RuntimeError(
                "LangGraph is required. Install langgraph package."
            ) from exc

        workflow: StateGraph[TrialistParseState] = StateGraph(TrialistParseState)
        
        # Add nodes for each stage
        workflow.add_node("prepare_context", self._prepare_context)
        workflow.add_node("stage1_ner", self._stage1_ner)
        workflow.add_node("stage2_standardization", self._stage2_standardization)
        workflow.add_node("stage3_cdm_mapping", self._stage3_cdm_mapping)
        workflow.add_node("assemble_results", self._assemble_results)
        workflow.add_node("stage4_enrich_with_mappings", self._stage4_enrich_with_mappings)

        # Add edges
        workflow.add_edge(START, "prepare_context")
        workflow.add_edge("prepare_context", "stage1_ner")
        workflow.add_edge("stage1_ner", "stage2_standardization")
        workflow.add_edge("stage2_standardization", "stage3_cdm_mapping")
        workflow.add_edge("stage3_cdm_mapping", "assemble_results")
        workflow.add_edge("assemble_results", "stage4_enrich_with_mappings")
        workflow.add_edge("stage4_enrich_with_mappings", END)
        
        return workflow.compile()

    def _save_stage_output(self, state: TrialistParseState, stage_name: str, output_data: Dict[str, Any]) -> None:
        """Save stage output to disk.

        Args:
            state: Current pipeline state (to get project context)
            stage_name: Name of the stage (e.g., "stage1_ner")
            output_data: Data to save
        """
        try:
            from pathlib import Path

            # Use stored context if available
            if self.current_context:
                workspace_root = self.current_context.workspace
                project_id = self.current_context.project_id
            else:
                # Fallback: try to infer from documents
                documents = state.get("documents", [])
                if not documents:
                    print(f"⚠️  Warning: No context or documents, cannot save {stage_name} output")
                    return

                workspace_root = Path("src/workspace")
                project_id = "nct03389555"  # Default

                if documents and hasattr(documents[0], 'identifier'):
                    doc_id = documents[0].identifier
                    if doc_id and doc_id.startswith("NCT"):
                        project_id = doc_id.lower()

            output_dir = workspace_root / project_id / "trialist_output"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"{stage_name}_output.json"

            with output_file.open("w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"💾 {stage_name} output saved to: {output_file}")

        except Exception as e:
            print(f"⚠️  Warning: Failed to save {stage_name} output: {e}")

    def _prepare_context(self, state: TrialistParseState) -> TrialistParseState:
        """Prepare document context for processing.

        Priority: inclusion, exclusion, outcomes (REQUIRED)
        Optional: title, abstract, interventions, full_text
        """
        documents = state.get("documents", [])
        sections: List[str] = []
        inclusion_items: List[str] = []
        exclusion_items: List[str] = []

        # Configuration: Set to True to include optional sections
        include_title = False
        include_abstract = False
        include_interventions = False
        include_full_text = False

        for doc in documents:
            # Initialize all section variables at the start
            eligibility_text = ""
            outcomes_text = ""
            treatment_text = ""

            if doc.metadata:
                # Extract eligibility criteria
                eligibility = doc.metadata.get("eligibility", {})
                if isinstance(eligibility, dict):
                    criteria = eligibility.get("eligibilityCriteria", "")
                    if criteria:
                        eligibility_text = f"\n\n## Eligibility Criteria\n\n{criteria}"
                        inc_items, exc_items = self._parse_eligibility_criteria(criteria)
                        inclusion_items.extend(inc_items)
                        exclusion_items.extend(exc_items)

                # Extract from full study data
                full_data = doc.metadata.get("full_study_data", {})
                if isinstance(full_data, dict):
                    protocol = full_data.get("protocolSection", {})
                    if isinstance(protocol, dict):
                        # Enhanced eligibility extraction (if not already found)
                        if not eligibility_text:
                            elig_module = protocol.get("eligibilityModule", {})
                            if isinstance(elig_module, dict):
                                criteria = elig_module.get("eligibilityCriteria", "")
                                if criteria:
                                    eligibility_text = f"\n\n## Eligibility Criteria\n\n{criteria}"
                                    inc_items, exc_items = self._parse_eligibility_criteria(criteria)
                                    inclusion_items.extend(inc_items)
                                    exclusion_items.extend(exc_items)

                        # PRIORITY 2: Extract outcomes (FILTER: mortality-related only)
                        # Return ONLY the FIRST mortality outcome found
                        # Priority: Primary outcomes first, then Secondary outcomes
                        outcomes_module = protocol.get("outcomesModule", {})
                        if isinstance(outcomes_module, dict) and not outcomes_text:
                            # Process primary outcomes first
                            primary_outcomes = outcomes_module.get("primaryOutcomes", [])
                            if primary_outcomes:
                                for outcome in primary_outcomes:
                                    if isinstance(outcome, dict):
                                        measure = outcome.get("measure", "")
                                        description = outcome.get("description", "")
                                        timeframe = outcome.get("timeFrame", "")

                                        # Filter: Only include mortality-related outcomes
                                        if self._is_mortality_related(measure, description):
                                            # Found first mortality outcome - return immediately
                                            outcome_line = f"- **{measure}** (Time Frame: {timeframe})" if timeframe else f"- **{measure}**"
                                            outcomes_text = "\n\n## Primary Outcomes\n\n" + outcome_line
                                            break  # Stop after first match

                            # Only check secondary outcomes if no mortality outcomes in primary
                            if not outcomes_text:
                                secondary_outcomes = outcomes_module.get("secondaryOutcomes", [])
                                if secondary_outcomes:
                                    for outcome in secondary_outcomes:
                                        if isinstance(outcome, dict):
                                            measure = outcome.get("measure", "")
                                            description = outcome.get("description", "")
                                            timeframe = outcome.get("timeFrame", "")

                                            # Filter: Only include mortality-related outcomes
                                            if self._is_mortality_related(measure, description):
                                                # Found first mortality outcome - return immediately
                                                outcome_line = f"- **{measure}** (Time Frame: {timeframe})" if timeframe else f"- **{measure}**"
                                                outcomes_text = "\n\n## Secondary Outcomes\n\n" + outcome_line
                                                break  # Stop after first match

                        # OPTIONAL: Treatment/Interventions
                        if include_interventions:
                            arms_module = protocol.get("armsInterventionsModule", {})
                            if isinstance(arms_module, dict):
                                interventions = arms_module.get("interventions", [])
                                if interventions:
                                    treatment_parts = []
                                    for intervention in interventions:
                                        if isinstance(intervention, dict):
                                            name = intervention.get("name", "")
                                            itype = intervention.get("type", "")
                                            desc = intervention.get("description", "")
                                            treatment_parts.append(
                                                f"- **{name}** ({itype}): {desc}" if desc else f"- **{name}** ({itype})"
                                            )
                                    if treatment_parts:
                                        treatment_text = "\n\n## Treatment/Interventions\n\n" + "\n".join(treatment_parts)

            # Build document text with priority sections
            doc_parts = []

            # Optional: Title
            if include_title and doc.title:
                doc_parts.append(f"## Trial: {doc.title.strip()}")

            # Optional: Abstract
            if include_abstract and doc.abstract:
                doc_parts.append(doc.abstract.strip())

            # REQUIRED: Eligibility (inclusion + exclusion)
            if eligibility_text:
                doc_parts.append(eligibility_text)

            # Optional: Interventions
            if include_interventions and treatment_text:
                doc_parts.append(treatment_text)

            # REQUIRED: Outcomes
            if outcomes_text:
                doc_parts.append(outcomes_text)

            # Optional: Full text
            if include_full_text and doc.full_text:
                doc_parts.append(doc.full_text.strip())

            doc_text = "\n\n".join(filter(None, doc_parts))
            sections.append(doc_text)

        context = "\n\n---\n\n".join(sections)[:20000]  # Limit context size
        new_state = dict(state)
        new_state['document_context'] = context
        new_state['inclusion_criteria_items'] = inclusion_items
        new_state['exclusion_criteria_items'] = exclusion_items
        return TrialistParseState(**new_state)
    
    def _is_mortality_related(self, measure: str, description: str = "") -> bool:
        """Check if an outcome measure is mortality-related.

        Args:
            measure: The outcome measure text
            description: Optional description text

        Returns:
            True if the measure is related to mortality/death
        """
        # Primary mortality keywords (strong indicators)
        primary_keywords = [
            "mortality",
            "mortality rate",
            "death rate",
            "survival",
            "survival rate",
            "fatal",
            "deceased",
            "all-cause death",
            "all cause death",
            "cardiovascular death",
            "cardiac death",
            "sudden death",
            "overall survival"
        ]

        # Exclusion patterns (not mortality outcomes)
        exclusion_patterns = [
            "sofa",  # SOFA score is organ dysfunction, not mortality
            "sequential organ failure",
            "apache",  # APACHE score
            "saps",  # Simplified Acute Physiology Score
            "quality of life",
            "qol",
            "disability",
            "functional status",
            "vasopressor",  # Vasopressor-related outcomes unless explicitly about death
            "ventilator-free"  # Unless explicitly about mortality
        ]

        measure_lower = measure.lower()
        description_lower = description.lower()

        # Check for exclusion patterns first
        for pattern in exclusion_patterns:
            if pattern in measure_lower:
                # If it's in the measure title, it's likely not a mortality outcome
                # Exception: if measure explicitly mentions "mortality" or "death"
                if "mortality" not in measure_lower and "death" not in measure_lower and "survival" not in measure_lower:
                    return False

        # Check measure title for primary keywords (high confidence)
        for keyword in primary_keywords:
            if keyword in measure_lower:
                return True

        # Check for explicit "death" keyword (very strong indicator)
        if "death" in measure_lower:
            return True

        # Check description for primary keywords if measure doesn't contain them
        # This catches cases like "Primary endpoint" with "mortality" in description
        for keyword in ["mortality", "mortality rate", "death rate", "survival", "survival rate"]:
            if keyword in description_lower:
                return True

        # Secondary check: "die/died/dying" but only in measure title
        # Avoid false positives from descriptions that mention death as a side note
        death_variants = ["die", "died", "dying"]
        for variant in death_variants:
            # Must be in measure title for high confidence
            if variant in measure_lower:
                return True

        return False

    def _parse_eligibility_criteria(self, criteria_text: str) -> tuple[List[str], List[str]]:
        """Parse eligibility criteria text into inclusion and exclusion items."""
        inclusion = []
        exclusion = []

        # Split by sections
        lines = criteria_text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section headers
            if 'inclusion criteria' in line.lower():
                current_section = 'inclusion'
                continue
            elif 'exclusion criteria' in line.lower():
                current_section = 'exclusion'
                continue

            # Skip empty lines and section headers
            if not current_section or line.startswith('#'):
                continue

            # Extract numbered items
            # Match patterns like "1.", "1)", "-", "•", etc.
            item_match = re.match(r'^(?:\d+[\.\)]\s*|-\s*|•\s*)(.*)', line)
            if item_match:
                item_text = item_match.group(1).strip()
                if item_text:
                    if current_section == 'inclusion':
                        inclusion.append(item_text)
                    elif current_section == 'exclusion':
                        exclusion.append(item_text)

        return inclusion, exclusion

    def _stage1_ner(self, state: TrialistParseState) -> TrialistParseState:
        """Stage 1: Enhanced NER with domain classification."""
        start_time = time.time()

        document_context = state.get("document_context", "")
        if not document_context:
            raise ValueError("document_context is empty; cannot perform NER.")

        # Debug: Print document context
        print("\n=== DEBUG: Document Context Sent to LLM ===")
        print(f"Length: {len(document_context)} characters")
        print(document_context)  # Print full context
        print("==========================================\n")

        try:
            # Process text through enhanced NER
            prompt = TRIALIST_NER_PROMPT.substitute(text_content=document_context)

            # Debug: Print prompt length
            print(f"\n=== DEBUG: Prompt Stats ===")
            print(f"Prompt length: {len(prompt)} characters")
            print(f"Last 500 chars of prompt:\n{prompt[-500:]}")
            print("==========================\n")

            response = self.llm.invoke(prompt)
            content = getattr(response, "content", response)

            if not isinstance(content, str):
                raise ValueError("LLM response did not return string content.")

            # Debug: Print raw LLM response
            print("\n=== DEBUG: RAW LLM Response ===")
            print(content[:2000])  # First 2000 chars
            print("================================\n")

            # Parse JSON response
            ner_result = self._parse_json_response(content.strip())

            # Debug: Print NER result
            print("\n=== DEBUG: NER Result ===")
            print(f"Keys in result: {list(ner_result.keys())}")
            print(f"Inclusion count: {len(ner_result.get('inclusion', []))}")
            print(f"Exclusion count: {len(ner_result.get('exclusion', []))}")
            print(f"Outcome count: {len(ner_result.get('outcome', []))}")
            if ner_result.get('inclusion'):
                print(f"First inclusion item: {ner_result['inclusion'][0]}")
            print("========================\n")

            # Convert to enhanced entities from new format
            entities = self._convert_to_enhanced_entities_from_sections(ner_result)

            # Record stage info
            stage_info = ProcessingStageInfo(
                stage_name="ner",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=True,
                entities_processed=len(entities)
            )

            processing_stages = list(state.get("processing_stages", []))
            processing_stages.append(stage_info)

            # Save Stage 1 output to disk with criterion-level structure
            self._save_stage_output(state, "stage1_ner", {
                "stage": "Stage 1: NER",
                "timestamp": time.time(),
                "execution_time_ms": stage_info.execution_time_ms,
                "entities_count": len(entities),
                "raw_ner_result": ner_result,  # Original LLM response with criterion structure
                "inclusion": ner_result.get("inclusion", []),  # Criterion-level structure
                "exclusion": ner_result.get("exclusion", []),
                "outcome": ner_result.get("outcome", [])
            })

            # Create new state without processing_stages from **state
            new_state = {k: v for k, v in state.items() if k != 'processing_stages'}
            return TrialistParseState(
                **new_state,
                ner_results=[ner_result],
                ner_entities=entities,
                processing_stages=processing_stages
            )

        except Exception as e:
            stage_info = ProcessingStageInfo(
                stage_name="ner",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
            processing_stages = state.get("processing_stages", [])
            processing_stages.append(stage_info)

            raise ValueError(f"Stage 1 NER failed: {e}") from e

    def _stage2_standardization(self, state: TrialistParseState) -> TrialistParseState:
        """Stage 2: Component standardization using UMLS/OHDSI APIs with offline fallback."""
        start_time = time.time()

        entities = state.get("ner_entities", [])
        document_context = state.get("document_context", "")
        ctx = state.get("ctx")

        try:
            # Import dependencies
            import os
            from ..api_standardizer import APIStandardizer
            from ..clients import UMLSClient, OHDSIClient, CacheManager
            from ..offline_standardizer import OfflineStandardizer

            # Get API credentials from environment
            umls_api_key = os.getenv("UMLS_API_KEY")
            ohdsi_base_url = os.getenv("OHDSI_BASE_URL", "http://api.ohdsi.org/WebAPI")

            # Read standardization mode from config.yaml (via context)
            config_mode = ctx.config.get("trialist", {}).get("standardization", {}).get("mode", "offline") if ctx else "offline"
            use_api_mode = config_mode.lower() == "online"

            print(f"🔧 Standardization mode from config: {config_mode}")

            # Initialize standardizer based on configuration
            if use_api_mode and umls_api_key:
                print("🔧 Initializing API-based standardizer (UMLS + OHDSI)")

                # Initialize API clients
                umls_client = UMLSClient(api_key=umls_api_key)
                ohdsi_client = OHDSIClient(base_url=ohdsi_base_url)
                cache = CacheManager(backend="memory", default_ttl=604800)  # 7 days

                # Initialize API standardizer with fallback
                standardizer = APIStandardizer(
                    umls_client=umls_client,
                    ohdsi_client=ohdsi_client,
                    cache_manager=cache,
                    fallback_to_offline=True
                )
                print("✅ API standardizer initialized with offline fallback enabled")
            else:
                # Fallback to offline standardizer
                if not umls_api_key:
                    print("⚠️  UMLS_API_KEY not found - using offline standardizer")
                else:
                    print("🔧 STANDARDIZATION_MODE=offline - using offline standardizer")
                standardizer = OfflineStandardizer()

            standardized_entities = []
            temporal_relations = []

            # Standardize each entity (batch processing if API mode)
            if isinstance(standardizer, APIStandardizer):
                print(f"📊 Batch standardizing {len(entities)} entities with API...")
                standardized_entities = standardizer.batch_standardize(entities, show_progress=False)
            else:
                # Sequential processing for offline mode
                for entity in entities:
                    standardized_entity = standardizer.standardize_entity(entity)
                    standardized_entities.append(standardized_entity)

            # Extract temporal relations from document context
            if document_context:
                # Split into sentences for temporal analysis
                sentences = re.split(r'[.!?]+', document_context)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        temporal_relation = standardizer.standardize_temporal_relation(sentence)
                        if temporal_relation:
                            temporal_relations.append(temporal_relation)

            # Record stage info
            stage_info = ProcessingStageInfo(
                stage_name="standardization",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=True,
                concepts_standardized=len(standardized_entities),
                entities_processed=len(entities)
            )

            processing_stages = list(state.get("processing_stages", []))
            processing_stages.append(stage_info)

            # Collect API statistics if using API standardizer
            api_stats = {}
            if isinstance(standardizer, APIStandardizer):
                api_stats = standardizer.get_stats()
                print(f"\n📈 Standardization Statistics:")
                print(f"  - Total entities: {api_stats['total_entities']}")
                print(f"  - UMLS requests: {api_stats['umls_requests']}")
                print(f"  - OHDSI requests: {api_stats['ohdsi_requests']}")
                print(f"  - Cache hits: {api_stats['cache_hits']} ({api_stats['cache_hits']/max(api_stats['total_entities'], 1)*100:.1f}%)")
                print(f"  - Fallback count: {api_stats['fallback_count']} ({api_stats['fallback_count']/max(api_stats['total_entities'], 1)*100:.1f}%)")

            # Save Stage 2 output to disk
            output_data = {
                "stage": "Stage 2: Standardization",
                "timestamp": time.time(),
                "execution_time_ms": stage_info.execution_time_ms,
                "entities_count": len(standardized_entities),
                "concepts_standardized": len(standardized_entities),
                "temporal_relations_count": len(temporal_relations),
                "standardization_mode": "api" if isinstance(standardizer, APIStandardizer) else "offline",
                "entities": [
                    {
                        "text": e.text,
                        "domain": e.domain,
                        "type": e.type,
                        "confidence": e.confidence,
                        "standard_name": e.standard_name,
                        "umls_cui": e.umls_cui,
                        "code_system": e.code_system,
                        "primary_code": e.primary_code,
                        "metadata": e.metadata
                    }
                    for e in standardized_entities
                ],
                "temporal_relations": [
                    {
                        "pattern": t.pattern,
                        "value": t.value,
                        "normalized_duration": t.normalized_duration,
                        "subject_concept": t.subject_concept,
                        "reference_concept": t.reference_concept,
                        "confidence": t.confidence
                    }
                    for t in temporal_relations
                ]
            }

            # Add API statistics if available
            if api_stats:
                output_data["api_stats"] = api_stats

            self._save_stage_output(state, "stage2_standardization", output_data)

            # Create new state without processing_stages from **state
            new_state = {k: v for k, v in state.items() if k != 'processing_stages'}
            return TrialistParseState(
                **new_state,
                standardized_entities=standardized_entities,
                temporal_relations=temporal_relations,
                processing_stages=processing_stages
            )

        except Exception as e:
            stage_info = ProcessingStageInfo(
                stage_name="standardization",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
            processing_stages = state.get("processing_stages", [])
            processing_stages.append(stage_info)

            raise ValueError(f"Stage 2 standardization failed: {e}") from e

    def _stage3_cdm_mapping(self, state: TrialistParseState) -> TrialistParseState:
        """Stage 3: CDM mapping using OHDSI API to get real OMOP codes."""
        start_time = time.time()

        entities = state.get("standardized_entities", [])

        try:
            # Import dependencies
            import os
            from ..cdm_mapper import CDMMapper
            from ..clients import OHDSIClient, CacheManager
            from ..time_event_mapper import TimeEventMapper

            # Get OHDSI configuration from environment
            ohdsi_base_url = os.getenv("OHDSI_BASE_URL", "http://api.ohdsi.org/WebAPI")
            use_cache = os.getenv("CDM_CACHE_ENABLED", "true").lower() == "true"
            standard_only = os.getenv("CDM_STANDARD_ONLY", "true").lower() == "true"

            # Initialize OHDSI client
            print(f"🔧 Initializing OHDSI client: {ohdsi_base_url}")
            ohdsi_client = OHDSIClient(base_url=ohdsi_base_url)

            # Initialize cache if enabled
            cache = None
            if use_cache:
                cache = CacheManager(backend="memory", default_ttl=2592000)  # 30 days
                print("✅ Cache enabled for CDM mapping")

            # Initialize Time Event Ontology mapper
            print("🔧 Initializing Time Event Ontology mapper")
            time_event_mapper = TimeEventMapper()

            # Initialize CDM mapper with TEO support
            mapper = CDMMapper(
                ohdsi_client=ohdsi_client,
                cache_manager=cache,
                fallback_enabled=True,
                standard_only=standard_only,
                time_event_mapper=time_event_mapper
            )

            # Map entities to OMOP concepts (batch processing)
            print(f"📊 Mapping {len(entities)} entities to OMOP CDM...")
            map_results = mapper.batch_map_entities(entities, show_progress=False)

            # Apply results to create enhanced entities
            cdm_entities = mapper.apply_results_to_entities(map_results)

            # Collect statistics
            cdm_stats = mapper.get_stats()
            success_count = sum(1 for r in map_results if r.omop_concept is not None)
            success_rate = success_count / max(len(entities), 1) * 100

            print(f"\n📈 CDM Mapping Statistics:")
            print(f"  - Total entities: {cdm_stats['total_entities']}")
            print(f"  - Successfully mapped: {success_count} ({success_rate:.1f}%)")
            print(f"  - TEO mappings: {cdm_stats.get('teo_mappings', 0)}")
            print(f"  - CUI lookups: {cdm_stats['cui_lookups']}")
            print(f"  - Text searches: {cdm_stats['text_searches']}")
            print(f"  - Cache hits: {cdm_stats['cache_hits']}")
            print(f"  - Domain skips: {cdm_stats.get('domain_skips', 0)}")
            print(f"  - Failures: {cdm_stats['failures']}")

            # Record stage info
            stage_info = ProcessingStageInfo(
                stage_name="cdm_mapping",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=True,
                codes_mapped=success_count,
                entities_processed=len(entities)
            )

            processing_stages = list(state.get("processing_stages", []))
            processing_stages.append(stage_info)

            # Save Stage 3 output to disk
            output_data = {
                "stage": "Stage 3: CDM Mapping",
                "timestamp": time.time(),
                "execution_time_ms": stage_info.execution_time_ms,
                "entities_count": len(cdm_entities),
                "codes_mapped": success_count,
                "success_rate": success_rate,
                "mapping_statistics": cdm_stats,
                "entities": [
                    {
                        "text": e.text,
                        "domain": e.domain,
                        "type": e.type,
                        "confidence": e.confidence,
                        "standard_name": e.standard_name,
                        "umls_cui": e.umls_cui,
                        "code_system": e.code_system,
                        "code_set": list(e.code_set) if e.code_set else None,
                        "primary_code": e.primary_code,
                        "metadata": e.metadata
                    }
                    for e in cdm_entities
                ]
            }

            self._save_stage_output(state, "stage3_cdm_mapping", output_data)

            # Create new state without processing_stages from **state
            new_state = {k: v for k, v in state.items() if k != 'processing_stages'}
            return TrialistParseState(
                **new_state,
                cdm_entities=cdm_entities,
                processing_stages=processing_stages
            )

        except Exception as e:
            stage_info = ProcessingStageInfo(
                stage_name="cdm_mapping",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
            processing_stages = state.get("processing_stages", [])
            processing_stages.append(stage_info)

            raise ValueError(f"Stage 3 CDM mapping failed: {e}") from e

    def _assemble_results(self, state: TrialistParseState) -> TrialistParseState:
        """Assemble final enhanced schema."""
        entities = state.get("cdm_entities", [])
        temporal_relations = state.get("temporal_relations", [])
        processing_stages = state.get("processing_stages", [])
        inclusion_items = state.get("inclusion_criteria_items", [])
        exclusion_items = state.get("exclusion_criteria_items", [])

        # Match entities to criteria items
        inclusion_criteria = self._match_entities_to_criteria(inclusion_items, entities, "inc", processing_stages)
        exclusion_criteria = self._match_entities_to_criteria(exclusion_items, entities, "exc", processing_stages)

        # Extract outcome entities (those marked with section="outcome")
        outcome_entities = [e for e in entities if e.metadata and e.metadata.get("section") == "outcome"]

        # Create simplified schema (only essential fields)
        enhanced_schema = {
            "schema_version": "trialist.v1",
            "disease_code": "enhanced_trial",
            "inclusion": [self._criterion_to_dict(c) for c in inclusion_criteria],
            "exclusion": [self._criterion_to_dict(c) for c in exclusion_criteria],
            "outcomes": [self._entity_to_dict(e) for e in outcome_entities]
        }
        
        new_state = dict(state)
        new_state['enhanced_schema'] = enhanced_schema
        return TrialistParseState(**new_state)

    def _convert_to_enhanced_entities_from_sections(
        self, ner_result: Dict[str, Any]
    ) -> List[EnhancedNamedEntity]:
        """Convert new NER format (criterion-level structure) to enhanced entities.

        Applies Phase 1 enhancements:
        - Value extraction (operator, numeric_value, unit, UCUM)
        - Temporal normalization (ISO 8601 duration, reference points)

        New format:
        {
            "inclusion": [
                {
                    "id": "inc_1",
                    "original": "...",
                    "entities": [{"concept": "...", "domain": "..."}]
                }
            ],
            "exclusion": [...],
            "outcome": [...]
        }
        """
        entities = []

        # Process inclusion criteria
        for criterion in ner_result.get("inclusion", []):
            criterion_id = criterion.get("id", "")
            original_text = criterion.get("original", "")
            for entity_item in criterion.get("entities", []):
                entity = self._create_enriched_entity(
                    entity_item,
                    section="inclusion",
                    criterion_id=criterion_id,
                    criterion_original=original_text
                )
                entities.append(entity)

        # Process exclusion criteria
        for criterion in ner_result.get("exclusion", []):
            criterion_id = criterion.get("id", "")
            original_text = criterion.get("original", "")
            for entity_item in criterion.get("entities", []):
                entity = self._create_enriched_entity(
                    entity_item,
                    section="exclusion",
                    criterion_id=criterion_id,
                    criterion_original=original_text
                )
                entities.append(entity)

        # Process outcome criteria
        for criterion in ner_result.get("outcome", []):
            criterion_id = criterion.get("id", "")
            original_text = criterion.get("original", "")
            for entity_item in criterion.get("entities", []):
                entity = self._create_enriched_entity(
                    entity_item,
                    section="outcome",
                    criterion_id=criterion_id,
                    criterion_original=original_text
                )
                entities.append(entity)

        return entities

    def _create_enriched_entity(
        self,
        entity_item: Dict[str, Any],
        section: str,
        criterion_id: str,
        criterion_original: str
    ) -> EnhancedNamedEntity:
        """Create enriched entity with value extraction and temporal normalization.

        Phase 1.4 Integration: Applies value_extractor and temporal_normalizer
        to enrich entities with structured data.
        """
        text = entity_item.get("concept", "")
        domain = entity_item.get("domain", "Unknown")

        # Determine entity type based on domain
        entity_type = "concept"
        if domain in ["Value", "Quantity"]:
            entity_type = "value"
        elif domain == "Temporal":
            entity_type = "temporal"

        # Phase 1.2: Extract value components
        value_components = extract_value_components(text)

        # Phase 1.3: Extract temporal components
        temporal_components = extract_temporal_components(text)

        # Create enriched entity
        return EnhancedNamedEntity(
            text=text,
            type=entity_type,
            domain=domain,
            confidence=0.9,  # Default confidence
            metadata={
                "section": section,
                "criterion_id": criterion_id,
                "criterion_original": criterion_original
            },
            # Phase 1.2: Value extraction fields
            operator=value_components["operator"],
            numeric_value=value_components["numeric_value"],
            value_range=value_components["value_range"],
            unit=value_components["unit"],
            ucum_unit=value_components["ucum_unit"],
            # Phase 1.3: Temporal normalization fields
            temporal_pattern=temporal_components["temporal_pattern"],
            iso_duration=temporal_components["iso_duration"],
            reference_point=temporal_components["reference_point"]
        )

    def _convert_to_enhanced_entities(self, annotations: List[Dict[str, Any]]) -> List[EnhancedNamedEntity]:
        """Convert LLM annotations to enhanced entities (legacy format)."""
        entities = []
        for ann in annotations:
            entity = EnhancedNamedEntity(
                text=ann.get("text", ""),
                type=ann.get("type", "concept"),
                domain=ann.get("domain", "Unknown"),
                start=ann.get("start"),
                end=ann.get("end"),
                confidence=ann.get("confidence", 0.8),
            )
            entities.append(entity)
        return entities

    def _match_entities_to_criteria(
        self,
        criteria_items: List[str],
        all_entities: List[EnhancedNamedEntity],
        prefix: str,
        stages: List[ProcessingStageInfo]
    ) -> List[EnhancedTrialCriterion]:
        """Match entities to criteria items and create enhanced criteria."""
        criteria = []
        
        for i, item_text in enumerate(criteria_items, 1):
            # Find entities that appear in this criterion text
            matched_entities = []
            for entity in all_entities:
                if entity.text.lower() in item_text.lower():
                    matched_entities.append(entity)
            
            # Determine category based on entities
            category = "clinical"
            if matched_entities:
                # Use the most relevant domain
                domain_counts = {}
                for entity in matched_entities:
                    domain_counts[entity.domain] = domain_counts.get(entity.domain, 0) + 1
                most_common_domain = max(domain_counts, key=domain_counts.get)
                category = most_common_domain.lower()
            
            # Calculate validation score
            validation_score = 0.9
            if matched_entities:
                validation_score = sum(e.confidence for e in matched_entities) / len(matched_entities)
            
            criterion = EnhancedTrialCriterion(
                id=f"{prefix}_{i}",
                description=item_text,
                category=category,
                kind="enhanced",
                value={"original_text": item_text},
                entities=matched_entities,
                processing_stages=stages,
                validation_score=validation_score
            )
            criteria.append(criterion)
        
        return criteria
    
    def _create_enhanced_criteria(
        self, 
        entities: List[EnhancedNamedEntity], 
        prefix: str, 
        stages: List[ProcessingStageInfo]
    ) -> List[EnhancedTrialCriterion]:
        """Create enhanced criteria from entities."""
        criteria = []
        for i, entity in enumerate(entities, 1):
            criterion = EnhancedTrialCriterion(
                id=f"{prefix}_{i}",
                description=f"Enhanced criterion based on {entity.text}",
                category=entity.domain.lower(),
                kind="enhanced",
                value={"domain": entity.domain, "standard_name": entity.standard_name},
                entities=[entity],
                processing_stages=stages,
                validation_score=entity.confidence
            )
            criteria.append(criterion)
        return criteria

    def _create_enhanced_features(
        self, 
        entities: List[EnhancedNamedEntity], 
        stages: List[ProcessingStageInfo]
    ) -> List[EnhancedTrialFeature]:
        """Create enhanced features from entities."""
        features = []
        for entity in entities:
            feature = EnhancedTrialFeature(
                name=entity.text.lower().replace(" ", "_"),
                source="enhanced",
                unit=None,
                time_window=None,
                metadata={"role": "enhanced_feature", "domain": entity.domain},
                entities=[entity],
                processing_stages=stages,
                validation_score=entity.confidence
            )
            features.append(feature)
        return features

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        """Parse JSON response from LLM."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            body_lines: List[str] = []
            fence_closed = False
            for line in lines[1:]:
                if line.strip().startswith("```"):
                    fence_closed = True
                    break
                body_lines.append(line)
            if not fence_closed:
                raise json.JSONDecodeError("Unclosed code fence", raw, 0)
            text = "\n".join(body_lines).strip()
        
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise json.JSONDecodeError("No JSON object found", raw, 0)
            text = text[start : end + 1]
        
        return json.loads(text)

    def _criterion_to_dict(self, criterion: EnhancedTrialCriterion) -> Dict[str, Any]:
        """Convert criterion to dictionary (simplified - only essential fields)."""
        return {
            "id": criterion.id,
            "description": criterion.description,
            "entities": [self._entity_to_dict(e) for e in (criterion.entities or [])]
        }

    def _feature_to_dict(self, feature: EnhancedTrialFeature) -> Dict[str, Any]:
        """Convert feature to dictionary."""
        return {
            "name": feature.name,
            "source": feature.source,
            "unit": feature.unit,
            "time_window": feature.time_window,
            "metadata": feature.metadata,
            "entities": [self._entity_to_dict(e) for e in (feature.entities or [])],
            "validation_score": feature.validation_score
        }

    def _entity_to_dict(self, entity: EnhancedNamedEntity) -> Dict[str, Any]:
        """Convert entity to dictionary with all enrichment fields."""
        return {
            "text": entity.text,
            "type": entity.type,
            "domain": entity.domain,
            "start": entity.start,
            "end": entity.end,
            "confidence": entity.confidence,
            "standard_name": entity.standard_name,
            "umls_cui": entity.umls_cui,
            "code_system": entity.code_system,
            "code_set": entity.code_set,
            "primary_code": entity.primary_code,
            # Value extraction fields (Phase 1.1)
            "operator": entity.operator,
            "numeric_value": entity.numeric_value,
            "value_range": list(entity.value_range) if entity.value_range else None,
            "unit": entity.unit,
            "ucum_unit": entity.ucum_unit,
            # Temporal normalization fields (Phase 1.3)
            "temporal_pattern": entity.temporal_pattern,
            "iso_duration": entity.iso_duration,
            "reference_point": entity.reference_point,
            # Relationship fields (Phase 2.1)
            "logical_operator": entity.logical_operator,
            "related_entity_ids": entity.related_entity_ids,
            # Inference fields (Phase 2.2)
            "is_inferred": entity.is_inferred,
            "inferred_from": entity.inferred_from,
            "metadata": entity.metadata
        }

    def _temporal_to_dict(self, temporal: TemporalRelation) -> Dict[str, Any]:
        """Convert temporal relation to dictionary."""
        return {
            "pattern": temporal.pattern,
            "value": temporal.value,
            "normalized_duration": temporal.normalized_duration,
            "subject_concept": temporal.subject_concept,
            "reference_concept": temporal.reference_concept,
            "confidence": temporal.confidence
        }

    def _stage_info_to_dict(self, stage: ProcessingStageInfo) -> Dict[str, Any]:
        """Convert stage info to dictionary."""
        return {
            "stage_name": stage.stage_name,
            "execution_time_ms": stage.execution_time_ms,
            "success": stage.success,
            "error_message": stage.error_message,
            "entities_processed": stage.entities_processed,
            "concepts_standardized": stage.concepts_standardized,
            "codes_mapped": stage.codes_mapped
        }

    def _stage4_enrich_with_mappings(self, state: TrialistParseState) -> TrialistParseState:
        """
        Stage 4: Enrich criteria with ICD codes and MIMIC-IV mappings.

        Two-step enrichment:
        1. Add ICD-9/10 codes to Condition entities (using LLM)
        2. Add MIMIC-IV mappings using IntelligentMimicMapper
        """
        start_time = time.time()
        print("🚀 Starting Stage 4: ICD + MIMIC Intelligent Mapping")

        enhanced_schema = state.get("enhanced_schema", {})
        if not enhanced_schema:
            print("⚠️  Stage 4 warning: enhanced_schema is empty. Skipping.")
            return state

        try:
            # Initialize IntelligentMimicMapper (once for all criteria)
            from pathlib import Path
            mapping_file = self.workspace_root / "project" / state.get("nct_id", "default") / "mimic_concept_mapping_cache.json"
            if not mapping_file.exists():
                # Fallback to global cache
                mapping_file = Path(__file__).parent.parent / "mimic_concept_mapping_v2.json"

            mapper = IntelligentMimicMapper(
                mapping_file=mapping_file,
                openrouter_api_key=self.enrichment_api_key,
                model="openai/gpt-4o-mini"
            )
            print(f"✓ Initialized IntelligentMimicMapper with cache: {mapping_file.name}")

            # Process both inclusion and exclusion criteria
            for criteria_list in [enhanced_schema.get("inclusion", []), enhanced_schema.get("exclusion", [])]:
                for criterion in criteria_list:
                    entities = criterion.get("entities", [])

                    # Step 1: ICD enrichment for Condition entities (preserved)
                    self._enrich_entities_with_icd(entities)

                    # Step 2: MIMIC mapping using intelligent mapper (new)
                    criterion_text = criterion.get("description", "")
                    primary_domain = self._get_primary_domain(entities)

                    if primary_domain and criterion_text:
                        print(f"🔍 Mapping criterion: '{criterion_text[:60]}...' (domain: {primary_domain})")

                        try:
                            mapping_result = mapper.map_concept(criterion_text, primary_domain)

                            criterion["mimic_mapping"] = {
                                "table": mapping_result.mapping.table,
                                "columns": mapping_result.mapping.columns,
                                "filter_logic": mapping_result.mapping.filter_logic,
                                "confidence": mapping_result.confidence,
                                "reasoning": mapping_result.reasoning,
                                "source": mapping_result.source,
                                "alternatives": [
                                    {"table": alt.table, "columns": alt.columns, "note": alt.note}
                                    for alt in mapping_result.alternatives
                                ]
                            }

                            if mapping_result.confidence < 0.7:
                                print(f"⚠️  Low confidence ({mapping_result.confidence:.2f}) - review recommended")

                        except Exception as e:
                            print(f"⚠️  Mapping failed for criterion: {e}")
                            criterion["mimic_mapping"] = {
                                "table": "chartevents",
                                "columns": ["value"],
                                "filter_logic": "-- Manual mapping required",
                                "confidence": 0.0,
                                "reasoning": f"Error: {str(e)}",
                                "source": "error",
                                "alternatives": []
                            }

            # Record stage info
            stage_info = ProcessingStageInfo(
                stage_name="icd_and_mimic_mapping",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=True,
                entities_processed=len(state.get("cdm_entities", []))
            )
            processing_stages = list(state.get("processing_stages", []))
            processing_stages.append(stage_info)

            # Save Stage 4 output
            self._save_stage_output(state, "stage4_enrichment", {
                "stage": "Stage 4: ICD + Intelligent MIMIC Mapping",
                "timestamp": time.time(),
                "execution_time_ms": stage_info.execution_time_ms,
                "enriched_schema": enhanced_schema,
                "mapper_config": {
                    "cache_file": str(mapping_file),
                    "model": "openai/gpt-4o-mini"
                }
            })

            new_state = {k: v for k, v in state.items() if k not in ['processing_stages', 'enhanced_schema']}
            return TrialistParseState(
                **new_state,
                enhanced_schema=enhanced_schema,
                processing_stages=processing_stages
            )

        except Exception as e:
            print(f"🔥 Stage 4 failed: {e}")
            import traceback
            traceback.print_exc()
            stage_info = ProcessingStageInfo(
                stage_name="icd_and_mimic_mapping",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
            processing_stages = list(state.get("processing_stages", []))
            processing_stages.append(stage_info)
            raise ValueError(f"Stage 4 failed: {e}") from e

    def _enrich_entities_with_icd(self, entities: List[Dict[str, Any]]):
        """Fetch and add ICD-9/10 codes to 'Condition' entities in-place."""
        for entity in entities:
            if entity.get("domain", "").lower() == "condition":
                condition_text = entity.get("text", "")
                if not condition_text:
                    continue

                print(f"🔍 Fetching ICD codes for: '{condition_text}'")
                try:
                    icd10_codes = self._fetch_icd_codes(condition_text, "ICD-10")
                    icd9_codes = self._fetch_icd_codes(condition_text, "ICD-9")

                    if 'metadata' not in entity or entity['metadata'] is None:
                        entity['metadata'] = {}

                    entity['metadata']['icd10'] = icd10_codes
                    entity['metadata']['icd9'] = icd9_codes

                except Exception as e:
                    print(f"⚠️  Failed to fetch ICD codes for '{condition_text}': {e}")
                    if 'metadata' not in entity or entity['metadata'] is None:
                        entity['metadata'] = {}
                    entity['metadata']['icd10'] = []
                    entity['metadata']['icd9'] = []

    def _fetch_icd_codes(self, term: str, code_system: str) -> List[Dict[str, str]]:
        """Helper to call OpenRouter API (via OpenAI client) for ICD code mapping."""
        prompts = {
            "ICD-10": """
                You are a medical coding assistant. Map the given disease name to the corresponding WHO ICD-10 code(s).
                Return JSON ONLY with this exact schema: {"query": "...", "codes": [{"code": "...", "title": "..."}, ...]}
                Rules:
                - Include ALL relevant ICD-10 codes.
                - Use WHO ICD-10 (not ICD-10-CM).
                - If no code exists, return an empty "codes" list.
                - No extra text before or after the JSON.
            """,
            "ICD-9": """
                You are a medical coding assistant. Map the given disease name to the corresponding ICD-9 code(s).
                Return JSON ONLY with this exact schema: {"query": "...", "codes": [{"code": "...", "title": "..."}, ...]}
                Rules:
                - Include ALL relevant ICD-9 codes.
                - Use ICD-9 (not ICD-9-CM).
                - If no code exists, return an empty "codes" list.
                - No extra text before or after the JSON.
            """
        }

        system_prompt = prompts.get(code_system)
        if not system_prompt:
            raise ValueError(f"Invalid code system: {code_system}")

        try:
            response = self.enrichment_client.chat.completions.create(
                model="openai/gpt-4o-mini",
                temperature=0.0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f'Query: "{term}"\nReturn JSON only.'},
                ]
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return data.get("codes", [])
        except Exception as e:
            print(f"⚠️  API Error fetching {code_system} for '{term}': {e}")
            return []

    def _get_primary_domain(self, entities: List[Dict[str, Any]]) -> Optional[str]:
        """
        Get primary domain from entities using priority heuristic.

        Domain priority (most specific to least):
        Condition > Drug > Procedure > Measurement > Observation > Demographic
        """
        DOMAIN_PRIORITY = ["Condition", "Drug", "Procedure", "Measurement", "Observation", "Demographic"]

        entity_domains = [e.get("domain", "") for e in entities if e.get("domain")]

        for priority_domain in DOMAIN_PRIORITY:
            if priority_domain in entity_domains:
                return priority_domain

        # Fallback to first domain if no priority match
        return entity_domains[0] if entity_domains else None

    # ========================================================================
    # Removed Methods (replaced by IntelligentMimicMapper)
    # ========================================================================
    # The following 138 lines of hardcoded MIMIC mapping logic were removed:
    # - _get_mimic_mapping_for_criterion
    # - _mimic_build_candidates
    # - _mimic_filter_candidates_with_llm
    # - _mimic_format_mapping
    #
    # Replaced by: IntelligentMimicMapper (intelligent_mapper.py)
    # Benefits: LLM-powered mapping, automatic caching, confidence scoring
    # ========================================================================

    def run(
        self,
        params: models.ParseTrialsParams,
        ctx: PipelineContext,
        corpus: models.LiteratureCorpus,
    ) -> EnhancedTrialSchema:
        """Run Trialist processing pipeline."""
        documents = list(corpus.documents)
        if not documents:
            raise ValueError("Literature corpus is empty.")

        # Store context for stage output saving
        self.current_context = ctx

        # Execute the graph
        state = self.graph.invoke(
            TrialistParseState(documents=documents, processing_stages=[]),
            config={"configurable": {"project_id": ctx.project_id}},
        )

        # Convert to enhanced schema
        schema_dict = state["enhanced_schema"]
        return self._dict_to_enhanced_schema(schema_dict)

    def _dict_to_enhanced_schema(self, payload: Mapping[str, Any]) -> EnhancedTrialSchema:
        """Convert dictionary to enhanced schema."""
        # Convert criteria
        inclusion = []
        for item in payload.get("inclusion", []):
            entities = [self._dict_to_entity(e) for e in item.get("entities", [])]
            criterion = EnhancedTrialCriterion(
                id=item["id"],
                description=item.get("description", ""),
                category=item.get("category", "clinical"),
                kind=item.get("kind", "threshold"),
                value=item.get("value", {}),
                entities=entities,
                validation_score=item.get("validation_score")
            )
            inclusion.append(criterion)
        
        exclusion = []
        for item in payload.get("exclusion", []):
            entities = [self._dict_to_entity(e) for e in item.get("entities", [])]
            criterion = EnhancedTrialCriterion(
                id=item["id"],
                description=item.get("description", ""),
                category=item.get("category", "clinical"),
                kind=item.get("kind", "threshold"),
                value=item.get("value", {}),
                entities=entities,
                validation_score=item.get("validation_score")
            )
            exclusion.append(criterion)
        
        features = []
        for item in payload.get("features", []):
            entities = [self._dict_to_entity(e) for e in item.get("entities", [])]
            feature = EnhancedTrialFeature(
                name=item["name"],
                source=item.get("source", "derived"),
                unit=item.get("unit"),
                time_window=tuple(item["time_window"]) if item.get("time_window") else None,
                metadata=item.get("metadata"),
                entities=entities,
                validation_score=item.get("validation_score")
            )
            features.append(feature)
        
        # Convert outcomes
        outcomes = []
        for item in payload.get("outcomes", []):
            entity = self._dict_to_entity(item)
            outcomes.append(entity)

        # Convert temporal relations
        temporal_relations = []
        for item in payload.get("temporal_relations", []):
            relation = TemporalRelation(
                pattern=item["pattern"],
                value=item["value"],
                normalized_duration=item.get("normalized_duration"),
                subject_concept=item.get("subject_concept"),
                reference_concept=item.get("reference_concept"),
                confidence=item.get("confidence")
            )
            temporal_relations.append(relation)

        return EnhancedTrialSchema(
            schema_version=payload.get("schema_version", "trialist.v1"),
            disease_code=payload.get("disease_code", ""),
            inclusion=inclusion,
            exclusion=exclusion,
            features=features or [],
            provenance=payload.get("provenance") or {},
            outcomes=outcomes or [],
            temporal_relations=temporal_relations or [],
            domain_statistics=payload.get("domain_statistics"),
            vocabulary_coverage=payload.get("vocabulary_coverage")
        )

    def _dict_to_entity(self, item: Dict[str, Any]) -> EnhancedNamedEntity:
        """Convert dictionary to enhanced entity."""
        return EnhancedNamedEntity(
            text=item.get("text", ""),
            type=item.get("type", "concept"),
            domain=item.get("domain", "Unknown"),
            start=item.get("start"),
            end=item.get("end"),
            confidence=item.get("confidence"),
            standard_name=item.get("standard_name"),
            umls_cui=item.get("umls_cui"),
            code_system=item.get("code_system"),
            code_set=item.get("code_set"),
            primary_code=item.get("primary_code"),
            # Value extraction fields (Phase 1.1)
            operator=item.get("operator"),
            numeric_value=item.get("numeric_value"),
            value_range=tuple(item["value_range"]) if item.get("value_range") else None,
            unit=item.get("unit"),
            ucum_unit=item.get("ucum_unit"),
            # Temporal normalization fields (Phase 1.3)
            temporal_pattern=item.get("temporal_pattern"),
            iso_duration=item.get("iso_duration"),
            reference_point=item.get("reference_point"),
            # Relationship fields (Phase 2.1)
            logical_operator=item.get("logical_operator"),
            related_entity_ids=item.get("related_entity_ids"),
            # Inference fields (Phase 2.2)
            is_inferred=item.get("is_inferred", False),
            inferred_from=item.get("inferred_from"),
            metadata=item.get("metadata")
        )


__all__ = ["TrialistParser"]