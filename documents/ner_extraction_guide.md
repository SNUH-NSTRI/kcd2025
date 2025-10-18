# Named Entity Recognition (NER) 가이드

## 📋 개요

LangGraph Parser는 임상시험 문서에서 **3가지 유형의 Named Entity**를 자동으로 추출합니다:

1. **CONCEPT** (개념) - 청록색/파란색
2. **TEMPORAL** (시간) - 노란색
3. **VALUE** (값) - 마젠타/분홍색

## 🎯 Entity 유형 정의

### 1. CONCEPT (개념 엔티티)

**의료/임상 개념을 나타내는 텍스트**

**예시:**
- 질병/증상: `septic shock`, `stroke`, `traumatic brain injury`, `organ dysfunction`
- 치료: `Hydrocortisone sodium succinate`, `thiamine`, `ascorbic acid`
- 결과: `28-day mortality`, `ICU length-of-stay`, `mechanical ventilation`
- 해부학적 위치: `ICU`, `hospital`, `emergency department`
- 인구학적 속성: `Age`, `Sex`, `pregnant`
- 진단 검사: `serum lactate`, `MAP`, `vasopressor`

**특징:**
- 의학 용어, SNOMED CT, ICD-10 코드로 매핑 가능
- EHR 데이터에서 조회 가능한 개념
- 치료, 진단, 결과, 해부학적 구조 등

### 2. TEMPORAL (시간 엔티티)

**시간 관련 정보를 나타내는 텍스트**

**예시:**
- 나이 범위: `≥ 18 years old`, `< 18 years`
- 시간 창: `within 24 hours`, `within the past 3 months`, `before the ICU admission`
- 지속 시간: `for at least 6 consecutive hours`, `7 days`
- 빈도: `every 6 hours`, `twice daily`
- 상대 시간: `after the ICU admission`, `until ICU discharge`, `at enrollment`

**특징:**
- 절대 시간 또는 상대 시간 표현
- Index time(기준 시점) 기준으로 변환 가능
- EHR에서 시간 필터링에 사용

### 3. VALUE (값 엔티티)

**수치 값과 단위를 나타내는 텍스트**

**예시:**
- 용량: `50 mg`, `100 mg/kg`
- 임계값: `> 2.0 mmol/L`, `≥ 65 mmHg`
- 범위: `18-65 years`, `2-4 weeks`
- 비율: `30 ml/kg`
- 점수: `SOFA score ≥ 2`

**특징:**
- 항상 숫자 + 단위 조합
- 비교 연산자 포함 가능 (>, ≥, <, ≤, =)
- EHR 쿼리의 필터 조건으로 사용

## 📊 실제 예시 (NCT04134403)

### Inclusion Criteria

#### 예시 1: "Age ≥ 18 years old"
```json
{
  "id": "inc_age_18_or_older",
  "description": "Age ≥ 18 years old",
  "category": "demographic",
  "kind": "threshold",
  "value": {"field": "age", "op": ">=", "value": 18},
  "entities": [
    {"text": "Age", "type": "concept"},
    {"text": "≥ 18 years old", "type": "temporal"}
  ]
}
```

**분석:**
- `Age` → **CONCEPT** (인구학적 속성)
- `≥ 18 years old` → **TEMPORAL** (나이 기준)

#### 예시 2: "Diagnosis of septic shock within 24 hours after the ICU admission"
```json
{
  "id": "inc_septic_shock_icu_24h",
  "description": "Diagnosis of septic shock within 24 hours after the ICU admission",
  "category": "clinical",
  "kind": "temporal",
  "value": {
    "condition": "septic_shock",
    "time_window": {"reference": "icu_admission", "max_hours": 24}
  },
  "entities": [
    {"text": "septic shock", "type": "concept"},
    {"text": "within 24 hours after", "type": "temporal"},
    {"text": "ICU admission", "type": "concept"}
  ]
}
```

**분석:**
- `septic shock` → **CONCEPT** (질병)
- `within 24 hours after` → **TEMPORAL** (시간 창)
- `ICU admission` → **CONCEPT** (이벤트)

#### 예시 3: "Organ dysfunction for at least 6 consecutive hours"
```json
{
  "id": "inc_organ_dysfunction_6h",
  "description": "Organ dysfunction for at least 6 consecutive hours",
  "category": "clinical",
  "kind": "temporal",
  "value": {
    "condition": "organ_dysfunction",
    "min_duration_hours": 6
  },
  "entities": [
    {"text": "Organ dysfunction", "type": "concept"},
    {"text": "for at least 6 consecutive hours", "type": "temporal"}
  ]
}
```

**분석:**
- `Organ dysfunction` → **CONCEPT** (임상 상태)
- `for at least 6 consecutive hours` → **TEMPORAL** (최소 지속 시간)

### Exclusion Criteria

#### 예시: "History of stroke within the past 3 months before the ICU admission"
```json
{
  "id": "exc_stroke_past_3mo",
  "description": "History of stroke within the past 3 months before the ICU admission",
  "category": "clinical",
  "kind": "temporal",
  "value": {
    "condition": "stroke",
    "time_window": {"reference": "icu_admission", "min_days": -90, "max_days": 0}
  },
  "entities": [
    {"text": "stroke", "type": "concept"},
    {"text": "within the past 3 months before", "type": "temporal"},
    {"text": "ICU admission", "type": "concept"}
  ]
}
```

