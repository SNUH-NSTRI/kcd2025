# 시스템 아키텍처

## 🏗️ 전체 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│           Trialist Pipeline (이미 구현됨)                │
├─────────────────────────────────────────────────────────┤
│ NER → Standardization → CDM Mapping                     │
│ (TrialistParser + CDMMapper + VocabularyAdapter)        │
└───────────────────────┬─────────────────────────────────┘
                        │ EnhancedTrialSchema
                        ↓
┌─────────────────────────────────────────────────────────┐
│        Pandas Cohort Filter (신규 구현)                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────┐          │
│  │  1. CriterionTranslator                  │          │
│  │     - EnhancedTrialCriterion →           │          │
│  │       Pandas filter conditions           │          │
│  └──────────────────────────────────────────┘          │
│                   ↓                                      │
│  ┌──────────────────────────────────────────┐          │
│  │  2. PandasCohortFilter (Core Engine)     │          │
│  │     - OMOP CDM 테이블 로드               │          │
│  │     - Domain별 필터링                     │          │
│  │     - Inclusion/Exclusion 로직            │          │
│  └──────────────────────────────────────────┘          │
│                   ↓                                      │
│  ┌─────────────┬────────────┬──────────────┐           │
│  │ Temporal    │ Value      │ Domain       │           │
│  │ Filter      │ Filter     │ Filters      │           │
│  └─────────────┴────────────┴──────────────┘           │
│                   ↓                                      │
│  ┌──────────────────────────────────────────┐          │
│  │  3. CohortBuilder (Integration)          │          │
│  │     - 전체 workflow 조율                  │          │
│  │     - 통계 생성                           │          │
│  │     - 결과 저장                           │          │
│  └──────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────┘
                        │ Cohort DataFrame
                        ↓
┌─────────────────────────────────────────────────────────┐
│              Cohort Analysis / Export                    │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 모듈 간 데이터 흐름

### 1. CriterionTranslator → PandasCohortFilter

**입력**: EnhancedTrialCriterion
```python
EnhancedTrialCriterion(
    original="History of TBI within 3 months before ICU admission",
    entities=[
        EnhancedNamedEntity(
            text="traumatic brain injury",
            domain="Condition",
            omop_concept_id=12345
        ),
        EnhancedNamedEntity(
            text="within 3 months before",
            type="temporal",
            temporal_pattern="XBeforeYwithTime",
            iso_duration="P3M"
        )
    ]
)
```

**출력**: FilterCondition
```python
FilterCondition(
    domain="Condition",
    concept_ids=[12345, 67890],
    temporal=TemporalCondition(
        pattern="XBeforeYwithTime",
        anchor_event="icu_admission",
        window=pd.Timedelta(days=90)
    ),
    value=None
)
```

### 2. PandasCohortFilter → TemporalFilter

**입력**: DataFrame + TemporalCondition
```python
# condition_df
   person_id  condition_concept_id  condition_start_date
0      1001                 12345            2023-01-15
1      1002                 12345            2023-06-20

# temporal_condition
TemporalCondition(
    pattern="XBeforeYwithTime",
    anchor_event="icu_admission",
    window=pd.Timedelta(days=90)
)
```

**출력**: Filtered DataFrame
```python
# Only rows where condition_start_date is within 90 days before ICU admission
   person_id  condition_concept_id  condition_start_date
0      1001                 12345            2023-01-15
```

### 3. PandasCohortFilter → ValueFilter

**입력**: DataFrame + ValueCondition
```python
# measurement_df
   person_id  measurement_concept_id  value_as_number
0      1001                   3004               65
1      1002                   3004               45
2      1003                   3004               25

# value_condition
ValueCondition(
    operator=">=",
    value=18,
    unit="year"
)
```

**출력**: Filtered DataFrame
```python
# Only rows where value >= 18
   person_id  measurement_concept_id  value_as_number
0      1001                   3004               65
1      1002                   3004               45
2      1003                   3004               25
```

---

## 🔄 CohortBuilder Workflow

```
┌─────────────────────────────────────────┐
│  1. Load Initial Population             │
│     - Load person.parquet                │
│     - All patients in database           │
└───────────────┬─────────────────────────┘
                │ initial_cohort (10,000 patients)
                ↓
┌─────────────────────────────────────────┐
│  2. Translate Criteria                   │
│     - Inclusion → FilterConditions       │
│     - Exclusion → FilterConditions       │
└───────────────┬─────────────────────────┘
                │ inclusion_conditions [3]
                │ exclusion_conditions [2]
                ↓
┌───────────────────────────────────────���─┐
│  3. Apply Inclusion Criteria (AND)       │
│     ┌──────────────────────────────┐    │
│     │ Criterion 1: Age >= 18       │    │
│     │   10,000 → 9,500             │    │
│     └──────────────────────────────┘    │
│     ┌──────────────────────────────┐    │
│     │ Criterion 2: ICU admission   │    │
│     │   9,500 → 3,000              │    │
│     └──────────────────────────────┘    │
│     ┌──────────────────────────────┐    │
│     │ Criterion 3: Mech. vent.     │    │
│     │   3,000 → 1,200              │    │
│     └──────────────────────────────┘    │
└───────────────┬─────────────────────────┘
                │ after_inclusion (1,200 patients)
                ↓
┌─────────────────────────────────────────┐
│  4. Apply Exclusion Criteria (NOT)       │
│     ┌──────────────────────────────┐    │
│     │ Criterion 1: Pregnancy       │    │
│     │   Exclude: 120               │    │
│     └──────────────────────────────┘    │
│     ┌──────────────────────────────┐    │
│     │ Criterion 2: Previous enroll │    │
│     │   Exclude: 100               │    │
│     └──────────────────────────────┘    │
└───────────────┬─────────────────────────┘
                │ final_cohort (980 patients)
                ↓
┌─────────────────────────────────────────┐
│  5. Generate Statistics                  │
│     - Initial: 10,000                    │
│     - After inclusion: 1,200 (12%)       │
│     - After exclusion: 980 (9.8%)        │
│     - Criteria breakdown                 │
└───────────────┬─────────────────────────┘
                │ cohort + stats
                ↓
┌─────────────────────────────────────────┐
│  6. Save Results                         │
│     - cohort.parquet                     │
│     - stats.json                         │
└─────────────────────────────────────────┘
```

