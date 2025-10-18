from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, TypedDict
from string import Template

from .. import models
from ..context import PipelineContext

PROMPT_TEMPLATE = Template("""\
You are a board-certified cardiologist and clinical trial methodologist with expertise in Named Entity Recognition (NER). Study the following trial documents and extract structured eligibility criteria with detailed entity annotations.

**CRITICAL TASK: Named Entity Recognition (NER)**
For EACH criterion, treatment, and outcome, you must identify and extract three types of entities:

1. **CONCEPT** entities (cyan/blue):
   - Medical conditions: septic shock, stroke, traumatic brain injury, organ dysfunction
   - Treatments: Hydrocortisone sodium succinate
   - Outcomes: 28-day mortality
   - Anatomical terms: ICU
   - Demographic attributes: Age

2. **TEMPORAL** entities (yellow):
   - Age ranges: ≥ 18 years old
   - Time windows: within 24 hours, within the past 3 months, for at least 6 consecutive hours
   - Duration: 7 days, every 6 hours
   - Relative time: before the ICU admission, after the ICU admission, until ICU discharge

3. **VALUE** entities (magenta/pink):
   - Numeric values with units: 50 mg, 18 years
   - Thresholds: > 2.0 mmol/L

**EXAMPLE:**
Text: "Age ≥ 18 years old"
Entities:
- {{"text": "Age", "type": "concept"}}
- {{"text": "≥ 18 years old", "type": "temporal"}}

Text: "Diagnosis of septic shock within 24 hours after the ICU admission"
Entities:
- {{"text": "septic shock", "type": "concept"}}
- {{"text": "within 24 hours after", "type": "temporal"}}
- {{"text": "ICU admission", "type": "concept"}}

Text: "Hydrocortisone sodium succinate, 50 mg, every 6 hours, 7 days or until ICU discharge"
Entities:
- {{"text": "Hydrocortisone sodium succinate", "type": "concept"}}
- {{"text": "50 mg", "type": "value"}}
- {{"text": "every 6 hours", "type": "temporal"}}
- {{"text": "7 days or until ICU discharge", "type": "temporal"}}
- {{"text": "ICU discharge", "type": "concept"}}

**OUTPUT FORMAT:**
Return ONLY a JSON object with the following top-level keys:
- schema_version (string, e.g., "schema.v1")
- disease_code (string; ICD-10, common trial acronym, or disease slug)
- inclusion (array of criteria with entities) - Extract from "Inclusion Criteria:" section
- exclusion (array of criteria with entities) - Extract from "Exclusion Criteria:" section
- features (array of feature definitions with entities)
- provenance (object with metadata: title, journal, year, doi, registry_id if available, llm_notes)

Each eligibility criterion must be an object:
- id: string, snake_case, prefixed with "inc_" or "exc_"
- description: concise clinical sentence copied or paraphrased from the eligibility criteria text
- category: one of ["demographic", "clinical", "laboratory", "imaging", "therapy"]
- kind: e.g., "threshold", "diagnosis", "temporal", "composite"
- value: JSON object describing the rule
- **entities**: array of entity objects with "text" (string) and "type" (concept/temporal/value)

Each feature must include:
- name: snake_case variable name
- source: table identifier (echodata, labevents, patients, chartevents, prescriptions, other)
- unit: measurement unit or null
- time_window: [start_hours, end_hours] relative to index time or null
- metadata: include role (primary_outcome, secondary_outcome, treatment, etc.)
- **entities**: array of entity objects with "text" (string) and "type" (concept/temporal/value)

**RULES:**
1. Extract criteria DIRECTLY from the "Inclusion Criteria:" and "Exclusion Criteria:" sections
2. For EVERY criterion and feature, extract ALL concept, temporal, and value entities
3. Entities must be verbatim text spans from the description
4. All numeric values must be numbers, not strings (except in entity text)
5. Mark uncertainty in provenance.llm_notes

Documents:
{document_context}

Provide the JSON object only with no extra commentary.
""")


class TrialParseState(TypedDict, total=False):
    documents: List[models.LiteratureDocument]
    document_context: str
    raw_response: str
    schema_dict: Dict[str, Any]


