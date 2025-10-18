# Pandas 기반 코호트 필터링 시스템 - 개요

## 📋 프로젝트 개요

**목표**: Trial Schema (NER → 표준화 → CDM 매핑)를 Pandas DataFrame 연산만으로 코호트 필터링 수행

**핵심 원칙**:
- ❌ SQL 쿼리 생성 제외
- ✅ Pandas DataFrame 연산만 사용
- ✅ OMOP CDM Parquet/CSV 파일 직접 처리
- ✅ 기존 LocalVocabulary/VocabularyAdapter 활용

---

## 🎯 Why Pandas?

### 기존 접근 (SQL 기반)
```python
# SQL 쿼리 생성
query = """
SELECT p.person_id
FROM condition_occurrence c
WHERE c.condition_concept_id IN (...)
  AND c.condition_start_date BETWEEN ...
"""
result = db.execute(query)
```

**문제점**:
- ❌ SQL 생성 로직 복잡
- ❌ 데이터베이스 의존성
- ❌ 디버깅 어려움

### Pandas 접근 (채택) ⭐
```python
# Pandas DataFrame 연산
condition_df = pd.read_parquet("condition_occurrence.parquet")
filtered = condition_df[
    condition_df['condition_concept_id'].isin(target_concepts) &
    condition_df['condition_start_date'].between(start, end)
]
cohort = filtered['person_id'].unique()
```

**장점**:
- ✅ 단순성: SQL 생성 불필요
- ✅ 유연성: Python 로직으로 복잡한 조건 처리
- ✅ 통합성: 기존 LocalVocabulary (Pandas) 와 자연스러운 통합
- ✅ 디버깅: Python debugger로 단계별 확인 용이
- ✅ 데이터 독립성: DB 없이도 작동 (Parquet/CSV)

---

## 🔄 전체 파이프라인 흐름

```
┌─────────────────────────────────────────────────────────┐
│           Trialist Pipeline (이미 구현됨)                │
├─────────────────────────────────────────────────────────┤
│ 1. NER → 2. Standardization → 3. CDM Mapping            │
│ (TrialistParser + CDMMapper + VocabularyAdapter)        │
└───────────────────────┬─────────────────────────────────┘
                        │ EnhancedTrialSchema
                        ↓
┌─────────────────────────────────────────────────────────┐
│        Pandas Cohort Filter (신규 구현)                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  CriterionTranslator                                    │
│         ↓                                                │
│  PandasCohortFilter (Core Engine)                       │
│         ↓                                                │
│  TemporalFilter + ValueFilter + DomainFilters           │
│         ↓                                                │
│  CohortBuilder (Integration)                            │
│                                                          │
└───────────────────────┬─────────────────────────────────┘
                        │ Cohort DataFrame
                        ↓
┌─────────────────────────────────────────────────────────┐
│              Cohort Analysis / Export                    │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 구현 모듈

### 1. CriterionTranslator
**책임**: Trial Criterion을 Pandas 필터 조건으로 변환

**입력**: `EnhancedTrialCriterion` (Trialist parser 결과)
**출력**: `FilterCondition` (Pandas 실행 가능한 조건)

### 2. PandasCohortFilter
**책임**: Pandas DataFrame 연산으로 코호트 필터링 수행

**기능**:
- OMOP CDM 테이블 로드 (Parquet/CSV)
- Domain별 필터링 (Condition, Drug, Measurement, Procedure)
- Inclusion/Exclusion 로직

### 3. TemporalFilter
**책임**: 시간 제약 처리

**지원 패턴**:
- XBeforeY: X가 Y 이전
- XAfterY: X가 Y 이후
- XBeforeYwithTime: X가 Y 이전 N일 이내
- XWithinTime: X가 Y 전후 N일 이내
- XDuringY: X가 Y 기간 중

### 4. ValueFilter
**책임**: 값 비교 조건 처리

**지원 연산자**: `>=`, `<=`, `>`, `<`, `=`, `between`

### 5. CohortBuilder
**책임**: 전체 workflow 통합 및 조율

**기능**:
- Trial schema → Cohort 변환
- 통계 생성
- 결과 저장

---

## 🗂️ 데이터 구조

### OMOP CDM Parquet 파일
```
data/omop_cdm/
├── person.parquet                  # 환자 기본 정보
├── condition_occurrence.parquet    # 진단
├── drug_exposure.parquet           # 약물
├── measurement.parquet             # 측정값 (lab, vital signs)
├── procedure_occurrence.parquet    # 시술
├── visit_occurrence.parquet        # 방문/입원
└── observation.parquet             # 관찰
```

---

## 📈 구현 로드맵

### Phase 1: Core Infrastructure (3-4시간)
- CriterionTranslator 구현
- PandasCohortFilter 기본 구조
- Condition 필터링

### Phase 2: Domain Filters (2-3시간)
- Drug, Measurement, Procedure 필터링
- ValueFilter 구현

### Phase 3: Temporal Logic (2-3시간)
- TemporalFilter 구현
- ISO 8601 duration 파싱
- Temporal 패턴 구현

### Phase 4: Integration (2시간)
- CohortBuilder 구현
- 통계 생성
- 결과 저장

### Phase 5: Testing & Optimization (2-3시간)
- NCT03389555 실제 테스트
- MIMIC-IV 데모 데이터 테스트
- 성능 최적화

---

## 🎯 성공 지표

### 기능 요구사항
- [ ] Inclusion criteria 필터링 작동
- [ ] Exclusion criteria 필터링 작동
- [ ] Temporal 제약 처리
- [ ] Value 비교 조건 처리
- [ ] 모든 Domain 지원

### 성능 요구사항
- [ ] 10,000명 코호트 처리 시간 < 60초
- [ ] 메모리 사용량 < 4GB
- [ ] 캐싱으로 재실행 시간 < 10초

### 품질 요구사항
- [ ] Unit test coverage > 80%
- [ ] Integration test 통과
- [ ] NCT03389555 trial 테스트 성공
- [ ] MIMIC-IV 데모 테스트 성공

---

## 📚 관련 문서

- [02-architecture.md](02-architecture.md) - 시스템 아키텍처 상세
- [03-data-structures.md](03-data-structures.md) - 데이터 구조 정의
- [04-implementation-modules.md](04-implementation-modules.md) - 모듈별 구현 계획
- [05-examples.md](05-examples.md) - 사용 예시
- [06-testing-strategy.md](06-testing-strategy.md) - 테스트 전략

---

**총 예상 소요 시간**: 12-15시간 (2일)