---

## 🗃️ 데이터 레이어

### OMOP CDM Tables (Parquet Format)

```
data/omop_cdm/
├── person.parquet
│   ├── person_id (PK)
│   ├── gender_concept_id
│   ├── year_of_birth
│   └── race_concept_id
│
├── condition_occurrence.parquet
│   ├── person_id (FK)
│   ├── condition_concept_id
│   ├── condition_start_date
│   └── condition_end_date
│
├── drug_exposure.parquet
│   ├── person_id (FK)
│   ├── drug_concept_id
│   ├── drug_exposure_start_date
│   └── drug_exposure_end_date
│
├── measurement.parquet
│   ├── person_id (FK)
│   ├── measurement_concept_id
│   ├── value_as_number
│   └── measurement_date
│
├── procedure_occurrence.parquet
│   ├── person_id (FK)
│   ├── procedure_concept_id
│   └── procedure_date
│
└── visit_occurrence.parquet
    ├── person_id (FK)
    ├── visit_concept_id
    ├── visit_start_date
    └── visit_end_date
```

---

## 🚀 성능 최적화 전략

### 1. DataFrame 캐싱
```python
# 자주 사용하는 테이블 메모리 캐시
@lru_cache(maxsize=10)
def load_table(table_name: str) -> pd.DataFrame:
    return pd.read_parquet(f"{table_name}.parquet")
```

### 2. 조기 필터링 (Early Filtering)
```python
# Step 1: person_id 먼저 축소
eligible_persons = initial_filter()  # 10,000 → 1,000

# Step 2: 축소된 person_id로만 OMOP 테이블 필터링
condition_df = condition_df[
    condition_df['person_id'].isin(eligible_persons)
]  # 1,000,000 rows → 10,000 rows
```

### 3. 청크 처리 (대용량 데이터)
```python
# 메모리 절약을 위한 청크 처리
results = []
for chunk in pd.read_parquet(
    "condition_occurrence.parquet",
    chunksize=100000
):
    filtered = apply_filters(chunk)
    results.append(filtered)
final = pd.concat(results)
```

### 4. Vectorized 연산
```python
# ❌ 나쁜 예: 루프
for idx, row in df.iterrows():
    if row['value'] >= 18:
        results.append(row)

# ✅ 좋은 예: Vectorized
results = df[df['value'] >= 18]
```

### 5. Index 활용
```python
# person_id를 인덱스로 설정
person_df = person_df.set_index('person_id')

# 빠른 조인
cohort = cohort.join(person_df, on='person_id')
```

---

## 🔍 에러 처리 전략

### 1. Missing Data
```python
# person_id가 없는 레코드 제외
condition_df = condition_df.dropna(subset=['person_id'])

# concept_id가 0인 레코드 제외
condition_df = condition_df[condition_df['condition_concept_id'] > 0]
```

### 2. Invalid Temporal Constraints
```python
try:
    window = parse_iso_duration("P3M")
except ValueError as e:
    logger.warning(f"Invalid ISO duration: {e}")
    window = pd.Timedelta(days=0)  # Fallback
```

### 3. Empty Results
```python
if len(cohort) == 0:
    logger.warning("No patients meet criteria")
    return pd.DataFrame(columns=['person_id']), stats
```

---

## 📊 확장성 고려사항

### Pandas → Dask 전환 (필요시)

```python
# Pandas (현재)
import pandas as pd
df = pd.read_parquet("large_table.parquet")

# Dask (분산 처리)
import dask.dataframe as dd
df = dd.read_parquet("large_table.parquet")

# API 동일 → 최소한의 코드 변경
filtered = df[df['value'] > 18].compute()
```

### 병렬 처리
```python
from concurrent.futures import ThreadPoolExecutor

# 여러 criteria를 병렬로 처리
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(filter_criterion, c, cohort)
        for c in criteria
    ]
    results = [f.result() for f in futures]
```

---

## 🔗 통합 포인트

### 기존 시스템과의 연결

```python
# 1. Trialist Pipeline 결과 활용
from src.pipeline.plugins.trialist_parser import TrialistParser

parser = TrialistParser(...)
trial_schema = parser.run(params, ctx, corpus)
# → EnhancedTrialSchema

# 2. VocabularyAdapter 통합
from src.pipeline.vocabulary_adapter import VocabularyAdapter

vocab_adapter = VocabularyAdapter("vocabulary/")
# → OMOP concept_id 검증

# 3. Cohort Filter 실행
from src.pipeline.cohort_builder import CohortBuilder

builder = CohortBuilder(data_root, vocab_adapter)
cohort, stats = builder.build_cohort(trial_schema)
# → Final cohort
```

---

## 🎯 설계 원칙

1. **단순성**: SQL 생성 없이 순수 Pandas
2. **모듈성**: 독립적인 모듈로 분리 (Translator, Filter, Builder)
3. **테스트 가능성**: 각 모듈 단위 테스트 가능
4. **확장성**: Dask 전환 가능한 구조
5. **성능**: 캐싱, 조기 필터링, Vectorized 연산

---

**다음 ���서**: [03-data-structures.md](03-data-structures.md)
