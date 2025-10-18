# 사용 예시 및 통합 가이드

## 🚀 기본 사용 예시

### Example 1: Simple Cohort Building

```python
from pathlib import Path
from src.pipeline.cohort_builder import CohortBuilder
from src.pipeline.vocabulary_adapter import VocabularyAdapter

# 1. Initialize
vocab_adapter = VocabularyAdapter("vocabulary/")
builder = CohortBuilder(
    data_root=Path("data/omop_cdm"),
    vocab_adapter=vocab_adapter
)

# 2. Load trial schema (from Trialist parser)
trial_schema = load_nct03389555_schema()

# 3. Build cohort
cohort, stats = builder.build_cohort(trial_schema)

# 4. Results
print(f"Initial population: {stats['initial_population']}")
print(f"Final cohort: {stats['final_cohort_size']}")
print(f"Inclusion rate: {stats['inclusion_rate']:.2%}")

# 5. Save
cohort.to_parquet("workspace/nct03389555/cohort/cohort.parquet")
```

---

### Example 2: NCT03389555 (MENDS2 Trial)

**Trial Description**: Dexmedetomidine vs. Propofol for ICU sedation

**Inclusion Criteria**:
1. Age >= 18 years
2. Mechanically ventilated in ICU
3. Expected ICU stay > 24 hours

**Exclusion Criteria**:
1. Pregnancy
2. Previous enrollment in study

```python
# Load trial schema
schema = EnhancedTrialSchema(
    inclusion=[
        EnhancedTrialCriterion(
            original="Age >= 18 years",
            entities=[
                EnhancedNamedEntity(
                    text="Age",
                    type="concept",
                    domain="Measurement",
                    omop_concept_id=3004,
                    operator=">=",
                    numeric_value=18,
                    unit="year"
                )
            ]
        ),
        EnhancedTrialCriterion(
            original="Mechanically ventilated",
            entities=[
                EnhancedNamedEntity(
                    text="mechanical ventilation",
                    type="concept",
                    domain="Procedure",
                    omop_concept_id=4230167
                )
            ]
        )
    ],
    exclusion=[
        EnhancedTrialCriterion(
            original="Pregnancy",
            entities=[
                EnhancedNamedEntity(
                    text="pregnancy",
                    type="concept",
                    domain="Condition",
                    omop_concept_id=4299535
                )
            ]
        )
    ]
)

# Build cohort
cohort, stats = builder.build_cohort(schema)

# Output
"""
Initial population: 10,000
After inclusion: 1,200 (12.0%)
  - Age >= 18: 9,500 → 9,500 (100.0%)
  - Mechanical ventilation: 9,500 → 1,200 (12.6%)
After exclusion: 1,180 (98.3%)
  - Pregnancy excluded: 20 (1.7%)
Final cohort: 1,180 patients
"""
```

---

### Example 3: Temporal Constraint

**Criterion**: "History of TBI within 3 months before ICU admission"

```python
criterion = EnhancedTrialCriterion(
    original="History of TBI within 3 months before ICU admission",
    entities=[
        # Concept: TBI
        EnhancedNamedEntity(
            text="traumatic brain injury",
            type="concept",
            domain="Condition",
            omop_concept_id=12345,
            standard_name="Traumatic Brain Injury"
        ),
        # Temporal: within 3 months before
        EnhancedNamedEntity(
            text="within 3 months before",
            type="temporal",
            temporal_pattern="XBeforeYwithTime",
            iso_duration="P3M",
            reference_point="icu_admission"
        )
    ]
)

# Translate to FilterCondition
translator = CriterionTranslator(vocab_adapter)
condition = translator.translate(criterion)

print(condition)
"""
FilterCondition(
    domain='Condition',
    concept_ids=[12345],
    temporal=TemporalCondition(
        pattern='XBeforeYwithTime',
        anchor_event='icu_admission',
        window=Timedelta('90 days 00:00:00'),
        direction='before'
    ),
    value=None
)
"""

# Apply filter
cohort_filter = PandasCohortFilter(data_root)
filtered_cohort = cohort_filter.filter_by_condition(condition, initial_cohort)
```

