# Trialist Agent Technical Specification

## Overview

The **Trialist Agent** is an advanced clinical trial parser that extends the existing `LangGraphTrialParser` with enhanced Named Entity Recognition (NER), standardization, and Common Data Model (CDM) mapping capabilities. It transforms unstructured clinical trial protocols into machine-readable, OMOP CDM-compatible formats.

## Architecture

The Trialist Agent implements a **3-stage pipeline**:

```
Raw Clinical Text → Stage 1: NER → Stage 2: Standardization → Stage 3: CDM Mapping
```

### Stage 1: Enhanced Named Entity Recognition (NER)

**Objective**: Extract and classify clinical concepts with detailed domain categorization.

**Input**: Raw clinical trial text (eligibility criteria, interventions, outcomes)

**Output**: Annotated text with entities classified by domain and type

#### Domain Classifications

| Domain | Description | Examples |
|--------|-------------|----------|
| `Demographic` | Patient characteristics | Age, gender, race |
| `Condition` | Medical conditions/diseases | Hypertension, diabetes, septic shock |
| `Device` | Medical devices | Pacemaker, ventilator, catheter |
| `Procedure` | Medical procedures | Surgery, biopsy, intubation |
| `Drug` | Medications and substances | Hydrocortisone, aspirin, vitamin C |
| `Measurement` | Lab values and vital signs | Blood pressure, glucose, creatinine |
| `Observation` | Clinical observations | ICU admission, hospital stay |
| `Visit` | Healthcare encounters | Outpatient visit, emergency visit |
| `Negation_cue` | Negation indicators | No history of, without, exclude |
| `Temporal` | Time expressions | Within 24 hours, past 3 months |
| `Quantity` | Numeric values with units | 50 mg, 140 mmHg |
| `Value` | Standalone numeric values | 18, 3.5, >2.0 |

#### Entity Types

- **Concept**: Medical concepts (conditions, procedures, drugs, etc.)
- **Temporal**: Time-related expressions
- **Value**: Numeric values and quantities

#### Processing Rules

1. **Maximum Granularity**: Split compound concepts into individual components
   - "Allergy to vitamin C, hydrocortisone, or thiamine" → 3 separate allergy concepts
2. **Inference**: Add implicit concepts
   - "Patients < 18 years" → add explicit "age" concept
3. **Context Preservation**: Maintain relationship between concepts and modifiers

#### Stage 1 Output Format

```json
{
  "source_text": "History of traumatic brain injury within the past 3 months before the ICU admission",
  "annotations": [
    {
      "text": "traumatic brain injury",
      "domain": "Condition",
      "type": "Concept",
      "start": 11,
      "end": 34,
      "confidence": 0.95
    },
    {
      "text": "within the past 3 months before",
      "domain": "Temporal",
      "type": "Temporal",
      "start": 35,
      "end": 67,
      "confidence": 0.92
    },
    {
      "text": "ICU admission",
      "domain": "Observation",
      "type": "Concept",
      "start": 72,
      "end": 85,
      "confidence": 0.89
    }
  ]
}
```

### Stage 2: Component Standardization

**Objective**: Normalize extracted concepts using standard medical terminologies

**Method**: 
- **Concept Normalization**: UMLS (Unified Medical Language System)
- **Temporal Normalization**: Time Event Ontology patterns
- **OHDSI APIs**: For additional concept mapping

#### Temporal Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `XBeforeY` | X occurs before Y | "before surgery" |
| `XBeforeYwithTime` | X before Y with time interval | "3 months before ICU admission" |
| `XAfterY` | X occurs after Y | "after discharge" |
| `XDuringY` | X occurs during Y | "during hospitalization" |
| `XWithinTime` | X within time period | "within 24 hours" |
| `XForDuration` | X for duration | "for 7 days" |

#### Stage 2 Output Format

```json
{
  "source_text": "History of traumatic brain injury within the past 3 months before the ICU admission",
  "annotations": [
    {
      "text": "traumatic brain injury",
      "domain": "Condition",
      "type": "Concept",
      "standard_name": "Traumatic Brain Injury",
      "umls_cui": "C0876926",
      "confidence": 0.95
    },
    {
      "text": "within the past 3 months before",
      "domain": "Temporal",
      "type": "Temporal",
      "temporal_pattern": "XBeforeYwithTime",
      "temporal_value": "3 month",
      "normalized_duration": "P3M",
      "confidence": 0.92
    },
    {
      "text": "ICU admission",
      "domain": "Observation",
      "type": "Concept",
      "standard_name": "Admission to Intensive Care Unit",
      "umls_cui": "C0184666",
      "confidence": 0.89
    }
  ]
}
```

### Stage 3: Common Data Model (CDM) Mapping

**Objective**: Map standardized concepts to OMOP CDM codes for direct EHR querying

**Method**: Domain-specific vocabulary mapping

#### Vocabulary Mapping Rules

