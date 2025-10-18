# ICD-10CM Mapping Implementation

## Overview

This document describes the implementation of ICD-10CM code mapping using OHDSI's `concept_relationship` table. The feature automatically maps SNOMED CT concepts to ICD-10CM codes for clinical/administrative use.

## Implementation Details

### 1. OHDSIClient Enhancement

**File**: `src/pipeline/clients/ohdsi_client.py`

Added `get_icd10cm_codes()` method that:
- Takes a SNOMED concept ID as input
- Queries OHDSI `concept_relationship` table for "Maps to" / "Mapped from" relationships
- Filters for ICD10CM vocabulary
- Returns list of ICD-10CM codes

**Method Signature**:
```python
def get_icd10cm_codes(self, concept_id: int) -> List[str]:
    """
    Get ICD-10CM codes for a SNOMED concept using OHDSI concept_relationship.

    Args:
        concept_id: OMOP concept identifier (typically SNOMED)

    Returns:
        List of ICD-10CM codes (may be empty if no mapping exists)

    Example:
        >>> icd_codes = client.get_icd10cm_codes(4216914)  # SNOMED: 30-day mortality
        >>> icd_codes
        ['R99']  # ICD-10CM: Ill-defined cause of mortality
    """
```

**Implementation Strategy**:
1. **Primary**: Query `concept_relationship` for related concepts
2. **Fallback**: Use `get_vocabulary_codes()` with ICD10CM filter
3. **Caching**: Leverages existing rate-limiting and retry logic

### 2. CDMMapper Integration

**File**: `src/pipeline/cdm_mapper.py`

Modified `apply_results_to_entities()` method to:
- Automatically fetch ICD-10CM codes for SNOMED concepts
- Store codes in `entity.metadata["icd10cm_codes"]`
- Handle errors gracefully with warning logs

**Changes**:
```python
if concept:
    # Fetch ICD-10CM codes for SNOMED concepts
    icd10cm_codes = []
    if concept.vocabulary_id == "SNOMED":
        try:
            icd10cm_codes = self.ohdsi_client.get_icd10cm_codes(concept.concept_id)
        except Exception as e:
            logger.warning(f"Failed to fetch ICD-10CM codes for concept {concept.concept_id}: {e}")

    # Prepare metadata with ICD-10CM codes
    metadata = {
        **(entity.metadata or {}),
        "omop_concept_id": concept.concept_id,
        "omop_domain": concept.domain_id,
        "omop_class": concept.concept_class_id,
        "mapping_method": result.method,
        "mapping_confidence": result.confidence
    }

    # Add ICD-10CM codes to metadata if found
    if icd10cm_codes:
        metadata["icd10cm_codes"] = icd10cm_codes
```

### 3. Entity Data Structure

**File**: `src/pipeline/trialist_models.py`

The `EnhancedNamedEntity` class already has a flexible `metadata` field:
```python
@dataclass(frozen=True)
class EnhancedNamedEntity:
    """Enhanced named entity with domain classification and standardization."""
    # ... other fields ...

    # CDM mapping fields (Stage 3)
    code_system: str | None = None  # e.g., "SNOMED"
    code_set: Sequence[str] | None = None
    primary_code: str | None = None  # e.g., "419620001"

    metadata: Mapping[str, Any] | None = None  # Contains "icd10cm_codes": ["R99"]
```

**ICD-10CM codes location**:
```python
entity.metadata["icd10cm_codes"]  # List[str], e.g., ["R99", "I46.9"]
```

## Usage

### Automatic in Trialist Pipeline

ICD-10CM mapping happens automatically in Stage 3 (CDM Mapping):

```python
# Run full Trialist pipeline
parser = TrialistParser()
result = parser.run(context)

# Access ICD-10CM codes
for criterion in result.criteria:
    if criterion.entities:
        for entity in criterion.entities:
            if entity.metadata and "icd10cm_codes" in entity.metadata:
                icd_codes = entity.metadata["icd10cm_codes"]
                print(f"{entity.text} → ICD-10CM: {', '.join(icd_codes)}")
```

