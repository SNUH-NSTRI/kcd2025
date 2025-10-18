# 데이터 구조 정의

## 📦 Core Data Classes

### FilterCondition
**목적**: Criterion을 Pandas 실행 가능한 조건으로 변환한 결과

```python
@dataclass
class FilterCondition:
    """Pandas 필터링 조건"""
    domain: str                          # "Condition", "Drug", "Measurement", "Procedure"
    concept_ids: List[int]               # OMOP concept IDs
    temporal: Optional[TemporalCondition] = None
    value: Optional[ValueCondition] = None
    logical_operator: str = "AND"        # "AND", "OR" for compound conditions
```

**예시**:
```python
# Simple condition: "History of diabetes"
FilterCondition(
    domain="Condition",
    concept_ids=[201826, 201254],  # Diabetes mellitus concepts
    temporal=None,
    value=None
)

# Complex condition: "eGFR < 60 within 30 days before enrollment"
FilterCondition(
    domain="Measurement",
    concept_ids=[3049187],  # eGFR concept
    temporal=TemporalCondition(
        pattern="XBeforeYwithTime",
        anchor_event="enrollment",
        window=pd.Timedelta(days=30)
    ),
    value=ValueCondition(
        operator="<",
        value=60,
        unit="mL/min/1.73m2"
    )
)
```

---

### TemporalCondition
**목적**: 시간 제약 정의

```python
@dataclass
class TemporalCondition:
    """시간 제약 조건"""
    pattern: str                         # Temporal pattern type
    anchor_event: str                    # Reference event name
    window: pd.Timedelta                 # Time window
    direction: str = "before"            # "before", "after", "during"
```

**지원 Temporal 패턴**:
| 패턴 | 설명 | 예시 |
|------|------|------|
| `XBeforeY` | X가 Y 이전 | "TBI before ICU admission" |
| `XAfterY` | X가 Y 이후 | "Follow-up after discharge" |
| `XBeforeYwithTime` | X가 Y 이전 N일 이내 | "TBI within 3 months before ICU" |
| `XAfterYwithTime` | X가 Y 이후 N일 이내 | "Lab within 24h after admission" |
| `XWithinTime` | X가 Y 전후 N일 이내 | "Measurement within ±7 days" |
| `XDuringY` | X가 Y 기간 중 | "Event during hospitalization" |

**예시**:
```python
# "History of TBI within 3 months before ICU admission"
TemporalCondition(
    pattern="XBeforeYwithTime",
    anchor_event="icu_admission",
    window=pd.Timedelta(days=90),
    direction="before"
)

# "Lab measurement within 24 hours after enrollment"
TemporalCondition(
    pattern="XAfterYwithTime",
    anchor_event="enrollment",
    window=pd.Timedelta(hours=24),
    direction="after"
)
```

---

### ValueCondition
**목적**: 값 비교 조건 정의

```python
@dataclass
class ValueCondition:
    """값 비교 조건"""
    operator: str                        # ">=", "<=", ">", "<", "=", "between"
    value: Union[float, Tuple[float, float]]
    unit: str
    unit_conversion: Optional[Dict[str, float]] = None
```

**지원 연산자**:
```python
OPERATORS = {
    ">=": "Greater than or equal",
    "<=": "Less than or equal",
    ">": "Greater than",
    "<": "Less than",
    "=": "Equal",
    "between": "Between two values"
}
```

**예시**:
```python
# "Age >= 18 years"
ValueCondition(
    operator=">=",
    value=18,
    unit="year"
)

# "eGFR between 30 and 60 mL/min/1.73m²"
ValueCondition(
    operator="between",
    value=(30, 60),
    unit="mL/min/1.73m2"
)

# "BMI < 30 kg/m²"
ValueCondition(
    operator="<",
    value=30,
    unit="kg/m2"
)
```

---

## 🗃️ OMOP CDM Table Schemas

### person.parquet
```python
{
    'person_id': int64,              # Primary key
    'gender_concept_id': int64,      # FK to CONCEPT
    'year_of_birth': int64,
    'month_of_birth': int64,
    'day_of_birth': int64,
    'birth_datetime': datetime64,
    'race_concept_id': int64,
    'ethnicity_concept_id': int64
}
```

### condition_occurrence.parquet
```python
{
    'condition_occurrence_id': int64,  # Primary key
    'person_id': int64,                # FK to PERSON
    'condition_concept_id': int64,     # FK to CONCEPT
    'condition_start_date': datetime64,
    'condition_start_datetime': datetime64,
    'condition_end_date': datetime64,
    'condition_end_datetime': datetime64,
    'condition_type_concept_id': int64,
    'visit_occurrence_id': int64       # FK to VISIT_OCCURRENCE
}
```

### drug_exposure.parquet
```python
{
    'drug_exposure_id': int64,         # Primary key
    'person_id': int64,                # FK to PERSON
    'drug_concept_id': int64,          # FK to CONCEPT
    'drug_exposure_start_date': datetime64,
    'drug_exposure_start_datetime': datetime64,
    'drug_exposure_end_date': datetime64,
    'drug_exposure_end_datetime': datetime64,
    'drug_type_concept_id': int64,
    'quantity': float64,
    'visit_occurrence_id': int64
}
```

### measurement.parquet
```python
{
    'measurement_id': int64,           # Primary key
    'person_id': int64,                # FK to PERSON
    'measurement_concept_id': int64,   # FK to CONCEPT
    'measurement_date': datetime64,
    'measurement_datetime': datetime64,
    'measurement_type_concept_id': int64,
    'value_as_number': float64,        # Numeric value
    'value_as_concept_id': int64,      # Categorical value
    'unit_concept_id': int64,          # FK to CONCEPT
    'range_low': float64,
    'range_high': float64,
    'visit_occurrence_id': int64
}
```

