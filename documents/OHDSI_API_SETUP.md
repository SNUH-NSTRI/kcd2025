# OHDSI Athena API Setup Guide

## Overview

The OHDSI (Observational Health Data Sciences and Informatics) Athena vocabulary provides standardized medical vocabularies using the OMOP Common Data Model (CDM). Our platform uses OHDSI WebAPI for mapping UMLS concepts to standard OMOP concept IDs and vocabulary codes (SNOMED CT, ICD-10, RxNorm, LOINC).

## Prerequisites

- Internet connection
- UMLS API already configured (see `UMLS_API_SETUP.md`)
- Basic understanding of OMOP CDM concepts

## Step 1: Understanding OHDSI Athena

### What is OHDSI Athena?
- **Public vocabulary browser** for OMOP CDM standard vocabularies
- **No API key required** for basic searches
- Provides standardized medical codes across different systems

### Key Concepts
- **Concept**: A clinical entity (e.g., disease, drug, procedure)
- **Concept ID**: Unique integer identifier in OMOP CDM
- **Vocabulary**: Source terminology (e.g., SNOMED CT, ICD-10-CM, RxNorm)
- **Domain**: Clinical category (Condition, Drug, Measurement, etc.)
- **Standard Concept**: Preferred terminology for data harmonization

## Step 2: Configure Environment Variables

1. **Locate `.env` File**
   ```bash
   cd /path/to/datathon
   ```

2. **Add OHDSI Configuration**
   Open `.env` file and add:
   ```bash
   # OHDSI Athena API Configuration
   OHDSI_ENDPOINT=https://athena.ohdsi.org/api/v1

   # Standardization Mode (if not already set)
   STANDARDIZATION_MODE=api
   ```

## Step 3: Test API Connection

1. **Run Validation Script**
   ```bash
   python -c "
   from src.pipeline.clients.ohdsi_client import OHDSIClient
   import os
   from dotenv import load_dotenv

   load_dotenv()

   client = OHDSIClient()

   # Test search
   concepts = client.search_concept('myocardial infarction', vocabulary='SNOMED')
   print(f'✅ Found {len(concepts)} concepts for \"myocardial infarction\"')

   if concepts:
       concept = concepts[0]
       print(f'   - Concept ID: {concept.concept_id}')
       print(f'   - Name: {concept.concept_name}')
       print(f'   - Code: {concept.concept_code}')
       print(f'   - Vocabulary: {concept.vocabulary_id}')
       print(f'   - Domain: {concept.domain_id}')
       print(f'   - Standard: {concept.standard_concept}')
   "
   ```

2. **Expected Output**
   ```
   ✅ Found 15 concepts for "myocardial infarction"
      - Concept ID: 312327
      - Name: Myocardial infarction
      - Code: 22298006
      - Vocabulary: SNOMED
      - Domain: Condition
      - Standard: S
   ```

## API Usage

### No Rate Limits
- OHDSI Athena API is **publicly accessible** with no authentication
- Designed for high-volume research queries
- No API key required (unlike UMLS)

### Best Practices
1. **Use Standard Concepts**: Filter by `standard_concept='S'` when possible
2. **Cache Results**: The system caches OHDSI responses for 30 days
3. **Domain Filtering**: Specify domain to get more relevant results

## OMOP Vocabulary Mapping

### Domain → Vocabulary Mapping

Our system automatically maps entity domains to appropriate OMOP vocabularies:

| Domain | Primary Vocabularies | Use Cases |
|--------|---------------------|-----------|
| **Condition** | SNOMED, ICD-10-CM, ICD-9-CM | Diseases, symptoms, diagnoses |
| **Drug** | RxNorm, ATC, NDC | Medications, prescriptions |
| **Measurement** | LOINC, SNOMED | Lab tests, vital signs |
| **Procedure** | SNOMED, CPT-4, ICD-10-PCS | Surgeries, treatments |
| **Device** | SNOMED | Medical devices, implants |
| **Observation** | SNOMED, LOINC | Clinical observations |

### Standard vs. Non-Standard Concepts

- **Standard (S)**: Preferred concept for data harmonization
- **Classification (C)**: Grouping concept (e.g., ICD-10 chapters)
- **Non-standard**: Source codes mapped to standard concepts

Our system prioritizes **standard concepts** for consistency.

## Integration with UMLS

### Workflow
1. **UMLS Search** → Get CUI and preferred name
2. **OHDSI Mapping** → Find standard OMOP concept ID
3. **Code Retrieval** → Get vocabulary-specific codes (ICD-10, SNOMED, etc.)

### Example
```
User Input: "heart attack"

Step 1 (UMLS):
- CUI: C0027051
- Preferred Name: Myocardial infarction

Step 2 (OHDSI):
- Concept ID: 312327
- Standard Concept: Yes
- Vocabulary: SNOMED

Step 3 (Vocabulary Codes):
- SNOMED: 22298006
- ICD-10-CM: I21.9
- ICD-9-CM: 410.9
```

## API Endpoints Used

Our implementation uses these OHDSI Athena API endpoints:

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `/v1/concepts` | Search concepts | Search for "diabetes" |
| `/v1/concepts/{id}` | Get concept details | Get details for concept 201826 |
| `/v1/concepts/{id}/relationships` | Get related concepts | Get "Maps to" relationships |