### Direct API Usage

```python
from pipeline.clients.ohdsi_client import OHDSIClient

client = OHDSIClient()

# Get ICD-10CM codes for a SNOMED concept
concept_id = 4306655  # SNOMED: Death
icd_codes = client.get_icd10cm_codes(concept_id)
print(f"ICD-10CM codes: {icd_codes}")  # ['R99'] or []
```

## Testing

### Unit Tests

**File**: `test_icd10_direct.py`
- Tests `get_icd10cm_codes()` with known SNOMED concept IDs
- Validates API integration and error handling

**File**: `test_icd10_with_vocabulary_adapter.py`
- Tests with Local Vocabulary system
- Validates concept search → ICD-10CM mapping flow

### Integration Tests

**File**: `test_icd10_end_to_end.py`
- Full Trialist pipeline with NCT03389555
- Validates ICD-10CM codes in entity metadata
- Tests mortality outcome filtering + ICD-10CM mapping

### Test Results

```bash
# Run unit tests
./venv/bin/python test_icd10_direct.py

# Run with Local Vocabulary
./venv/bin/python test_icd10_with_vocabulary_adapter.py

# Run end-to-end test
./venv/bin/python test_icd10_end_to_end.py
```

**Expected Output**:
```
✅ SUCCESS: ICD-10CM mapping implementation is working!
   2/4 concepts successfully mapped to ICD-10CM
```

## Limitations

### 1. OHDSI API Coverage

Not all SNOMED concepts have ICD-10CM mappings in OHDSI:
- Research-focused concepts may lack clinical codes
- Some mappings are one-to-many or many-to-one
- Deprecated concepts may have no mappings

### 2. Vocabulary Scope

ICD-10CM mapping only applies to:
- ✅ SNOMED CT concepts
- ❌ TEO (Time Event Ontology) concepts
- ❌ Already ICD-10CM concepts (self-mapping)
- ❌ RxNorm drug concepts (use RxCUI instead)

### 3. API Performance

- OHDSI API can be slow (5-15s per request)
- Rate limiting: 20 requests/second (default)
- Timeout: 15s per request
- Max retries: 3 attempts

## Future Enhancements

### 1. Batch ICD-10CM Mapping

Optimize parallel concept lookups:
```python
def batch_get_icd10cm_codes(
    self,
    concept_ids: List[int]
) -> Dict[int, List[str]]:
    """Get ICD-10CM codes for multiple concepts in parallel."""
```

### 2. Local ICD-10CM Cache

Store SNOMED → ICD-10CM mappings locally:
```
data/vocabularies/concept_relationship_icd10cm.parquet
```

### 3. Alternative Vocabularies

Support other clinical coding systems:
- `get_icd9cm_codes()` - Legacy ICD-9 codes
- `get_cpt_codes()` - Procedure codes
- `get_loinc_codes()` - Lab test codes

### 4. Mapping Confidence Scores

Add quality metrics:
```python
{
    "icd10cm_codes": ["R99"],
    "icd10cm_confidence": 0.95,  # Mapping quality
    "icd10cm_is_approximate": False  # Exact vs approximate
}
```

## References

- **OHDSI WebAPI Docs**: http://webapidoc.ohdsi.org/
- **OMOP CDM**: https://ohdsi.github.io/CommonDataModel/
- **ICD-10CM**: https://www.cdc.gov/nchs/icd/icd-10-cm.htm
- **SNOMED CT**: https://www.snomed.org/

## Related Documents

- [Mortality Filtering Summary](../todolist/20251014_211500_filter_mortality_outcomes.md)
- [CDM Mapping Guide](../docs/cdm-mapping/README.md)
- [OHDSI Client API](../src/pipeline/clients/ohdsi_client.py)
- [Trialist Models](../src/pipeline/trialist_models.py)
