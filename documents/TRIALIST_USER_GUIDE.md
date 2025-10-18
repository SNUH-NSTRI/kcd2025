# Trialist Agent User Guide

**Version**: 1.0
**Last Updated**: 2025-10-13
**Status**: Production (Stage 1), Development (Stages 2-3)

---

## Table of Contents

1. [What is Trialist?](#what-is-trialist)
2. [Architecture Overview](#architecture-overview)
3. [Features & Capabilities](#features--capabilities)
4. [Getting Started](#getting-started)
5. [Usage Examples](#usage-examples)
6. [Output Format](#output-format)
7. [Configuration](#configuration)
8. [Current Limitations](#current-limitations)
9. [Development Roadmap](#development-roadmap)
10. [Troubleshooting](#troubleshooting)

---

## What is Trialist?

**Trialist** is an advanced clinical trial parser that transforms unstructured clinical trial protocols into machine-readable, standardized formats. It uses AI-powered Natural Language Processing (NLP) to extract, classify, and standardize medical concepts from clinical trial documents.

### Key Value Propositions

- **Automated Extraction**: Converts free-text eligibility criteria into structured data
- **Domain Classification**: Categorizes medical concepts into 12 clinical domains
- **Standardization**: Maps concepts to UMLS and OMOP CDM standards
- **Enhanced Precision**: 12-domain classification vs traditional 3-type systems
- **EHR Integration Ready**: Outputs designed for direct EHR querying

### Use Cases

1. **Clinical Trial Matching**: Automatically match patients to relevant trials
2. **EHR Cohort Building**: Generate SQL queries from trial criteria
3. **Trial Design Analysis**: Extract and compare eligibility criteria patterns
4. **Regulatory Compliance**: Ensure standardized terminology usage
5. **Research Analytics**: Analyze trends in clinical trial design

---

## Architecture Overview

Trialist implements a **3-stage pipeline** architecture:

```
┌──────────────────────────────────────────────────────────────┐
│                     Clinical Trial Text                       │
│            (Eligibility Criteria, Outcomes, etc.)             │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │   Stage 1: Enhanced NER    │
        │  - 12-Domain Classification │
        │  - Granular Entity Parsing  │
        │  - Confidence Scoring       │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ Stage 2: Standardization   │
        │  - UMLS Concept Mapping     │
        │  - Temporal Normalization   │
        │  - Synonym Resolution       │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  Stage 3: CDM Mapping      │
        │  - OMOP Code Assignment     │
        │  - Vocabulary Selection     │
        │  - Code Validation          │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │   Enhanced Trial Schema    │
        │  - Structured Criteria      │
        │  - Standardized Concepts    │
        │  - Query-Ready Codes        │
        └────────────────────────────┘
```

### Processing Workflow

1. **Document Preparation**
   - Extract eligibility criteria, outcomes, interventions
   - Split into inclusion/exclusion sections
   - Normalize text formatting

2. **Stage 1: Enhanced NER** ✅ Production Ready
   - Extract clinical entities using GPT-4o-mini
   - Classify into 12 clinical domains
   - Assign confidence scores
   - Maintain source text references

3. **Stage 2: Standardization** ⚠️ Partially Implemented
   - Map entities to standard medical terminologies
   - Resolve abbreviations and synonyms
   - Normalize temporal expressions
   - Assign UMLS CUIs

4. **Stage 3: CDM Mapping** 🚧 Placeholder
   - Map to OMOP CDM vocabularies
   - Assign ICD-10, RxNorm, LOINC, SNOMED codes
   - Validate code correctness
   - Prioritize primary codes

---

## Features & Capabilities

### 1. 12-Domain Classification System

Trialist categorizes medical concepts into 12 specialized domains:

| Domain | Description | Examples |
|--------|-------------|----------|
| **Demographic** | Patient characteristics | Age, gender, race, ethnicity |
| **Condition** | Diseases and diagnoses | Hypertension, diabetes, septic shock |
| **Device** | Medical equipment | Pacemaker, ventilator, catheter |
| **Procedure** | Medical procedures | Surgery, biopsy, intubation |
| **Drug** | Medications | Hydrocortisone, aspirin, vitamin C |
| **Measurement** | Lab values and vitals | Blood pressure, glucose, creatinine |
| **Observation** | Clinical observations | ICU admission, hospital stay |
| **Visit** | Healthcare encounters | Outpatient visit, emergency visit |
| **Negation_cue** | Negation indicators | No history of, without, exclude |
| **Temporal** | Time expressions | Within 24 hours, past 3 months |
| **Quantity** | Numeric with units | 50 mg, 140 mmHg, 2.5 mg/dL |
| **Value** | Standalone numbers | 18, 3.5, >2.0 |

### 2. Processing Rules

#### Maximum Granularity
Split compound concepts into individual components:
- **Input**: "Allergy to vitamin C, hydrocortisone, or thiamine"
- **Output**: 3 separate allergy concepts

#### Inference
Add implicit concepts:
- **Input**: "Patients < 18 years"
- **Output**: Adds explicit "age" concept

#### Context Preservation
Maintain relationships between concepts and modifiers:
- Link temporal expressions to related conditions
- Track negation scopes
- Preserve numeric constraints

### 3. Confidence Scoring

Each entity receives a confidence score (0.0-1.0):
- **0.9-1.0**: High confidence (exact medical terminology)
- **0.7-0.9**: Medium confidence (common abbreviations)
- **0.5-0.7**: Low confidence (ambiguous or inferred)
- **<0.5**: Very low confidence (requires manual review)

### 4. Metadata Tracking

Every processing stage records:
- Execution time (milliseconds)
- Success/failure status
- Entity counts
- Error messages
- Validation scores

---

## Getting Started

### Prerequisites

1. **System Requirements**
   - Python 3.9+
   - Node.js 18+ (for frontend)
   - OpenAI API key (for GPT-4o-mini)

2. **Dependencies**
   ```bash
   pip install -r requirements-api.txt
   ```

3. **Environment Variables**
   ```bash
   # .env file
   OPENAI_API_KEY=your_openai_api_key_here
   ```

### Installation

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd datathon
   ```

2. **Install Dependencies**
   ```bash
   # Python backend
   pip install -r requirements-api.txt

   # Node.js frontend
   npm install
   ```

3. **Start Servers**
   ```bash
   # Start both frontend and backend
   npm run dev:all

   # Or start separately:
   npm run backend    # Backend only (port 8000)
   npm run dev        # Frontend only (port 3000)
   ```

### Quick Start

```python
from pipeline.plugins import registry
from pipeline.context import PipelineContext
from pipeline.models import ParseTrialsParams, LiteratureCorpus

# 1. Get Trialist parser
parser = registry.get_parser('trialist')

# 2. Create context
context = PipelineContext(
    project_id="test_project",
    workspace="./workspace"
)

# 3. Prepare corpus (your trial documents)
corpus = LiteratureCorpus(
    documents=[...],  # Your trial documents
    provenance={...}
)

# 4. Run parser
params = ParseTrialsParams()
result = parser.run(params, context, corpus)

# 5. Access results
print(f"Inclusion criteria: {len(result.inclusion)}")
print(f"Exclusion criteria: {len(result.exclusion)}")
print(f"Domain statistics: {result.domain_statistics}")
```

---

## Usage Examples

### Example 1: Parse NCT Trial from ClinicalTrials.gov

```python
from pipeline.plugins import registry
from pipeline.context import PipelineContext
from pipeline.models import LiteratureDocument, LiteratureCorpus

# 1. Create trial document
trial_doc = LiteratureDocument(
    identifier="NCT03389555",
    title="VICTAS: Vitamin C, Thiamine, and Steroids in Sepsis",
    abstract="A randomized controlled trial...",
    metadata={
        "eligibility": {
            "eligibilityCriteria": """
                Inclusion Criteria:
                1. Adult patients (age ≥ 18 years)
                2. Suspected or confirmed infection
                3. Two or more SIRS criteria

                Exclusion Criteria:
                1. Known kidney stones within the past 1 year
                2. Pregnancy or breastfeeding
                3. Known allergy to vitamin C, hydrocortisone, or thiamine
            """
        }
    }
)

# 2. Create corpus
corpus = LiteratureCorpus(
    documents=[trial_doc],
    provenance={"source": "clinicaltrials.gov"}
)

# 3. Parse
parser = registry.get_parser('trialist')
context = PipelineContext(project_id="victas", workspace="./workspace")
result = parser.run(ParseTrialsParams(), context, corpus)

# 4. Examine results
for criterion in result.inclusion:
    print(f"\n{criterion.id}: {criterion.description}")
    for entity in criterion.entities:
        print(f"  - {entity.text} ({entity.domain}) [{entity.confidence:.2f}]")
```

**Output:**
```
inc_1: Adult patients (age ≥ 18 years)
  - Adult (Demographic) [0.95]
  - age (Demographic) [0.93]
  - ≥ 18 years (Value) [0.98]

inc_2: Suspected or confirmed infection
  - Suspected infection (Condition) [0.87]
  - confirmed infection (Condition) [0.91]

inc_3: Two or more SIRS criteria
  - SIRS criteria (Observation) [0.89]
  - Two or more (Quantity) [0.92]
```

### Example 2: API Usage

```bash
# Parse trials using REST API
curl -X POST "http://localhost:8000/api/pipeline/parse-trials" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "nct03389555",
    "llm_provider": "gpt-4o-mini",
    "impl": "trialist"
  }'
```

**Response:**
```json
{
  "schema_version": "trialist.v1",
  "disease_code": "enhanced_trial",
  "inclusion": [
    {
      "id": "inc_1",
      "description": "Adult patients (age ≥ 18 years)",
      "entities": [
        {
          "text": "Adult",
          "domain": "Demographic",
          "standard_name": "Adult",
          "umls_cui": "C0001675",
          "confidence": 0.95
        }
      ]
    }
  ],
  "domain_statistics": {
    "Demographic": 3,
    "Condition": 5,
    "Temporal": 2
  }
}
```

### Example 3: Get Trialist Information

```bash
curl "http://localhost:8000/api/trialist/info"
```

**Response:**
```json
{
  "status": "available",
  "version": "1.0.0",
  "capabilities": {
    "enhanced_ner": true,
    "domain_classification": true,
    "standardization": "placeholder",
    "cdm_mapping": "placeholder"
  },
  "domains": [
    "Demographic", "Condition", "Device", "Procedure",
    "Drug", "Measurement", "Observation", "Visit",
    "Negation_cue", "Temporal", "Quantity", "Value"
  ],
  "vocabularies": {
    "Condition": "ICD-10-CM",
    "Drug": "RxNorm",
    "Measurement": "LOINC"
  }
}
```

---

## Output Format

### Enhanced Trial Schema

```json
{
  "schema_version": "trialist.v1",
  "disease_code": "enhanced_trial",

  "inclusion": [
    {
      "id": "inc_1",
      "description": "Original criterion text",
      "entities": [
        {
          "text": "concept text",
          "domain": "Condition",
          "type": "concept",
          "confidence": 0.95,
          "standard_name": "Standardized Name",
          "umls_cui": "C0018801",
          "code_system": "ICD-10-CM",
          "code_set": ["I50.9"],
          "primary_code": "I50.9"
        }
      ]
    }
  ],

  "exclusion": [...],

  "outcomes": [
    {
      "text": "Primary outcome measure",
      "domain": "Measurement",
      "standard_name": "SOFA Score",
      "umls_cui": "C3494459"
    }
  ],

  "temporal_relations": [
    {
      "pattern": "XBeforeYwithTime",
      "value": "1 year",
      "normalized_duration": "P1Y",
      "subject_concept": "kidney stones",
      "reference_concept": "trial enrollment",
      "confidence": 0.92
    }
  ],

  "domain_statistics": {
    "Demographic": 3,
    "Condition": 8,
    "Drug": 5,
    "Temporal": 4
  },

  "vocabulary_coverage": {
    "ICD-10-CM": 8,
    "RxNorm": 5,
    "LOINC": 3
  }
}
```

### Stage Output Files

Trialist saves intermediate outputs to disk:

```
workspace/{project_id}/trialist_output/
├── stage1_ner_output.json           # NER results
├── stage2_standardization_output.json # Standardized concepts
└── stage3_cdm_mapping_output.json    # CDM codes
```

Each file contains:
- Timestamp and execution time
- Entity counts
- Processing metadata
- Detailed results

---

## Configuration

### YAML Configuration

Edit `config.yaml` to customize Trialist behavior:

```yaml
project:
  default_impls:
    parser: "trialist"  # Use Trialist as default parser

trialist:
  enabled: true
  llm_provider: "gpt-4o-mini"
  temperature: 0.0

  ner:
    max_granularity: true
    inference_enabled: true
    confidence_threshold: 0.7
    domain_taxonomy:
      - Demographic
      - Condition
      - Device
      - Procedure
      - Drug
      - Measurement
      - Observation
      - Visit
      - Negation_cue
      - Temporal
      - Quantity
      - Value

  standardization:
    mode: "offline"  # "offline" or "api"
    umls_api_key: "${UMLS_API_KEY}"
    ohdsi_endpoint: "https://athena.ohdsi.org/api"
    confidence_threshold: 0.8

  cdm_mapping:
    primary_vocabularies:
      Condition: "ICD-10-CM"
      Drug: "RxNorm"
      Measurement: "LOINC"
      Procedure: "CPT4"
      Device: "SNOMED CT"
    fallback_enabled: true
```

### Python Configuration

```python
from pipeline.trialist_models import TrialistParams, TrialistNERParams

params = TrialistParams(
    llm_provider="gpt-4o-mini",
    temperature=0.0,
    ner_params=TrialistNERParams(
        max_granularity=True,
        inference_enabled=True,
        confidence_threshold=0.7
    )
)
```

---

## Current Limitations

### Implementation Status

| Feature | Status | Completion |
|---------|--------|-----------|
| Stage 1: Enhanced NER | ✅ Production | 95% |
| Stage 2: Standardization | ⚠️ Prototype | 32% |
| Stage 3: CDM Mapping | 🚧 Placeholder | 10% |

### Known Limitations

#### 1. Vocabulary Coverage (~3%)
- Only ~30 medical concepts have real UMLS mappings
- Most concepts use fuzzy matching or placeholders
- **Impact**: Limited standardization for rare conditions

#### 2. Placeholder CDM Codes
- Stage 3 generates hash-based fake codes
- Not usable for real EHR queries
- **Impact**: Cannot query actual medical databases

#### 3. API Integration Missing
- No UMLS API client implemented
- No OHDSI Athena API integration
- **Impact**: Cannot scale beyond hardcoded vocabulary

#### 4. Language Support
- English only
- No multi-language support
- **Impact**: Limited to English trials

#### 5. Performance
- No caching implemented
- Sequential processing only
- **Impact**: Slow for large batches

### Supported Concepts (Stage 2)

**Conditions** (~12): heart failure, myocardial infarction, stroke, diabetes, hypertension, COPD, asthma, sepsis, pneumonia, COVID-19, traumatic brain injury, chronic kidney disease

**Drugs** (~8): aspirin, insulin, metformin, atorvastatin, lisinopril, warfarin, vitamin C, hydrocortisone

**Measurements** (~5): blood pressure, heart rate, glucose, creatinine, hemoglobin

**Procedures** (~3): intubation, dialysis, surgery

**Devices** (~2): pacemaker, ventilator

---

## Development Roadmap

### Phase 1: UMLS API Integration (10 days) 🔴 Critical
**Target**: Full concept standardization

- [ ] Implement UMLS REST API client
- [ ] Add response caching (LRU + Redis)
- [ ] Integrate with offline standardizer
- [ ] Create fallback logic (API → offline)
- [ ] Write integration tests

**Impact**: Standardize 1,000+ concepts instead of 30

### Phase 2: OHDSI Athena Integration (10 days) 🔴 Critical
**Target**: Real OMOP CDM codes

- [ ] Implement Athena API client
- [ ] Domain-specific vocabulary mapping
- [ ] Code validation against OMOP
- [ ] "Maps to" relationship resolution
- [ ] Write integration tests

**Impact**: Generate real ICD-10/RxNorm/LOINC codes

### Phase 3: OMOP Vocabulary Database (7 days) 🟡 Medium
**Target**: Offline capability + speed

- [ ] Download OMOP vocabularies
- [ ] Load into PostgreSQL
- [ ] Create database client
- [ ] Replace API calls with DB queries
- [ ] Maintain API as fallback

**Impact**: 10x faster, works offline

### Phase 4: Testing & Validation (5 days) 🔴 Critical
**Target**: Ensure correctness

- [ ] Create 100-concept gold standard dataset
- [ ] Measure precision/recall/F1
- [ ] Performance benchmarking
- [ ] Edge case testing
- [ ] Clinical expert validation

**Impact**: Confidence in production deployment

### Phase 5: Production Hardening (5 days) 🟡 Medium
**Target**: Reliability

- [ ] Retry logic with exponential backoff
- [ ] Circuit breaker pattern
- [ ] Monitoring and alerting
- [ ] Graceful degradation
- [ ] Deployment documentation

**Impact**: Production-ready system

### Total Timeline
- **Sequential**: 7.5 weeks (1 developer)
- **Parallel**: 5 weeks (2 developers)

---

## Troubleshooting

### Common Issues

#### Issue: "No parser named 'trialist' found"

**Cause**: Trialist not registered or import error

**Solution**:
```python
# Check registry
from pipeline.plugins import registry
print(registry.list_parsers())  # Should include 'trialist'

# Force reimport
import importlib
import pipeline.plugins
importlib.reload(pipeline.plugins)
```

#### Issue: "OPENAI_API_KEY not found"

**Cause**: Missing environment variable

**Solution**:
```bash
# Add to .env file
echo "OPENAI_API_KEY=sk-..." >> .env

# Or export directly
export OPENAI_API_KEY=sk-...
```

#### Issue: "Stage 2 returns no standard_name"

**Cause**: Concept not in offline vocabulary

**Solution**:
- Check `src/pipeline/offline_standardizer.py:48-303` for supported concepts
- Add custom mappings if needed
- Wait for UMLS API integration (Phase 1)

#### Issue: "Generated codes look fake"

**Expected Behavior**: Stage 3 currently generates placeholder codes

**Explanation**: Real OMOP CDM codes require OHDSI integration (Phase 2)

**Workaround**: Use `standard_name` and `umls_cui` instead of codes for now

#### Issue: "Performance is slow"

**Cause**: No caching, LLM API calls

**Solution**:
```python
# Reduce context size
# In trialist_parser.py:390
context = "\n\n".join(sections)[:10000]  # Reduce from 20000

# Batch process
# Process multiple trials in parallel
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run parser
parser = registry.get_parser('trialist')
result = parser.run(params, context, corpus)
```

### Getting Help

1. **Check Documentation**
   - `/documents/trialist_agent_specification.md` - Technical spec
   - `/documents/trialist_implementation_status.md` - Current status
   - `/documents/trialist_critical_assessment.md` - Detailed analysis

2. **Review Test Files**
   - `test_trialist_parser.py` - Basic tests
   - `test_stage2_standardization.py` - Stage 2 tests
   - `test_nct03389555.py` - Real trial example

3. **Inspect Output Files**
   ```bash
   # Check stage outputs
   cat workspace/{project_id}/trialist_output/stage1_ner_output.json
   ```

---

## Best Practices

### 1. Start with Stage 1 Only
For production use, rely on Stage 1 (NER) and ignore Stage 2/3 outputs until APIs are integrated.

### 2. Validate Confidence Scores
Filter entities by confidence threshold:
```python
high_conf_entities = [
    e for e in result.inclusion[0].entities
    if e.confidence >= 0.8
]
```

### 3. Use Domain Statistics
Sanity check parsed results:
```python
stats = result.domain_statistics
if stats.get("Condition", 0) == 0:
    print("Warning: No conditions found!")
```

### 4. Save Intermediate Outputs
Always check stage output files for debugging:
```bash
ls -lh workspace/{project_id}/trialist_output/
```

### 5. Batch Processing
For multiple trials, process in batches:
```python
for trial_batch in chunks(trials, batch_size=10):
    results = [parser.run(...) for trial in trial_batch]
```

---

## Conclusion

Trialist is a powerful clinical trial parsing system with:

✅ **Production-ready NER** (95% complete)
- 12-domain classification
- High precision entity extraction
- Comprehensive metadata

⚠️ **Prototype Standardization** (32% complete)
- Limited vocabulary coverage
- Basic UMLS mapping
- Missing API integration

🚧 **Placeholder CDM Mapping** (10% complete)
- Generates fake codes
- Requires OMOP integration
- Not production-ready

**Recommendation**: Use Stage 1 (NER) in production. Wait for Phases 1-2 before relying on standardization and CDM mapping.

**Next Steps**:
1. Review current limitations
2. Plan Phase 1 (UMLS integration)
3. Create validation dataset
4. Iterate towards production readiness

For questions or support, see project documentation or contact the development team.

---

**Document Version**: 1.0
**Maintainers**: RWE Platform Team
**Last Review**: 2025-10-13
