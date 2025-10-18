# 테스트 전략

## 🎯 테스트 목표

**핵심 원칙**:
- ✅ 각 모듈의 독립적 검증
- ✅ 엔드-투-엔드 통합 검증
- ✅ 성능 목표 달성 확인
- ✅ OMOP CDM 표준 준수 검증

**Coverage 목표**:
- Unit tests: > 80%
- Integration tests: 주요 workflow 100%
- Performance tests: 모든 critical path

---

## 🧪 Unit Test 전략

### 1. CriterionTranslator Tests

#### Test Cases

**test_translate_simple_condition.py**
```python
def test_translate_simple_condition():
    """Test simple condition translation without temporal/value constraints"""
    translator = CriterionTranslator(vocab_adapter)

    criterion = EnhancedTrialCriterion(
        original="History of diabetes",
        entities=[
            EnhancedNamedEntity(
                text="diabetes mellitus",
                type="concept",
                domain="Condition",
                omop_concept_id=201826,
                standard_name="Type 2 diabetes mellitus"
            )
        ]
    )

    condition = translator.translate(criterion)

    assert condition.domain == "Condition"
    assert 201826 in condition.concept_ids
    assert condition.temporal is None
    assert condition.value is None
```

**test_translate_temporal_condition.py**
```python
def test_translate_temporal_condition():
    """Test temporal constraint translation"""
    translator = CriterionTranslator(vocab_adapter)

    criterion = EnhancedTrialCriterion(
        original="History of TBI within 3 months before ICU admission",
        entities=[
            EnhancedNamedEntity(
                text="traumatic brain injury",
                type="concept",
                domain="Condition",
                omop_concept_id=12345
            ),
            EnhancedNamedEntity(
                text="within 3 months before",
                type="temporal",
                temporal_pattern="XBeforeYwithTime",
                iso_duration="P3M",
                reference_point="icu_admission"
            )
        ]
    )

    condition = translator.translate(criterion)

    assert condition.temporal is not None
    assert condition.temporal.pattern == "XBeforeYwithTime"
    assert condition.temporal.anchor_event == "icu_admission"
    assert condition.temporal.window == pd.Timedelta(days=90)
    assert condition.temporal.direction == "before"
```

**test_translate_value_condition.py**
```python
def test_translate_value_condition():
    """Test value constraint translation"""
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
    assert condition.value is not None
    assert condition.value.operator == ">="
    assert condition.value.value == 18
    assert condition.value.unit == "year"
```

**test_translate_combined_condition.py**
```python
def test_translate_combined_temporal_and_value():
    """Test temporal + value constraints combined"""
    translator = CriterionTranslator(vocab_adapter)

    criterion = EnhancedTrialCriterion(
        original="eGFR < 60 within 30 days before enrollment",
        entities=[
            EnhancedNamedEntity(
                text="eGFR",
                type="concept",
                domain="Measurement",
                omop_concept_id=3049187,
                operator="<",
                numeric_value=60,
                unit="mL/min/1.73m2"
            ),
            EnhancedNamedEntity(
                text="within 30 days before",
                type="temporal",
                temporal_pattern="XBeforeYwithTime",
                iso_duration="P30D",
                reference_point="enrollment"
            )
        ]
    )

    condition = translator.translate(criterion)

    # Both temporal AND value should exist
    assert condition.temporal is not None
    assert condition.value is not None
    assert condition.value.operator == "<"
    assert condition.value.value == 60
    assert condition.temporal.window == pd.Timedelta(days=30)
```

---

### 2. PandasCohortFilter Tests

#### Test Cases

**test_filter_by_condition.py**
```python
def test_filter_by_condition():
    """Test condition filtering"""
    filter_engine = PandasCohortFilter(data_root)

    condition = FilterCondition(
        domain="Condition",
        concept_ids=[201826, 201254],  # Diabetes concepts
        temporal=None,
        value=None
    )

    initial_cohort = pd.DataFrame({'person_id': [1, 2, 3, 4, 5]})
    filtered = filter_engine.filter_by_condition(condition, initial_cohort)

    assert len(filtered) > 0
    assert 'person_id' in filtered.columns
    assert filtered['person_id'].is_unique
    # Verify all returned persons have diabetes
    condition_df = filter_engine.load_table("condition_occurrence")
    for person_id in filtered['person_id']:
        person_conditions = condition_df[
            condition_df['person_id'] == person_id
        ]
        assert any(
            person_conditions['condition_concept_id'].isin([201826, 201254])
        )
```