---

### Example 4: Value Constraint

**Criterion**: "eGFR between 30 and 60 mL/min/1.73m²"

```python
criterion = EnhancedTrialCriterion(
    original="eGFR between 30 and 60 mL/min/1.73m²",
    entities=[
        EnhancedNamedEntity(
            text="eGFR",
            type="concept",
            domain="Measurement",
            omop_concept_id=3049187,
            operator="between",
            value_range=(30, 60),
            unit="mL/min/1.73m2"
        )
    ]
)

# Translate
condition = translator.translate(criterion)

print(condition)
"""
FilterCondition(
    domain='Measurement',
    concept_ids=[3049187],
    temporal=None,
    value=ValueCondition(
        operator='between',
        value=(30, 60),
        unit='mL/min/1.73m2'
    )
)
"""

# Apply filter
filtered_cohort = cohort_filter.filter_by_measurement(condition, initial_cohort)
```

---

### Example 5: Combined Temporal + Value

**Criterion**: "eGFR < 60 within 30 days before enrollment"

```python
criterion = EnhancedTrialCriterion(
    original="eGFR < 60 within 30 days before enrollment",
    entities=[
        # Concept + Value
        EnhancedNamedEntity(
            text="eGFR",
            type="concept",
            domain="Measurement",
            omop_concept_id=3049187,
            operator="<",
            numeric_value=60,
            unit="mL/min/1.73m2"
        ),
        # Temporal
        EnhancedNamedEntity(
            text="within 30 days before",
            type="temporal",
            temporal_pattern="XBeforeYwithTime",
            iso_duration="P30D",
            reference_point="enrollment"
        )
    ]
)

# Results in both temporal AND value constraints
condition = translator.translate(criterion)
"""
FilterCondition(
    domain='Measurement',
    concept_ids=[3049187],
    temporal=TemporalCondition(
        pattern='XBeforeYwithTime',
        anchor_event='enrollment',
        window=Timedelta('30 days')
    ),
    value=ValueCondition(
        operator='<',
        value=60,
        unit='mL/min/1.73m2'
    )
)
"""
```

---

## 🔄 전체 Workflow 예시

### Complete Pipeline: Trialist → Cohort

```python
from src.pipeline.plugins.trialist_parser import TrialistParser
from src.pipeline.cohort_builder import CohortBuilder
from src.pipeline.vocabulary_adapter import VocabularyAdapter
from pathlib import Path

# ===== Step 1: NER + Standardization + CDM Mapping =====
# (Already implemented in Trialist pipeline)

# Parse trial from ClinicalTrials.gov
parser = TrialistParser(model_name="gpt-4o-mini", temperature=0.0)
corpus = load_trial_corpus("NCT03389555")
trial_schema = parser.run(params, ctx, corpus)

# trial_schema now has:
# - inclusion: List[EnhancedTrialCriterion]
# - exclusion: List[EnhancedTrialCriterion]
# - Each criterion has entities with omop_concept_id already mapped

# ===== Step 2: Build Cohort (NEW) =====

# Initialize cohort builder
vocab_adapter = VocabularyAdapter("vocabulary/")
builder = CohortBuilder(
    data_root=Path("data/omop_cdm"),
    vocab_adapter=vocab_adapter
)

# Build cohort
cohort, stats = builder.build_cohort(trial_schema)

# ===== Step 3: Results & Analysis =====

print(f"""
=== Cohort Building Results ===
Initial Population: {stats['initial_population']:,}
After Inclusion: {stats['after_inclusion']:,} ({stats['inclusion_rate']:.1%})
After Exclusion: {stats['after_exclusion']:,}
Final Cohort: {stats['final_cohort_size']:,}

Processing Time: {stats['processing_time_seconds']:.1f}s
Memory Peak: {stats['memory_peak_mb']:.0f} MB
""")

# Criteria breakdown
for criterion in stats['criteria_breakdown']:
    print(f"  {criterion['criterion_text']}")
    print(f"    Before: {criterion['patients_before']:,}")
    print(f"    After: {criterion['patients_after']:,}")
    print(f"    Pass rate: {criterion['pass_rate']:.1%}")

# Save cohort
cohort.to_parquet("workspace/nct03389555/cohort/cohort.parquet")

# Save statistics
import json
with open("workspace/nct03389555/cohort/stats.json", "w") as f:
    json.dump(stats, f, indent=2, default=str)
```