| Domain | Primary Vocabulary | Secondary Vocabularies |
|--------|-------------------|----------------------|
| Condition | ICD-10-CM, ICD-9-CM | SNOMED CT |
| Drug | RxNorm | ATC, NDC |
| Measurement | LOINC | CPT4, HCPCS |
| Procedure | CPT4, ICD-10-PCS | SNOMED CT, HCPCS |
| Device | SNOMED CT | HCPCS |
| Observation | SNOMED CT | LOINC |

#### Stage 3 Output Format

```json
{
  "source_text": "History of traumatic brain injury within the past 3 months before the ICU admission",
  "components": [
    {
      "text": "traumatic brain injury",
      "domain": "Condition",
      "standard_name": "Traumatic Brain Injury",
      "umls_cui": "C0876926",
      "code_system": "ICD-10-CM",
      "code_set": ["S06.9X9A", "S06.2X9A", "S06.1X9A"],
      "primary_code": "S06.9X9A",
      "confidence": 0.95
    },
    {
      "text": "ICU admission",
      "domain": "Observation",
      "standard_name": "Admission to Intensive Care Unit",
      "umls_cui": "C0184666",
      "code_system": "SNOMED CT",
      "code_set": ["305351004", "32485007"],
      "primary_code": "305351004",
      "confidence": 0.89
    }
  ],
  "temporal_relations": [
    {
      "pattern": "XBeforeYwithTime",
      "value": "3 month",
      "normalized_duration": "P3M",
      "subject_concept": "traumatic brain injury",
      "reference_concept": "ICU admission",
      "confidence": 0.92
    }
  ]
}
```

## Integration with Existing Pipeline

### Model Extensions

The Trialist Agent extends the existing `TrialSchema` model:

```python
@dataclass(frozen=True)
class EnhancedNamedEntity:
    """Enhanced named entity with domain classification and standardization."""
    text: str
    type: Literal["concept", "temporal", "value"]
    domain: str  # New: Domain classification
    start: int | None = None
    end: int | None = None
    confidence: float | None = None
    standard_name: str | None = None  # New: Standardized name
    umls_cui: str | None = None  # New: UMLS CUI
    code_system: str | None = None  # New: Vocabulary system
    code_set: Sequence[str] | None = None  # New: Concept codes
    primary_code: str | None = None  # New: Primary code
    metadata: Mapping[str, Any] | None = None

@dataclass(frozen=True)
class TemporalRelation:
    """Temporal relationship between concepts."""
    pattern: str
    value: str
    normalized_duration: str | None = None
    subject_concept: str | None = None
    reference_concept: str | None = None
    confidence: float | None = None

@dataclass(frozen=True)
class EnhancedTrialSchema:
    """Enhanced trial schema with Trialist processing."""
    schema_version: str
    disease_code: str
    inclusion: Sequence[TrialCriterion]
    exclusion: Sequence[TrialCriterion]
    features: Sequence[TrialFeature]
    provenance: Mapping[str, Any]
    temporal_relations: Sequence[TemporalRelation] | None = None  # New
    processing_metadata: Mapping[str, Any] | None = None  # New
```

### Plugin Architecture

```python
class TrialistParser(Protocol):
    def run(
        self,
        params: ParseTrialsParams,
        ctx: PipelineContext,
        corpus: LiteratureCorpus,
    ) -> EnhancedTrialSchema: ...
```

## Implementation Phases

### Phase 1: Enhanced NER Implementation
- Extend existing LangGraph parser with domain classification
- Implement 12-domain taxonomy
- Add granularity and inference rules

### Phase 2: Standardization Layer
- Integrate UMLS API for concept normalization
- Implement temporal pattern recognition
- Add confidence scoring

### Phase 3: CDM Mapping
- Implement OMOP vocabulary mapping
- Add code system integration
- Create validation framework

### Phase 4: Integration & Testing
- Update pipeline models and services
- Create comprehensive test suite
- Performance optimization

## Configuration

```yaml
trialist:
  enabled: true
  llm_provider: "gpt-4o-mini"
  temperature: 0.0
  stages:
    ner:
      max_granularity: true
      inference_enabled: true
      confidence_threshold: 0.7
    standardization:
      umls_api_key: "${UMLS_API_KEY}"
      ohdsi_endpoint: "https://athena.ohdsi.org/api"
      temporal_ontology: "time_event_v1"
    cdm_mapping:
      primary_vocabularies:
        condition: "ICD-10-CM"
        drug: "RxNorm" 
        measurement: "LOINC"
        procedure: "CPT4"
      fallback_enabled: true
```

## API Extensions

### New Endpoints

```
POST /api/pipeline/parse-trials-enhanced
  - Uses Trialist parser with full 3-stage processing

GET /api/trialist/vocabularies
  - Lists available code systems and vocabularies

POST /api/trialist/validate-codes
  - Validates concept codes against OMOP CDM
```

### Enhanced Responses

All parsing responses will include:
- Domain-classified entities
- Standardized concept names
- OMOP CDM codes
- Temporal relationships
- Confidence scores

This specification provides the foundation for implementing a production-ready Trialist Agent that transforms clinical trial protocols into standardized, machine-readable formats compatible with EHR systems and research databases.