**분석:**
- `stroke` → **CONCEPT** (질병)
- `within the past 3 months before` → **TEMPORAL** (과거 시간 창)
- `ICU admission` → **CONCEPT** (기준 이벤트)

### Treatment (Feature)

#### 예시: "Hydrocortisone sodium succinate, 50 mg, every 6 hours, 7 days or until ICU discharge"
```json
{
  "name": "hydrocortisone_treatment",
  "source": "prescriptions",
  "unit": "mg",
  "time_window": [0, 168],
  "metadata": {
    "role": "intervention",
    "dose": "50 mg",
    "frequency": "every 6 hours",
    "duration": "7 days or until ICU discharge"
  },
  "entities": [
    {"text": "Hydrocortisone sodium succinate", "type": "concept"},
    {"text": "50 mg", "type": "value"},
    {"text": "every 6 hours", "type": "temporal"},
    {"text": "7 days or until ICU discharge", "type": "temporal"},
    {"text": "ICU discharge", "type": "concept"}
  ]
}
```

**분석:**
- `Hydrocortisone sodium succinate` → **CONCEPT** (약물명)
- `50 mg` → **VALUE** (용량)
- `every 6 hours` → **TEMPORAL** (투여 빈도)
- `7 days or until ICU discharge` → **TEMPORAL** (치료 기간)
- `ICU discharge` → **CONCEPT** (종료 이벤트)

### Primary Outcome

#### 예시: "28-day mortality"
```json
{
  "name": "mortality_28d",
  "source": "patients",
  "unit": null,
  "time_window": [0, 672],
  "metadata": {
    "role": "primary_outcome",
    "definition": "All-cause mortality within 28 days"
  },
  "entities": [
    {"text": "28-day mortality", "type": "concept"}
  ]
}
```

**분석:**
- `28-day mortality` → **CONCEPT** (결과 지표, 시간이 포함되어 있지만 전체가 하나의 개념)

## 🔄 EHR 매핑 활용

### CONCEPT → EHR Table/Column
```python
concept_mapping = {
    "septic_shock": {
        "table": "diagnoses_icd",
        "column": "icd_code",
        "values": ["R65.21", "A41.9"]
    },
    "Age": {
        "table": "patients",
        "column": "anchor_age"
    },
    "ICU admission": {
        "table": "icustays",
        "column": "intime"
    }
}
```

### TEMPORAL → SQL WHERE 조건
```sql
-- "within 24 hours after the ICU admission"
WHERE diagnosis_time >= icu.intime 
  AND diagnosis_time <= icu.intime + INTERVAL '24 hours'

-- "for at least 6 consecutive hours"
HAVING MAX(end_time) - MIN(start_time) >= INTERVAL '6 hours'

-- "within the past 3 months before"
WHERE event_time >= icu.intime - INTERVAL '3 months'
  AND event_time < icu.intime
```

### VALUE → SQL 필터
```sql
-- "50 mg"
WHERE dose = 50 AND dose_unit = 'mg'

-- "> 2.0 mmol/L"
WHERE value > 2.0 AND unit = 'mmol/L'

-- "≥ 18 years old"
WHERE age >= 18
```

## 🚀 API 사용 예시

### 1. Parse-Trials 실행
```bash
curl -X POST "http://localhost:8000/api/pipeline/parse-trials" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "final_test",
    "llm_provider": "gpt-4o-mini",
    "impl": "langgraph"
  }'
```

### 2. 결과 확인
```bash
cat workspace/final_test/schema/trial_schema.json | python -m json.tool
```

### 3. Entities 추출
```python
import json

with open('workspace/final_test/schema/trial_schema.json') as f:
    schema = json.load(f)

# Inclusion criteria의 모든 entities 출력
for criterion in schema['inclusion']:
    print(f"\n{criterion['description']}")
    if criterion.get('entities'):
        for entity in criterion['entities']:
            print(f"  [{entity['type'].upper()}] {entity['text']}")
```

## 📈 NER 품질 개선 팁

### 1. Prompt Engineering
- 구체적인 예시를 프롬프트에 포함
- Entity 유형 정의를 명확하게
- Few-shot learning 활용

### 2. Post-processing
- 중복 entity 제거
- Overlapping entity 해결
- Entity 경계 보정

### 3. Validation
- 의학 용어 사전(UMLS, SNOMED CT)과 대조
- EHR 스키마와 매핑 가능한지 확인
- 도메인 전문가 리뷰

## 🔧 문제 해결

### Q: Entity가 추출되지 않는 경우
**A:** 
1. LLM 모델 확인 (gpt-4o-mini 권장)
2. 프롬프트에 예시 추가
3. Eligibility criteria 텍스트 품질 확인

### Q: Concept과 Temporal 구분이 모호한 경우
**A:**
- `28-day mortality` → **CONCEPT** (복합 개념)
- `within 28 days` → **TEMPORAL** (순수 시간 표현)
- 규칙: 의학적 의미가 있으면 CONCEPT

### Q: Value 추출 기준은?
**A:**
- 반드시 숫자 + 단위 조합
- 단독 숫자는 CONCEPT 또는 TEMPORAL로 분류
- 예: `18 years old` → TEMPORAL (나이 기준)

## 📚 관련 문서

- [LangGraph Parser Usage](./langgraph_parser_usage.md)
- [API Specification](./api_specification.md)
- [CLI Modules](./cli_modules.md)