---

## 📊 Output 예시

### cohort.parquet
```python
pd.read_parquet("workspace/nct03389555/cohort/cohort.parquet")

   person_id  inclusion_date  cohort_start_date  age_at_inclusion  gender_concept_id
0      1001      2023-01-15         2023-01-15              65.3               8507
1      1002      2023-02-20         2023-02-20              72.1               8532
2      1003      2023-03-10         2023-03-10              58.9               8507
3      1004      2023-04-05         2023-04-05              61.2               8532
...
```

### stats.json
```json
{
  "initial_population": 10000,
  "after_inclusion": 1200,
  "after_exclusion": 980,
  "final_cohort_size": 980,
  "inclusion_rate": 0.12,
  "exclusion_rate": 0.183,
  "criteria_breakdown": [
    {
      "criterion_id": "INC-001",
      "criterion_text": "Age >= 18 years",
      "patients_before": 10000,
      "patients_after": 9500,
      "patients_excluded": 500,
      "pass_rate": 0.95
    },
    {
      "criterion_id": "INC-002",
      "criterion_text": "Mechanically ventilated in ICU",
      "patients_before": 9500,
      "patients_after": 3000,
      "patients_excluded": 6500,
      "pass_rate": 0.316
    },
    {
      "criterion_id": "INC-003",
      "criterion_text": "Expected ICU stay > 24 hours",
      "patients_before": 3000,
      "patients_after": 1200,
      "patients_excluded": 1800,
      "pass_rate": 0.40
    },
    {
      "criterion_id": "EXC-001",
      "criterion_text": "Pregnancy",
      "patients_before": 1200,
      "patients_excluded": 120,
      "pass_rate": 0.10
    },
    {
      "criterion_id": "EXC-002",
      "criterion_text": "Previous enrollment",
      "patients_before": 1200,
      "patients_excluded": 100,
      "pass_rate": 0.083
    }
  ],
  "processing_time_seconds": 45.3,
  "memory_peak_mb": 2048.5
}
```

---

## 🧪 테스트 예시

### Unit Test: CriterionTranslator

```python
def test_translate_simple_condition():
    """Test simple condition translation"""
    translator = CriterionTranslator(vocab_adapter)

    criterion = EnhancedTrialCriterion(
        original="Age >= 18 years",
        entities=[
            EnhancedNamedEntity(
                text="Age",
                type="concept",
                domain="Measurement",
                omop_concept_id=3004,
                operator=">=",
                numeric_value=18,
                unit="year"
            )
        ]
    )

    condition = translator.translate(criterion)

    assert condition.domain == "Measurement"
    assert 3004 in condition.concept_ids
    assert condition.value.operator == ">="
    assert condition.value.value == 18
    assert condition.temporal is None
```

### Integration Test: Full Cohort Build

```python
def test_nct03389555_cohort_build():
    """Test NCT03389555 cohort building"""
    # Load schema
    schema = load_nct03389555_schema()

    # Build cohort
    builder = CohortBuilder(data_root, vocab_adapter)
    cohort, stats = builder.build_cohort(schema)

    # Assertions
    assert len(cohort) > 0
    assert stats['initial_population'] > stats['after_inclusion']
    assert stats['after_inclusion'] >= stats['after_exclusion']
    assert stats['inclusion_rate'] > 0
    assert stats['inclusion_rate'] <= 1.0

    # Verify cohort structure
    assert 'person_id' in cohort.columns
    assert 'inclusion_date' in cohort.columns
    assert cohort['person_id'].is_unique
```