**test_filter_by_measurement.py**
```python
def test_filter_by_measurement_with_value():
    """Test measurement filtering with value constraint"""
    filter_engine = PandasCohortFilter(data_root)

    condition = FilterCondition(
        domain="Measurement",
        concept_ids=[3004],  # Age concept
        temporal=None,
        value=ValueCondition(
            operator=">=",
            value=18,
            unit="year"
        )
    )

    initial_cohort = pd.DataFrame({'person_id': [1, 2, 3, 4, 5]})
    filtered = filter_engine.filter_by_measurement(condition, initial_cohort)

    # All returned persons should have age >= 18
    measurement_df = filter_engine.load_table("measurement")
    for person_id in filtered['person_id']:
        person_measurements = measurement_df[
            (measurement_df['person_id'] == person_id) &
            (measurement_df['measurement_concept_id'] == 3004)
        ]
        assert person_measurements['value_as_number'].max() >= 18
```

**test_inclusion_criteria.py**
```python
def test_apply_inclusion_criteria():
    """Test inclusion criteria application (AND logic)"""
    filter_engine = PandasCohortFilter(data_root)

    criteria = [
        FilterCondition(domain="Measurement", concept_ids=[3004], value=ValueCondition(">=", 18, "year")),
        FilterCondition(domain="Condition", concept_ids=[201826]),
        FilterCondition(domain="Procedure", concept_ids=[4230167])
    ]

    initial_cohort = pd.DataFrame({'person_id': list(range(1, 101))})
    filtered = filter_engine.apply_inclusion_criteria(criteria, initial_cohort)

    # Should only include persons meeting ALL criteria
    assert len(filtered) <= len(initial_cohort)
    assert 'person_id' in filtered.columns
```

**test_exclusion_criteria.py**
```python
def test_apply_exclusion_criteria():
    """Test exclusion criteria application (NOT logic)"""
    filter_engine = PandasCohortFilter(data_root)

    criteria = [
        FilterCondition(domain="Condition", concept_ids=[4299535]),  # Pregnancy
        FilterCondition(domain="Condition", concept_ids=[40481087])  # Prior enrollment
    ]

    initial_cohort = pd.DataFrame({'person_id': list(range(1, 101))})
    filtered = filter_engine.apply_exclusion_criteria(criteria, initial_cohort)

    # Should exclude persons meeting ANY exclusion criterion
    assert len(filtered) <= len(initial_cohort)
```

---

### 3. TemporalFilter Tests

#### Test Cases

**test_temporal_before.py**
```python
def test_temporal_before_pattern():
    """Test XBeforeY pattern"""
    temporal_filter = TemporalFilter()

    temporal_condition = TemporalCondition(
        pattern="XBeforeY",
        anchor_event="icu_admission",
        window=pd.Timedelta(days=0),
        direction="before"
    )

    event_df = pd.DataFrame({
        'person_id': [1, 2, 3],
        'event_date': [
            datetime(2023, 1, 1),
            datetime(2023, 1, 15),
            datetime(2023, 2, 1)
        ]
    })

    anchor_dates = pd.DataFrame({
        'person_id': [1, 2, 3],
        'icu_admission': [
            datetime(2023, 1, 10),
            datetime(2023, 1, 10),
            datetime(2023, 1, 20)
        ]
    })

    filtered = temporal_filter.apply(event_df, temporal_condition, anchor_dates)

    # Only person 1 has event before ICU admission
    assert len(filtered) == 1
    assert filtered.iloc[0]['person_id'] == 1
```

**test_temporal_within_time.py**
```python
def test_temporal_within_time_pattern():
    """Test XBeforeYwithTime pattern"""
    temporal_filter = TemporalFilter()

    temporal_condition = TemporalCondition(
        pattern="XBeforeYwithTime",
        anchor_event="enrollment",
        window=pd.Timedelta(days=30),
        direction="before"
    )

    event_df = pd.DataFrame({
        'person_id': [1, 2, 3, 4],
        'event_date': [
            datetime(2023, 1, 1),   # 29 days before (include)
            datetime(2023, 1, 5),   # 25 days before (include)
            datetime(2022, 12, 1),  # 60 days before (exclude)
            datetime(2023, 2, 1)    # After enrollment (exclude)
        ]
    })

    anchor_dates = pd.DataFrame({
        'person_id': [1, 2, 3, 4],
        'enrollment': [datetime(2023, 1, 30)] * 4
    })

    filtered = temporal_filter.apply(event_df, temporal_condition, anchor_dates)

    # Only persons 1 and 2 should be included
    assert len(filtered) == 2
    assert set(filtered['person_id']) == {1, 2}
```

---

### 4. ValueFilter Tests

#### Test Cases