## Troubleshooting

### Error: "Connection refused" or "Timeout"
**Cause**: Network issues or API unavailable

**Solution**:
1. Check internet connection
2. Verify https://athena.ohdsi.org is accessible in browser
3. Check firewall/proxy settings
4. Increase timeout:
   ```python
   client = OHDSIClient(timeout=15)  # 15 seconds
   ```

### Error: "No standard concept found"
**Cause**: Concept exists but is not a standard concept

**Solution**:
- Check "Maps to" relationships for equivalent standard concept
- Try alternative search terms
- Search by CUI if available from UMLS

### Empty Search Results
**Cause**: Term not found or incorrect vocabulary

**Solutions**:
1. **Try broader search**:
   ```python
   concepts = client.search_concept("MI")  # Too ambiguous
   concepts = client.search_concept("myocardial infarction")  # Better
   ```

2. **Remove vocabulary filter**:
   ```python
   concepts = client.search_concept("hypertension")  # Search all vocabularies
   ```

3. **Check alternative spellings**:
   - "myocardial infarction" vs. "heart attack"
   - "diabetes mellitus" vs. "diabetes"

### Error: "No module named 'requests'"
**Cause**: Missing dependencies

**Solution**:
```bash
pip install -r requirements-api.txt
```

## Advanced Usage

### Search with Multiple Parameters
```python
from src.pipeline.clients.ohdsi_client import OHDSIClient

client = OHDSIClient()

concepts = client.search_concept(
    term="diabetes",
    vocabulary="SNOMED",
    domain="Condition",
    standard_only=True,
    page_size=10
)
```

### Get Concept Relationships
```python
# Find equivalent codes in different vocabularies
relationships = client.get_concept_relationships(
    concept_id=201826,  # Diabetes mellitus
    relationship_types=["Maps to", "Mapped from"]
)
```

### Get Vocabulary Codes
```python
# Get codes across multiple vocabularies
vocab_codes = client.get_vocabulary_codes(
    concept_id=312327,  # Myocardial infarction
    target_vocabularies=["ICD10CM", "ICD9CM", "SNOMED"]
)

print(vocab_codes)
# Output: {'ICD10CM': 'I21.9', 'ICD9CM': '410.9', 'SNOMED': '22298006'}
```

## Understanding OMOP CDM

### Concept Attributes

```python
concept = client.get_concept_by_id(312327)

# Concept attributes:
# - concept_id: 312327 (unique integer)
# - concept_name: "Myocardial infarction"
# - domain_id: "Condition" (clinical category)
# - vocabulary_id: "SNOMED" (source terminology)
# - concept_class_id: "Clinical Finding" (concept type)
# - standard_concept: "S" (is standard)
# - concept_code: "22298006" (source code)
# - valid_start_date: "1970-01-01"
# - valid_end_date: "2099-12-31"
# - invalid_reason: None (still valid)
```

### Domains
- **Condition**: Diseases, disorders, syndromes
- **Drug**: Medications, ingredients, combinations
- **Measurement**: Lab results, vital signs
- **Procedure**: Surgeries, interventions
- **Device**: Implants, medical equipment
- **Observation**: Clinical facts, social history
- **Visit**: Encounter types
- **Specimen**: Biological samples

### Concept Classes
- **Clinical Finding**: Symptoms, diagnoses (SNOMED)
- **Ingredient**: Drug active ingredients (RxNorm)
- **Lab Test**: Laboratory procedures (LOINC)
- **Procedure**: Medical procedures (CPT-4, ICD-10-PCS)

## Vocabulary Downloads

For offline usage or custom mapping, download vocabularies from:
- **Athena Portal**: https://athena.ohdsi.org/vocabulary/list
- Requires free OHDSI account
- Download full OMOP CDM vocabulary files

## Resources

- **OHDSI Home**: https://www.ohdsi.org/
- **Athena Vocabulary Browser**: https://athena.ohdsi.org/
- **OMOP CDM Documentation**: https://ohdsi.github.io/CommonDataModel/
- **WebAPI Documentation**: https://github.com/OHDSI/WebAPI
- **OHDSI Forums**: https://forums.ohdsi.org/

## Support

For OHDSI-specific issues:
- **Forums**: https://forums.ohdsi.org/
- **GitHub**: https://github.com/OHDSI/WebAPI/issues
- **Slack**: Join OHDSI Slack workspace

For RWE platform issues:
- Check platform documentation in `TRIALIST_README.md`
- Review logs in `workspace/*/logs/`
- Open GitHub issue with error details

## Comparison: UMLS vs. OHDSI

| Feature | UMLS | OHDSI Athena |
|---------|------|--------------|
| **API Key** | Required | Not required |
| **Coverage** | 200+ vocabularies | OMOP standard vocabularies |
| **Primary Use** | Concept search & CUIs | Standard concept IDs & codes |
| **Rate Limit** | 20 req/sec | No limit |
| **Best For** | Initial concept lookup | OMOP CDM mapping |
| **Cost** | Free (with registration) | Free |

**Recommended Workflow**: Use UMLS first for concept identification, then OHDSI for standard OMOP mapping.

---

**Last Updated**: 2025-10-14
**Version**: 1.0