### procedure_occurrence.parquet
```python
{
    'procedure_occurrence_id': int64,  # Primary key
    'person_id': int64,                # FK to PERSON
    'procedure_concept_id': int64,     # FK to CONCEPT
    'procedure_date': datetime64,
    'procedure_datetime': datetime64,
    'procedure_type_concept_id': int64,
    'quantity': int64,
    'visit_occurrence_id': int64
}
```

### visit_occurrence.parquet
```python
{
    'visit_occurrence_id': int64,      # Primary key
    'person_id': int64,                # FK to PERSON
    'visit_concept_id': int64,         # FK to CONCEPT
    'visit_start_date': datetime64,
    'visit_start_datetime': datetime64,
    'visit_end_date': datetime64,
    'visit_end_datetime': datetime64,
    'visit_type_concept_id': int64,
    'care_site_id': int64,
    'admitted_from_concept_id': int64,
    'discharged_to_concept_id': int64
}
```

---

## 📊 Output Data Structures

### Cohort DataFrame
```python
pd.DataFrame({
    'person_id': int64,                # Patient identifier
    'inclusion_date': datetime64,      # Date when patient met inclusion criteria
    'cohort_start_date': datetime64,   # Study start date for this patient
    'cohort_end_date': datetime64,     # Study end date for this patient
    'age_at_inclusion': float64,       # Age when included
    'gender_concept_id': int64,        # Gender
    'race_concept_id': int64,          # Race
    'criteria_met': str                # JSON of which criteria were met
})
```

**예시**:
```python
   person_id  inclusion_date  cohort_start_date  age_at_inclusion  gender_concept_id
0      1001      2023-01-15         2023-01-15              65.3               8507
1      1002      2023-02-20         2023-02-20              72.1               8532
2      1003      2023-03-10         2023-03-10              58.9               8507
```

---

### CohortStatistics
```python
@dataclass
class CohortStatistics:
    """코호트 생성 통계"""
    initial_population: int
    after_inclusion: int
    after_exclusion: int
    final_cohort_size: int
    inclusion_rate: float
    exclusion_rate: float

    criteria_breakdown: List[CriterionStats]
    processing_time_seconds: float
    memory_peak_mb: float
```

**CriterionStats**:
```python
@dataclass
class CriterionStats:
    """개별 Criterion 통계"""
    criterion_id: str
    criterion_text: str
    patients_before: int
    patients_after: int
    patients_excluded: int
    pass_rate: float
```

**예시 JSON 출력**:
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
      "pass_rate": 0.95
    },
    {
      "criterion_id": "INC-002",
      "criterion_text": "ICU admission",
      "patients_before": 9500,
      "patients_after": 3000,
      "pass_rate": 0.316
    },
    {
      "criterion_id": "EXC-001",
      "criterion_text": "Pregnancy",
      "patients_before": 1200,
      "patients_excluded": 120,
      "pass_rate": 0.10
    }
  ],
  "processing_time_seconds": 45.3,
  "memory_peak_mb": 2048
}
```

---

## 🔄 Data Transformation Pipeline

### Stage 1: Trial Schema → FilterConditions
```python
# Input: EnhancedTrialCriterion
criterion = EnhancedTrialCriterion(
    original="Age >= 18 years",
    entities=[
        EnhancedNamedEntity(
            text="Age",
            domain="Measurement",
            omop_concept_id=3004,
            operator=">=",
            numeric_value=18,
            unit="year"
        )
    ]
)

# Output: FilterCondition
condition = FilterCondition(
    domain="Measurement",
    concept_ids=[3004],
    value=ValueCondition(operator=">=", value=18, unit="year")
)
```

### Stage 2: FilterConditions → Pandas Filters
```python
# Input: FilterCondition
condition = FilterCondition(
    domain="Condition",
    concept_ids=[201826, 201254],
    temporal=TemporalCondition(
        pattern="XBeforeYwithTime",
        anchor_event="icu_admission",
        window=pd.Timedelta(days=90)
    )
)

# Output: Filtered DataFrame
condition_df = pd.read_parquet("condition_occurrence.parquet")
filtered = condition_df[
    condition_df['condition_concept_id'].isin([201826, 201254]) &
    (condition_df['condition_start_date'] >= anchor_date - pd.Timedelta(days=90)) &
    (condition_df['condition_start_date'] <= anchor_date)
]
```

### Stage 3: Filtered DataFrames → Cohort
```python
# Input: Multiple filtered DataFrames
inclusion_results = [df1, df2, df3]  # From each inclusion criterion

# Output: Final cohort (intersection of all)
cohort_person_ids = set(df1['person_id'])
for df in inclusion_results[1:]:
    cohort_person_ids &= set(df['person_id'])

cohort = person_df[person_df['person_id'].isin(cohort_person_ids)]
```

---

## 💾 File Formats

### Input: OMOP CDM Parquet Files
**Why Parquet?**
- ✅ Columnar format → Fast column-wise reading
- ✅ Compression → Space efficient
- ✅ Schema included → Type safety
- ✅ Pandas native support

**Storage Example**:
```
data/omop_cdm/
├── person.parquet           (500 KB for 10,000 patients)
├── condition_occurrence.parquet  (50 MB for 1M records)
├── drug_exposure.parquet    (40 MB for 800K records)
└── measurement.parquet      (100 MB for 2M records)
```

### Output: Cohort Parquet + JSON Stats
```
workspace/nct03389555/cohort/
├── cohort.parquet           # Final cohort DataFrame
├── stats.json               # CohortStatistics
└── criteria_details.json    # Detailed breakdown
```

---

**다음 문서**: [04-implementation-modules.md](04-implementation-modules.md)