**test_value_operators.py**
```python
@pytest.mark.parametrize("operator,value,expected_persons", [
    (">=", 18, [1, 2, 3]),
    ("<=", 30, [1, 2]),
    (">", 25, [2, 3]),
    ("<", 20, [1]),
    ("=", 25, [2]),
    ("between", (20, 30), [2, 3])
])
def test_value_comparison_operators(operator, value, expected_persons):
    """Test all value comparison operators"""
    value_filter = ValueFilter()

    measurement_df = pd.DataFrame({
        'person_id': [1, 2, 3],
        'value_as_number': [18, 25, 35]
    })

    value_condition = ValueCondition(
        operator=operator,
        value=value,
        unit="year"
    )

    filtered = value_filter.apply(measurement_df, value_condition)

    assert set(filtered['person_id']) == set(expected_persons)
```

---

## 🔗 Integration Tests

### Test 1: NCT03389555 Full Cohort Build

**test_nct03389555_integration.py**
```python
def test_nct03389555_full_pipeline():
    """Test complete NCT03389555 cohort building"""
    # 1. Load trial schema (from Trialist parser output)
    schema = load_nct03389555_schema()

    # 2. Build cohort
    vocab_adapter = VocabularyAdapter("vocabulary/")
    builder = CohortBuilder(data_root=Path("data/omop_cdm"), vocab_adapter=vocab_adapter)
    cohort, stats = builder.build_cohort(schema)

    # 3. Assertions
    assert len(cohort) > 0, "Cohort should not be empty"
    assert stats['initial_population'] > 0
    assert stats['after_inclusion'] <= stats['initial_population']
    assert stats['after_exclusion'] <= stats['after_inclusion']
    assert stats['final_cohort_size'] == len(cohort)

    # 4. Verify cohort structure
    expected_columns = ['person_id', 'inclusion_date', 'cohort_start_date', 'age_at_inclusion']
    for col in expected_columns:
        assert col in cohort.columns

    assert cohort['person_id'].is_unique

    # 5. Verify statistics structure
    assert 'criteria_breakdown' in stats
    assert len(stats['criteria_breakdown']) > 0
    assert 'processing_time_seconds' in stats
    assert stats['processing_time_seconds'] > 0
```

### Test 2: MIMIC-IV Demo Data

**test_mimic_demo_integration.py**
```python
def test_mimic_demo_cohort_build():
    """Test cohort building with MIMIC-IV demo data"""
    # 1. Create simple trial schema
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
                original="ICU admission",
                entities=[
                    EnhancedNamedEntity(
                        text="ICU",
                        type="concept",
                        domain="Visit",
                        omop_concept_id=9203  # ICU visit
                    )
                ]
            )
        ],
        exclusion=[]
    )

    # 2. Build cohort
    vocab_adapter = VocabularyAdapter("vocabulary/")
    builder = CohortBuilder(data_root=Path("mimiciv/3.1/"), vocab_adapter=vocab_adapter)
    cohort, stats = builder.build_cohort(schema)

    # 3. Verify results
    assert len(cohort) > 0
    assert stats['inclusion_rate'] > 0
    assert stats['inclusion_rate'] <= 1.0
```

---

## ⚡ Performance Tests

### Test 1: Large Cohort Performance

**test_performance_large_cohort.py**
```python
def test_large_cohort_performance():
    """Test performance with 10,000+ patients"""
    import time

    # 1. Create schema with 3 inclusion + 2 exclusion criteria
    schema = create_complex_schema()

    # 2. Measure execution time
    start_time = time.time()

    vocab_adapter = VocabularyAdapter("vocabulary/")
    builder = CohortBuilder(data_root=Path("data/omop_cdm"), vocab_adapter=vocab_adapter)
    cohort, stats = builder.build_cohort(schema)

    elapsed = time.time() - start_time

    # 3. Performance assertions
    assert elapsed < 60, f"Build took {elapsed:.1f}s (target: <60s)"
    assert stats['memory_peak_mb'] < 4096, f"Memory peak {stats['memory_peak_mb']:.0f} MB (target: <4GB)"

    # 4. Log performance metrics
    print(f"\nPerformance Metrics:")
    print(f"  Initial population: {stats['initial_population']:,}")
    print(f"  Final cohort: {stats['final_cohort_size']:,}")
    print(f"  Processing time: {elapsed:.1f}s")
    print(f"  Memory peak: {stats['memory_peak_mb']:.0f} MB")
```

### Test 2: Caching Performance

**test_performance_caching.py**
```python
def test_caching_performance():
    """Test that caching improves re-run performance"""
    import time

    schema = create_simple_schema()
    vocab_adapter = VocabularyAdapter("vocabulary/")
    builder = CohortBuilder(data_root=Path("data/omop_cdm"), vocab_adapter=vocab_adapter)

    # First run (cold cache)
    start1 = time.time()
    cohort1, stats1 = builder.build_cohort(schema)
    time1 = time.time() - start1

    # Second run (warm cache)
    start2 = time.time()
    cohort2, stats2 = builder.build_cohort(schema)
    time2 = time.time() - start2

    # Cache should make second run faster
    assert time2 < time1 * 0.5, f"Caching ineffective: {time1:.1f}s → {time2:.1f}s"

    # Results should be identical
    assert len(cohort1) == len(cohort2)
```

