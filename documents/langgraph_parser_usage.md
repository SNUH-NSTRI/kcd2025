# LangGraph 기반 Parser Agent 사용 가이드

## 개요

`LangGraphTrialParser`는 ClinicalTrials.gov의 구조화된 데이터에서 eligibility criteria를 자동으로 추출하여 구조화된 Trial Schema로 변환합니다.

**✨ 주요 기능:**
- Inclusion/Exclusion Criteria 자동 파싱
- **Named Entity Recognition (NER)**: Concept, Temporal, Value 3가지 유형의 entity 자동 추출
- EHR 매핑을 위한 구조화된 데이터 생성

## 1. 개요
- `LangGraphTrialParser`는 LangChain + LangGraph 조합으로 논문 코퍼스에서 Trial Schema를 추출하는 파서 구현체다.
- CLI에서 `--impl parse-trials=langgraph` 옵션을 주면 해당 파서가 실행된다.
- 기본 LLM은 `gpt-4o-mini`이며 OpenAI 호환 키가 `OPENAI_API_KEY` 환경 변수로 설정돼 있어야 한다.

## 2. 의존성 설치
```bash
pip install "langchain>=0.2" "langgraph>=0.2" "langchain-openai>=0.1" "pydantic>=2.6"
```
- PDF 전처리를 확장하려면 `unstructured` 또는 `pymupdf`를 추가 설치하는 것이 좋다.

## 3. 동작 흐름

### 3.1 ClinicalTrials.gov 데이터 처리 (langgraph-search 사용 시)

Parser Agent의 `prepare_context` 단계에서 **4가지 핵심 정보**를 명시적으로 추출합니다:

1. **Inclusion Criteria (포함 기준) 자동 추출**
   - `metadata.eligibility.eligibilityCriteria` 또는 `metadata.full_study_data.protocolSection.eligibilityModule.eligibilityCriteria`에서 추출
   - "Inclusion Criteria:" 섹션의 각 항목을 `inclusion` criterion 객체로 변환

2. **Exclusion Criteria (제외 기준) 자동 추출**
   - 동일한 eligibilityCriteria 필드에서 "Exclusion Criteria:" 섹션 추출
   - 각 항목을 `exclusion` criterion 객체로 변환

3. **Treatment/Interventions (치료/중재) 자동 추출**
   - `metadata.full_study_data.protocolSection.armsInterventionsModule.interventions`에서 추출
   - 각 intervention의 name, type, description 포함
   - 용량, 빈도, 기간 등의 정보를 NER로 추출하여 `features` 배열에 포함

4. **Primary Outcomes (주요 결과 지표) 자동 추출**
   - `metadata.full_study_data.protocolSection.outcomesModule.primaryOutcomes`에서 추출
   - 각 outcome의 measure, timeFrame 포함
   - 결과 지표를 `features` 배열에 포함 (role: "primary_outcome")

5. **Context 구성**
   - Trial title, abstract, **4가지 핵심 정보**를 명시적으로 포함
   - 텍스트 분할: `RecursiveCharacterTextSplitter` (chunk_size=2500, overlap=250)

6. **LLM 파싱 (extract_schema 단계)**
   - "Inclusion Criteria:" 섹션의 각 bullet point → `inclusion` criterion 객체
   - "Exclusion Criteria:" 섹션의 각 bullet point → `exclusion` criterion 객체
   - "Treatment/Interventions" 정보 → `features` 배열에 포함 (role: "intervention")
   - "Primary Outcomes" 정보 → `features` 배열에 포함 (role: "primary_outcome")
   
   각 criterion은 구조화된 JSON 객체로 변환:
     - `id`: inc_/exc_ 접두사 (예: inc_septic_shock_icu_24h)
     - `description`: 원문 텍스트
     - `category`: demographic, clinical, laboratory, imaging, therapy
     - `kind`: threshold, diagnosis, temporal, composite
     - `value`: 구조화된 규칙 (연산자, 값, 범위)
     - `entities`: NER로 추출된 concept, temporal, value 엔티티

7. **검증 및 저장 (validate_schema 단계)**
   - JSON 파싱 및 필수 키 검증 후 `TrialSchema` 데이터클래스로 변환
   - `workspace/<project_id>/schema/trial_schema.json`에 저장

### 3.2 예시: NCT04134403

**Input (4가지 핵심 정보):**

**1. Eligibility Criteria:**
```
Inclusion Criteria:

* Septic shock admitted to the ICU within 24 hours as defined by SEPSIS-3
* Age ≥ 18 years
* Non-pregnant

Exclusion Criteria:

* Age < 18 years
* Pregnant
* Known G6PD deficiency
```

**2. Treatment/Interventions:**
```
- Hydrocortisone sodium succinate (Drug): 50 mg every 6 hours for 7 days or until ICU discharge
- Thiamine (Drug): 200 mg every 12 hours for 7 days
- Ascorbic acid (Drug): 1.5 g every 6 hours for 4 days
```

**3. Primary Outcomes:**
```
- 28-day mortality (Time Frame: 28 days)
- ICU length-of-stay (Time Frame: Up to 90 days)
```