def _build_llm_chain(model_name: Optional[str] = None, temperature: float = 0.0):
    try:
        from langchain_openai import ChatOpenAI
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "langchain-openai package is required. Install via `pip install langchain-openai`."
        ) from exc

    if model_name is None:
        model_name = "gpt-4o-mini"
    return ChatOpenAI(model=model_name, temperature=temperature)


def _get_text_splitter():
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "LangChain text splitter unavailable. Install langchain package."
        ) from exc
    return RecursiveCharacterTextSplitter(
        chunk_size=2500,
        chunk_overlap=250,
        separators=["\n## ", "\n### ", "\n", ". "],
    )


class LangGraphTrialParser:
    """
    Parse trial documents using a LangGraph pipeline composed of LangChain components.
    """

    def __init__(
        self,
        llm: Any | None = None,
        model_name: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        self.llm = llm or _build_llm_chain(model_name=model_name, temperature=temperature)
        self.text_splitter = _get_text_splitter()
        self.graph = self._build_graph()

    def _build_graph(self):
        try:
            from langgraph.graph import END, START, StateGraph
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "LangGraph is required. Install langgraph package."
            ) from exc

        workflow: StateGraph[TrialParseState] = StateGraph(TrialParseState)
        workflow.add_node("prepare_context", self._prepare_context)
        workflow.add_node("extract_schema", self._extract_schema)
        workflow.add_node("validate_schema", self._validate_schema)
        workflow.add_edge(START, "prepare_context")
        workflow.add_edge("prepare_context", "extract_schema")
        workflow.add_edge("extract_schema", "validate_schema")
        workflow.add_edge("validate_schema", END)
        return workflow.compile()

    def _prepare_context(self, state: TrialParseState) -> TrialParseState:
        documents = state.get("documents", [])
        sections: List[str] = []
        for doc in documents:
            # ClinicalTrials.gov 데이터에서 4가지 핵심 정보를 명시적으로 추출:
            # 1. Inclusion Criteria, 2. Exclusion Criteria, 3. Treatment/Interventions, 4. Primary Outcomes
            eligibility_text = ""
            treatment_text = ""
            outcomes_text = ""
            
            if doc.metadata:
                # eligibility 모듈에서 직접 가져오기
                eligibility = doc.metadata.get("eligibility", {})
                if isinstance(eligibility, dict):
                    criteria = eligibility.get("eligibilityCriteria", "")
                    if criteria:
                        eligibility_text = f"\n\n## Eligibility Criteria\n\n{criteria}"
                
                # full_study_data에서 추출
                full_data = doc.metadata.get("full_study_data", {})
                if isinstance(full_data, dict):
                    protocol = full_data.get("protocolSection", {})
                    if isinstance(protocol, dict):
                        # Eligibility Criteria (full_study_data 우선 확인)
                        if not eligibility_text:
                            elig_module = protocol.get("eligibilityModule", {})
                            if isinstance(elig_module, dict):
                                criteria = elig_module.get("eligibilityCriteria", "")
                                if criteria:
                                    eligibility_text = f"\n\n## Eligibility Criteria\n\n{criteria}"
                        
                        # Treatment/Interventions 추출
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
                                    treatment_text = f"\n\n## Treatment/Interventions\n\n" + "\n".join(treatment_parts)
                        
                        # Primary Outcomes 추출
                        outcomes_module = protocol.get("outcomesModule", {})
                        if isinstance(outcomes_module, dict):
                            primary_outcomes = outcomes_module.get("primaryOutcomes", [])
                            if primary_outcomes:
                                outcome_parts = []
                                for outcome in primary_outcomes:
                                    if isinstance(outcome, dict):
                                        measure = outcome.get("measure", "")
                                        timeframe = outcome.get("timeFrame", "")
                                        outcome_parts.append(
                                            f"- **{measure}** (Time Frame: {timeframe})" if timeframe else f"- **{measure}**"
                                        )
                                if outcome_parts:
                                    outcomes_text = f"\n\n## Primary Outcomes\n\n" + "\n".join(outcome_parts)
            
            # 기본 문서 텍스트 조합 (4가지 핵심 정보 포함)
            doc_text = "\n\n".join(
                filter(
                    None,
                    [
                        f"## Trial: {doc.title.strip()}",
                        (doc.abstract or "").strip(),
                        eligibility_text,  # Inclusion/Exclusion Criteria
                        treatment_text,    # Treatment/Interventions
                        outcomes_text,     # Primary Outcomes
                        (doc.full_text or "").strip(),
                    ],
                )
            )
            
            chunks = self.text_splitter.split_text(doc_text)
            sections.extend(chunks)
        
        context = "\n\n---\n\n".join(sections)[:20000]
        return TrialParseState(**state, document_context=context)

    def _extract_schema(self, state: TrialParseState) -> TrialParseState:
        document_context = state.get("document_context", "")
        if not document_context:
            raise ValueError("document_context is empty; cannot extract schema.")

        prompt = PROMPT_TEMPLATE.substitute(document_context=document_context)
        response = self.llm.invoke(prompt)
        content = getattr(response, "content", response)
        if not isinstance(content, str):
            raise ValueError("LLM response did not return string content.")
        return TrialParseState(**state, raw_response=content.strip())

    def _validate_schema(self, state: TrialParseState) -> TrialParseState:
        raw = state.get("raw_response", "")
        if not raw:
            raise ValueError("LLM returned empty response.")
        try:
            schema_dict = self._parse_json_response(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "LLM response was not valid JSON. Enable Guardrails or adjust prompt."
            ) from exc

        required_keys = {
            "schema_version",
            "disease_code",
            "inclusion",
            "exclusion",
            "features",
            "provenance",
        }
        missing = required_keys - schema_dict.keys()
        if missing:
            raise ValueError(f"Schema response missing keys: {sorted(missing)}")
        return TrialParseState(**state, schema_dict=schema_dict)

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
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

    def run(
        self,
        params: models.ParseTrialsParams,
        ctx: PipelineContext,
        corpus: models.LiteratureCorpus,
    ) -> models.TrialSchema:
        documents = list(corpus.documents)
        if not documents:
            raise ValueError("Literature corpus is empty.")

        state = self.graph.invoke(
            TrialParseState(documents=documents),
            config={"configurable": {"project_id": ctx.project_id}},
        )
        schema_dict = state["schema_dict"]
        return self._dict_to_schema(schema_dict)

    def _dict_to_schema(self, payload: Mapping[str, Any]) -> models.TrialSchema:
        def build_entities(entities_data: list[dict[str, Any]] | None) -> list[models.NamedEntity] | None:
            """Parse entities from LLM response."""
            if not entities_data:
                return None
            entities = []
            for entity in entities_data:
                entities.append(
                    models.NamedEntity(
                        text=entity.get("text", ""),
                        type=entity.get("type", "concept"),
                        start=entity.get("start"),
                        end=entity.get("end"),
                        metadata=entity.get("metadata"),
                    )
                )
            return entities if entities else None

        def build_criterion(item: Mapping[str, Any]) -> models.TrialCriterion:
            entities = build_entities(item.get("entities"))
            return models.TrialCriterion(
                id=item["id"],
                description=item.get("description", ""),
                category=item.get("category", "clinical"),
                kind=item.get("kind", "threshold"),
                value=item.get("value", {}),
                entities=entities,
            )

        def build_feature(item: Mapping[str, Any]) -> models.TrialFeature:
            time_window = item.get("time_window")
            if time_window is not None:
                time_window = tuple(time_window)
            entities = build_entities(item.get("entities"))
            return models.TrialFeature(
                name=item["name"],
                source=item.get("source", "derived"),
                unit=item.get("unit"),
                time_window=time_window,
                metadata=item.get("metadata"),
                entities=entities,
            )

        inclusion = [build_criterion(it) for it in payload.get("inclusion", [])]
        exclusion = [build_criterion(it) for it in payload.get("exclusion", [])]
        features = [build_feature(it) for it in payload.get("features", [])]
        provenance = payload.get("provenance") or {}
        return models.TrialSchema(
            schema_version=payload.get("schema_version", "schema.v1"),
            disease_code=payload.get("disease_code", ""),
            inclusion=inclusion,
            exclusion=exclusion,
            features=features,
            provenance=provenance,
        )


__all__ = ["LangGraphTrialParser"]