---

## 🔧 디버깅 예시

### Debug Mode: Step-by-Step

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Build with verbose output
builder = CohortBuilder(data_root, vocab_adapter, verbose=True)

# This will print:
# - Each criterion being processed
# - Cohort size before/after each step
# - SQL-like explanation of filters
# - Timing for each operation
cohort, stats = builder.build_cohort(schema)

"""
Output:
[DEBUG] Loading initial population...
[DEBUG] Initial cohort: 10,000 patients
[DEBUG] Applying inclusion criterion 1/3: Age >= 18 years
[DEBUG]   Domain: Measurement, Concepts: [3004]
[DEBUG]   Value constraint: >= 18
[DEBUG]   Cohort: 10,000 → 9,500 (95.0%)
[DEBUG]   Elapsed: 1.2s
[DEBUG] Applying inclusion criterion 2/3: Mechanical ventilation
[DEBUG]   Domain: Procedure, Concepts: [4230167]
[DEBUG]   Cohort: 9,500 → 1,200 (12.6%)
[DEBUG]   Elapsed: 2.5s
...
"""
```

---

## 📋 CohortBuilder 구현

```python
class CohortBuilder:
    """엔드-투-엔드 코호트 빌더"""

    def __init__(
        self,
        data_root: Path,
        vocab_adapter: VocabularyAdapter,
        verbose: bool = False
    ):
        self.filter = PandasCohortFilter(data_root)
        self.translator = CriterionTranslator(vocab_adapter)
        self.verbose = verbose

    def build_cohort(
        self,
        trial_schema: EnhancedTrialSchema
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Build cohort from trial schema

        Returns:
            (cohort_df, statistics)
        """
        start_time = time.time()

        # 1. Load initial population
        cohort = self._load_initial_population()
        initial_count = len(cohort)
        if self.verbose:
            print(f"Initial population: {initial_count:,}")

        # 2. Translate criteria
        inclusion_conditions = [
            self.translator.translate(c)
            for c in trial_schema.inclusion
        ]
        exclusion_conditions = [
            self.translator.translate(c)
            for c in trial_schema.exclusion
        ]

        # 3. Apply inclusion
        criteria_stats = []
        cohort = self.filter.apply_inclusion_criteria(
            inclusion_conditions,
            cohort
        )
        after_inclusion = len(cohort)
        if self.verbose:
            print(f"After inclusion: {after_inclusion:,} ({after_inclusion/initial_count:.1%})")

        # 4. Apply exclusion
        cohort = self.filter.apply_exclusion_criteria(
            exclusion_conditions,
            cohort
        )
        final_count = len(cohort)
        if self.verbose:
            print(f"Final cohort: {final_count:,}")

        # 5. Generate statistics
        elapsed = time.time() - start_time
        stats = {
            'initial_population': initial_count,
            'after_inclusion': after_inclusion,
            'after_exclusion': final_count,
            'final_cohort_size': final_count,
            'inclusion_rate': after_inclusion / initial_count if initial_count > 0 else 0,
            'exclusion_rate': (after_inclusion - final_count) / after_inclusion if after_inclusion > 0 else 0,
            'criteria_breakdown': criteria_stats,
            'processing_time_seconds': elapsed,
            'memory_peak_mb': self._get_memory_usage()
        }

        return cohort, stats

    def _load_initial_population(self) -> pd.DataFrame:
        """Load initial population (all patients)"""
        person_df = self.filter.load_table("person")
        return person_df[['person_id']].copy()

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
```

---

**다음 문서**: [06-testing-strategy.md](06-testing-strategy.md)