---

## 📊 Test Data Requirements

### 1. OMOP CDM Sample Data

**Required tables** (Parquet format):
```
data/omop_cdm/
├── person.parquet               # 10,000 patients
├── condition_occurrence.parquet # 1M records
├── drug_exposure.parquet        # 800K records
├── measurement.parquet          # 2M records
├── procedure_occurrence.parquet # 500K records
└── visit_occurrence.parquet     # 100K records
```

### 2. MIMIC-IV Demo Data

**Location**: `mimiciv/3.1/`
**Required files**:
- admissions.csv
- patients.csv
- diagnoses_icd.csv
- labevents.csv
- prescriptions.csv

### 3. Test Fixtures

**fixtures/trial_schemas/**
```python
# fixtures/trial_schemas/nct03389555.json
{
    "inclusion": [
        {
            "original": "Age >= 18 years",
            "entities": [...]
        },
        {
            "original": "Mechanically ventilated",
            "entities": [...]
        }
    ],
    "exclusion": [
        {
            "original": "Pregnancy",
            "entities": [...]
        }
    ]
}
```

---

## 🏃 CI/CD Testing Workflow

### GitHub Actions Workflow

```yaml
name: Cohort Filter Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Download test data
      run: |
        # Download OMOP CDM sample data
        python scripts/download_test_data.py

    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src/pipeline/cohort_filtering

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v

    - name: Run performance tests
      run: |
        pytest tests/performance/ -v

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

---

## 📈 Coverage Goals

### Coverage Targets

| Component | Unit Test Coverage | Integration Coverage |
|-----------|-------------------|---------------------|
| CriterionTranslator | > 90% | 100% (NCT03389555) |
| PandasCohortFilter | > 85% | 100% (workflow) |
| TemporalFilter | > 90% | 100% (patterns) |
| ValueFilter | > 95% | 100% (operators) |
| CohortBuilder | > 80% | 100% (end-to-end) |

### Quality Gates

- ✅ All tests pass
- ✅ Coverage > 80%
- ✅ No critical bugs
- ✅ Performance targets met
- ✅ Integration tests pass

---

## 🐛 Known Edge Cases to Test

### 1. Empty Results
```python
def test_empty_cohort_handling():
    """Test when no patients meet criteria"""
    schema = create_impossible_schema()  # Contradictory criteria
    cohort, stats = builder.build_cohort(schema)

    assert len(cohort) == 0
    assert stats['final_cohort_size'] == 0
    assert stats['inclusion_rate'] == 0
```

### 2. Missing Data
```python
def test_missing_temporal_data():
    """Test when anchor event dates are missing"""
    # Some persons have no ICU admission date
    # Should handle gracefully
```

### 3. Invalid Constraints
```python
def test_invalid_iso_duration():
    """Test invalid ISO 8601 duration"""
    criterion = EnhancedTrialCriterion(
        original="Invalid temporal",
        entities=[
            EnhancedNamedEntity(
                iso_duration="INVALID"  # Should handle gracefully
            )
        ]
    )
```

---

## 📝 Test Documentation

### Test Naming Convention
```
test_{module}_{scenario}_{expected_result}.py

Examples:
- test_translator_simple_condition_success.py
- test_filter_temporal_before_correct_results.py
- test_builder_empty_cohort_zero_size.py
```

### Test Docstrings
```python
def test_function():
    """
    One-line summary of what's being tested.

    Test Steps:
    1. Setup test data
    2. Execute function
    3. Verify results

    Expected:
    - Specific assertion 1
    - Specific assertion 2
    """
```

---

## 🔄 Test Execution Order

### Recommended Test Order

1. **Unit Tests** (Fast, ~5 minutes)
   ```bash
   pytest tests/unit/ -v
   ```

2. **Integration Tests** (Medium, ~10 minutes)
   ```bash
   pytest tests/integration/ -v
   ```

3. **Performance Tests** (Slow, ~15 minutes)
   ```bash
   pytest tests/performance/ -v
   ```

### Parallel Execution
```bash
# Run tests in parallel (4 workers)
pytest -n 4 tests/
```

---

## ✅ Acceptance Criteria

Before considering the implementation complete:

- [ ] All unit tests pass (> 80% coverage)
- [ ] All integration tests pass
- [ ] NCT03389555 test successful
- [ ] MIMIC-IV demo test successful
- [ ] Performance < 60s for 10,000 patients
- [ ] Memory < 4GB
- [ ] Caching reduces re-run time by > 50%
- [ ] No critical bugs
- [ ] Documentation complete
- [ ] Code review passed

---

**다음 단계**: 구현 시작 (Phase 1: CriterionTranslator)