**Output (trial_schema.json):**
```json
{
  "schema_version": "schema.v1",
  "disease_code": "septic_shock",
  "inclusion": [
    {
      "id": "inc_septic_shock_icu_24h",
      "description": "Septic shock admitted to the ICU within 24 hours",
      "category": "clinical",
      "kind": "temporal",
      "value": {"field": "icu_admission", "op": "<=", "value": 24, "unit": "hours"},
      "entities": [
        {"text": "Septic shock", "type": "concept"},
        {"text": "ICU", "type": "concept"},
        {"text": "within 24 hours", "type": "temporal"}
      ]
    },
    {
      "id": "inc_age_18_or_older",
      "description": "Age ≥ 18 years",
      "category": "demographic",
      "kind": "threshold",
      "value": {"field": "age", "op": ">=", "value": 18},
      "entities": [
        {"text": "Age", "type": "concept"},
        {"text": "≥ 18 years", "type": "temporal"}
      ]
    }
  ],
  "exclusion": [
    {
      "id": "exc_age_under_18",
      "description": "Age < 18 years",
      "category": "demographic",
      "kind": "threshold",
      "value": {"field": "age", "op": "<", "value": 18},
      "entities": [
        {"text": "Age", "type": "concept"},
        {"text": "< 18 years", "type": "temporal"}
      ]
    },
    {
      "id": "exc_g6pd_deficiency",
      "description": "Known G6PD deficiency",
      "category": "laboratory",
      "kind": "diagnosis",
      "value": {"field": "g6pd_status", "op": "=", "value": "deficient"},
      "entities": [
        {"text": "G6PD deficiency", "type": "concept"}
      ]
    }
  ],
  "features": [
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
        {"text": "7 days or until ICU discharge", "type": "temporal"}
      ]
    },
    {
      "name": "thiamine_treatment",
      "source": "prescriptions",
      "unit": "mg",
      "time_window": [0, 168],
      "metadata": {
        "role": "intervention",
        "dose": "200 mg",
        "frequency": "every 12 hours",
        "duration": "7 days"
      },
      "entities": [
        {"text": "Thiamine", "type": "concept"},
        {"text": "200 mg", "type": "value"},
        {"text": "every 12 hours", "type": "temporal"},
        {"text": "7 days", "type": "temporal"}
      ]
    },
    {
      "name": "mortality_28d",
      "source": "patients",
      "unit": null,
      "time_window": [0, 672],
      "metadata": {
        "role": "primary_outcome",
        "measure": "28-day mortality",
        "timeframe": "28 days"
      },
      "entities": [
        {"text": "28-day mortality", "type": "concept"},
        {"text": "28 days", "type": "temporal"}
      ]
    },
    {
      "name": "icu_los",
      "source": "icustays",
      "unit": "hours",
      "time_window": [0, 2160],
      "metadata": {
        "role": "primary_outcome",
        "measure": "ICU length-of-stay",
        "timeframe": "Up to 90 days"
      },
      "entities": [
        {"text": "ICU length-of-stay", "type": "concept"},
        {"text": "Up to 90 days", "type": "temporal"}
      ]
    }
  ]
}
```

### 3.3 Named Entity Recognition (NER)

각 criterion과 feature에는 **entities** 필드가 포함되어 3가지 유형의 entity를 저장합니다:

#### Entity 유형:
1. **concept** (청록색): 의학 개념, 질병, 치료, 결과, 해부학적 위치
   - 예: `septic shock`, `ICU`, `Age`, `G6PD deficiency`, `28-day mortality`

2. **temporal** (노란색): 시간 관련 정보
   - 예: `within 24 hours`, `≥ 18 years`, `every 6 hours`, `7 days`

3. **value** (마젠타): 수치 값
   - 예: `50 mg`, `> 2.0 mmol/L`, `≥ 65 mmHg`

**활용:**
- EHR 매핑: concept → table/column
- 시간 필터: temporal → SQL WHERE 조건
- 값 필터: value → 수치 비교 연산

## 4. 구동 예시

### 4.1 CLI 사용
```bash
export OPENAI_API_KEY=sk-...

# 1단계: NCT ID로 임상시험 데이터 검색
PYTHONPATH=src python -m rwe_cli --project nct04134403 --workspace workspace \
  --impl search-lit=langgraph-search \
  search-lit --keyword NCT04134403 --source clinicaltrials

# 2단계: LangGraph parser로 eligibility criteria 추출
PYTHONPATH=src python -m rwe_cli --project nct04134403 --workspace workspace \
  --impl parse-trials=langgraph \
  parse-trials --llm-provider gpt-4o-mini
```

### 4.2 API 사용
```bash
# 1단계: 문헌 검색
curl -X POST "http://localhost:8000/api/pipeline/search-lit" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "nct04134403",
    "keywords": ["NCT04134403"],
    "sources": ["clinicaltrials"],
    "impl": "langgraph-search"
  }'

# 2단계: Trial schema 파싱
curl -X POST "http://localhost:8000/api/pipeline/parse-trials" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "nct04134403",
    "llm_provider": "gpt-4o-mini",
    "impl": "langgraph"
  }'
```

**참고**:
- `--prompt-template` 옵션은 현재 무시되지만 향후 LangChain 프롬프트 디렉터리와 연동할 수 있다.
- `impl: "langgraph"`는 LangGraph parser를 사용하도록 지정 (synthetic이 아닌 실제 LLM 기반 파싱)

## 5. 확장 아이디어
- Guardrails/Structured Output Parser를 붙여 JSON 품질을 높이기.
- Summarize → Extract 두 단계로 Subgraph를 확장해 섹션별 재시도/휴먼 검수 노드 삽입.
- VectorStore(Retriever) 노드를 추가해 대규모 문헌에서도 필요한 섹션만 추출.
