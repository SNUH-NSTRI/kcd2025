# RWE Clinical Trial Emulation API 명세

## 개요

이 문서는 Real-World Evidence(RWE) Clinical Trial Emulation 플랫폼의 FastAPI 기반 REST API 명세를 정의합니다. 

**Base URL**: `http://localhost:8000`  
**API Version**: `0.1.0`  
**Interactive Docs**: `http://localhost:8000/docs`

## 인증

현재 버전은 인증을 요구하지 않습니다.

---

## Implementation (impl) 파라미터 가이드

모든 파이프라인 엔드포인트는 선택적 `impl` 파라미터를 지원하며, 각 단계에서 사용할 구현체를 지정할 수 있습니다.

### 사용 가능한 구현체

| Stage | impl 값 | 설명 | 요구사항 |
|-------|---------|------|----------|
| **search-lit** | `synthetic` | 테스트용 가짜 데이터 생성 (기본값) | - |
| | `langgraph-search` | ClinicalTrials.gov에서 실제 데이터 가져오기 | `requests` 패키지 |
| **parse-trials** | `synthetic` | 테스트용 가짜 스키마 생성 (기본값) | - |
| | `langgraph` | LLM 기반 실제 파싱 | OpenAI API 키, `langchain-openai` |
| **map-to-ehr** | `synthetic` | 테스트용 가짜 매핑 생성 (기본값) | - |
| | `mimic-demo` | MIMIC-IV 데모 데이터셋 기반 실제 매핑 | MIMIC-IV 데이터 |
| **filter-cohort** | `synthetic` | 테스트용 가짜 코호트 생성 (기본값) | - |
| | `mimic-demo` | MIMIC-IV 데모 데이터셋 기반 실제 필터링 | MIMIC-IV 데이터 |
| **analyze** | `synthetic` | 테스트용 가짜 분석 결과 생성 (기본값) | - |
| **write-report** | `synthetic` | 테스트용 가짜 리포트 생성 (기본값) | - |

### NCT ID로 직접 검색하기

`langgraph-search` 구현체는 NCT ID를 직접 인식하여 ClinicalTrials.gov에서 특정 임상시험을 가져올 수 있습니다.

**예시: NCT04134403 임상시험 가져오기**
```bash
curl -X POST "http://localhost:8000/api/pipeline/search-lit" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "nct04134403",
    "disease_code": "",
    "keywords": ["NCT04134403"],
    "sources": ["clinicaltrials"],
    "max_records": 5,
    "require_full_text": false,
    "impl": "langgraph-search"
  }'
```

**응답 예시:**
```json
{
  "status": "success",
  "message": "Literature search completed: 1 documents",
  "corpus": {
    "schema_version": "lit.v1",
    "documents": [
      {
        "source": "clinicaltrials",
        "identifier": "NCT04134403",
        "title": "Steroids, Thiamine and Ascorbic Acid Supplementation in Septic Shock (STASIS)",
        "abstract": "...",
        "metadata": {
          "nct_id": "NCT04134403",
          "phase": ["PHASE3"],
          "conditions": ["Septic Shock"],
          "status": "UNKNOWN",
          "arms_interventions": {...},
          "eligibility": {...},
          "outcomes": {...},
          "sponsors": {...},
          "contacts_locations": {...},
          "design": {...},
          "full_study_data": {
            "protocolSection": {
              "identificationModule": {...},
              "statusModule": {...},
              "... 12개 모듈 전체 포함": "..."
            }
          }
        }
      }
    ]
  },
  "document_count": 1
}
```

**주요 metadata 필드:**
- `full_study_data`: ClinicalTrials.gov API의 **전체 응답 데이터** (약 11KB)
  - 12개 protocolSection 모듈 전체 포함
  - 모든 원본 정보 보존
- `eligibility`: 포함/제외 기준 (성별, 나이, criteria 전문)
- `outcomes`: Primary/Secondary 결과 지표
- `sponsors`: 스폰서 및 협력 기관  
- `design`: 연구 설계 정보 (연구 유형, 참여자 수)
- `contacts_locations`: 연구 기관 및 연락처

**데이터 크기:**
- 단일 문서 metadata: 약 18KB
- workspace corpus.jsonl 파일: 약 21KB

---

## API 엔드포인트

### 1. Literature Search (`POST /api/pipeline/search-lit`)

문헌 검색을 수행하고 임상시험 데이터를 수집합니다.

#### Request

```json
{
  "project_id": "hfpef-001",
  "disease_code": "HFpEF",
  "keywords": ["sacubitril", "valsartan"],
  "sources": ["clinicaltrials"],
  "max_records": 5,
  "require_full_text": false,
  "impl": null
}
```

**필수 필드**:
- `project_id` (string): 프로젝트 식별자
- `disease_code` (string): 질환 코드
- `keywords` (array): 검색 키워드 목록
- `sources` (array): 데이터 소스 목록

**선택 필드**:
- `max_records` (integer): 최대 레코드 수 (기본값: 5)
- `require_full_text` (boolean): 전문 필요 여부 (기본값: false)
- `impl` (string): 구현체 오버라이드

#### Response

```json
{
  "status": "success",
  "message": "Literature search completed: 5 documents",
  "corpus": {
    "schema_version": "lit.v1",
    "documents": [
      {
        "source": "clinicaltrials",
        "identifier": "NCT05818397",
        "title": "Study of Sacubitril/Valsartan in HFpEF",
        "abstract": "...",
        "full_text": null,
        "fetched_at": "2025-10-12T10:30:00Z",
        "url": "https://clinicaltrials.gov/...",
        "metadata": {}
      }
    ]
  },
  "document_count": 5
}
```

#### 에러 응답

```json
{
  "detail": "Error message"
}
```

HTTP Status: 500

---

### 2. Parse Trials (`POST /api/pipeline/parse-trials`)

문헌에서 Trial Schema를 추출합니다.

#### Request

```json
{
  "project_id": "hfpef-001",
  "llm_provider": "gpt-4o-mini",
  "prompt_template": "default-trial-prompt.txt",
  "impl": null
}
```

**필수 필드**:
- `project_id` (string): 프로젝트 식별자

**선택 필드**:
- `llm_provider` (string): LLM 제공자 (기본값: "synthetic-llm")
- `prompt_template` (string): 프롬프트 템플릿 (기본값: "default-trial-prompt.txt")
- `impl` (string): 구현체 오버라이드

#### Response

```json
{
  "status": "success",
  "message": "Trial parsing completed: 3 inclusion criteria",
  "schema": {
    "schema_version": "schema.v1",
    "disease_code": "HFpEF",
    "inclusion": [
      {
        "id": "inc_01",
        "description": "LVEF >= 40%",
        "category": "inclusion",
        "kind": "clinical",
        "value": {"field": "lvef", "op": ">=", "threshold": 40}
      }
    ],
    "exclusion": [...],
    "features": [...],
    "provenance": {}
  },
  "inclusion_count": 3,
  "exclusion_count": 2,
  "feature_count": 5
}
```

---

### 3. Map to EHR (`POST /api/pipeline/map-to-ehr`)

Trial Schema를 EHR 변수에 매핑합니다.

#### Request

```json
{
  "project_id": "hfpef-001",
  "ehr_source": "mimic",
  "dictionary": "documents/mimic_lv_feature_schema.md",
  "output_format": "json",
  "impl": null
}
```

**필수 필드**:
- `project_id` (string): 프로젝트 식별자

**선택 필드**:
- `ehr_source` (string): EHR 소스 (기본값: "mimic")
- `dictionary` (string): 변수 사전 경로
- `output_format` (string): 출력 형식 ("json" | "sql", 기본값: "json")
- `impl` (string): 구현체 오버라이드

#### Response

```json
{
  "status": "success",
  "message": "EHR mapping completed: 5 variables mapped",
  "filter_spec": {
    "schema_version": "filters.v1",
    "ehr_source": "mimic",
    "variable_map": [...],
    "inclusion_filters": [...],
    "exclusion_filters": [...],
    "lineage": {}
  },
  "variable_map_count": 5,
  "inclusion_filters_count": 3,
  "exclusion_filters_count": 2
}
```

---

### 4. Filter Cohort (`POST /api/pipeline/filter-cohort`)

필터 명세를 적용해 코호트를 추출합니다.

#### Request

```json
{
  "project_id": "hfpef-001",
  "input_uri": "duckdb:///synthetic.duckdb",
  "sample_size": null,
  "dry_run": false,
  "impl": null
}
```

**필수 필드**:
- `project_id` (string): 프로젝트 식별자

**선택 필드**:
- `input_uri` (string): 입력 데이터 URI (기본값: "duckdb:///synthetic.duckdb")
- `sample_size` (integer): 샘플 크기 제한
- `dry_run` (boolean): 드라이런 모드 (기본값: false)
- `impl` (string): 구현체 오버라이드

#### Response

```json
{
  "status": "success",
  "message": "Cohort filtering completed: 150 subjects",
  "cohort": {
    "schema_version": "cohort.v1",
    "rows": [...],
    "summary": {
      "total_subjects": 150,
      "exclusion_counts": {},
      "generated_at": "2025-10-12T11:00:00Z"
    }
  },
  "total_subjects": 150,
  "summary": {...}
}
```

---

### 5. Analyze Outcomes (`POST /api/pipeline/analyze`)

코호트 기반 분석을 수행합니다.

#### Request

```json
{
  "project_id": "hfpef-001",
  "treatment_column": "on_arnI",
  "outcome_column": "mortality_30d",
  "estimators": ["synthetic", "ate-synthetic"],
  "impl": null
}
```

**필수 필드**:
- `project_id` (string): 프로젝트 식별자
- `estimators` (array): 추정기 목록

**선택 필드**:
- `treatment_column` (string): 치료 컬럼 (기본값: "on_arnI")
- `outcome_column` (string): 결과 컬럼 (기본값: "mortality_30d")
- `impl` (string): 구현체 오버라이드

#### Response

```json
{
  "status": "success",
  "message": "Outcome analysis completed",
  "analysis": {
    "schema_version": "analysis.v1",
    "outcomes": [...],
    "metrics": {
      "estimators": ["synthetic"],
      "generated_at": "2025-10-12T11:30:00Z",
      "summary": {
        "mean_ate": -0.05,
        "std_ate": 0.02
      }
    }
  },
  "outcome_count": 150,
  "metrics_summary": {...}
}
```

---

### 6. Write Report (`POST /api/pipeline/write-report`)

분석 결과를 보고서로 생성합니다.

#### Request

```json
{
  "project_id": "hfpef-001",
  "template": "templates/default_report.md",
  "format": "markdown",
  "hil_review": false,
  "impl": null
}
```

**필수 필드**:
- `project_id` (string): 프로젝트 식별자
- `template` (string): 템플릿 경로

**선택 필드**:
- `format` (string): 출력 형식 ("markdown" | "pdf", 기본값: "markdown")
- `hil_review` (boolean): HIL 리뷰 활성화 (기본값: false)
- `impl` (string): 구현체 오버라이드

#### Response

```json
{
  "status": "success",
  "message": "Report generated: 3 figures",
  "report_path": "workspace/hfpef-001/report/report.md",
  "report_body_length": 2500,
  "figure_count": 3
}
```

---

### 7. What-If Simulation (`POST /api/pipeline/stimula`)

가상 시나리오 시뮬레이션을 수행합니다.

#### Request

```json
{
  "project_id": "hfpef-001",
  "vary": ["LVEF_LT=35,40,45", "AGE_MIN=50,60"],
  "max_variations": 3,
  "subject_id": null
}
```

**필수 필드**:
- `project_id` (string): 프로젝트 식별자

**선택 필드**:
- `vary` (array): 변수 변경 명세
- `max_variations` (integer): 최대 변경 수 (기본값: 3)
- `subject_id` (string): 특정 환자 ID

#### Response

```json
{
  "status": "success",
  "message": "Stimula completed: 6 scenarios",
  "scenario_count": 6,
  "baseline_subjects": 150,
  "scenarios": [
    {
      "variation": "LVEF_LT=35",
      "applied_on": "lvef",
      "threshold": 35,
      "kept_subjects": 120,
      "dropped_subjects": 30,
      "keep_rate": 0.8,
      "sample_subjects": ["001", "002", "003"]
    }
  ]
}
```

---

### 8. Run All Pipeline (`POST /api/pipeline/run-all`)

전체 파이프라인을 순차 실행합니다.

#### Request

```json
{
  "project_id": "hfpef-001",
  "disease_code": "HFpEF",
  "keywords": ["sacubitril", "valsartan"],
  "sources": ["clinicaltrials"],
  "estimators": ["synthetic"],
  "template": "templates/default_report.md",
  "max_records": 5,
  "require_full_text": false,
  "llm_provider": "synthetic-llm",
  "prompt_template": "default-trial-prompt.txt",
  "ehr_source": "mimic",
  "dictionary": null,
  "filters_format": "json",
  "input_uri": "duckdb:///synthetic.duckdb",
  "sample_size": null,
  "treatment_column": "on_arnI",
  "outcome_column": "mortality_30d",
  "report_format": "markdown"
}
```

#### Response

```json
{
  "status": "success",
  "message": "Full pipeline completed successfully",
  "stages": {
    "literature": {
      "document_count": 5,
      "schema_version": "lit.v1"
    },
    "parsing": {
      "disease_code": "HFpEF",
      "inclusion_count": 3,
      "exclusion_count": 2,
      "feature_count": 5
    },
    "mapping": {
      "ehr_source": "mimic",
      "variable_map_count": 5,
      "inclusion_filters_count": 3,
      "exclusion_filters_count": 2
    },
    "cohort": {
      "total_subjects": 150,
      "summary": {...}
    },
    "analysis": {
      "outcome_count": 150,
      "metrics_summary": {...}
    },
    "report": {
      "report_body_length": 2500,
      "figure_count": 3
    }
  }
}
```

---

## Workspace 엔드포인트

### List Projects (`GET /api/projects`)

워크스페이스의 모든 프로젝트를 조회합니다.

#### Response

```json
{
  "projects": [
    {
      "project_id": "hfpef-001",
      "stages": ["lit", "schema", "filters", "cohort", "analysis", "report"],
      "created_at": null
    }
  ],
  "total": 1
}
```

### Get Project (`GET /api/projects/{project_id}`)

특정 프로젝트의 정보를 조회합니다.

### Get Stage Data (`GET /api/workspace/{project_id}/{stage}`)

특정 프로젝트의 단계별 데이터를 조회합니다.

**단계 목록**:
- `lit`: 문헌 코퍼스
- `schema`: Trial Schema
- `filters`: 필터 명세
- `cohort`: 코호트 결과
- `analysis`: 분석 결과
- `report`: 보고서

---

## 데이터 모델

### LiteratureDocument

```typescript
{
  source: string
  identifier: string
  title: string
  abstract: string | null
  full_text: string | null
  fetched_at: datetime
  url: string | null
  metadata: object | null
}
```

### TrialCriterion

```typescript
{
  id: string
  description: string
  category: "inclusion" | "exclusion"
  kind: string
  value: object
}
```

### TrialFeature

```typescript
{
  name: string
  source: string
  unit: string | null
  time_window: [number, number] | null
  metadata: object | null
}
```

### VariableMapping

```typescript
{
  schema_feature: string
  ehr_table: string
  column: string
  concept_id: number | null
  transform: object | null
}
```

### CohortRow

```typescript
{
  subject_id: number | string
  stay_id: number | string | null
  matched_criteria: string[]
  index_time: datetime
  features: object | null
}
```

---

## 에러 처리

모든 엔드포인트는 에러 발생 시 HTTP 500 상태 코드와 함께 다음 형식의 응답을 반환합니다:

```json
{
  "detail": "Error description"
}
```

---

## 워크스페이스 구조

```
workspace/
  └── {project_id}/
        ├── lit/
        │   ├── corpus.jsonl
        │   └── manifest.json
        ├── schema/
        │   └── trial_schema.json
        ├── filters/
        │   ├── filter_spec.json
        │   └── filter_spec.sql (optional)
        ├── cohort/
        │   ├── cohort.json
        │   ├── cohort.parquet
        │   └── summary.json
        ├── analysis/
        │   ├── outcomes.json
        │   ├── outcomes.parquet
        │   └── metrics.json
        └── report/
            ├── report.md
            └── figures/
                └── *.png
```

---

## 환경 변수

- `WORKSPACE_ROOT`: 워크스페이스 루트 디렉터리 (기본값: `./workspace`)
- `CORS_ORIGINS`: CORS 허용 오리진 (기본값: `http://localhost:3000`)

---

## 시작하기

### 서버 실행

```bash
cd /Users/kyh/datathon
source venv/bin/activate
uvicorn rwe_api.main:app --reload --port 8000
```

### API 문서 확인

브라우저에서 `http://localhost:8000/docs` 접속

### 예시 요청

```bash
curl -X POST "http://localhost:8000/api/pipeline/search-lit" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "disease_code": "HFpEF",
    "keywords": ["sacubitril"],
    "sources": ["clinicaltrials"],
    "max_records": 5
  }'
```

---

## 버전 히스토리

- **v0.1.0** (2025-10-12): 초기 버전
  - CLI에서 FastAPI로 완전 마이그레이션
  - documents/cli_modules.md 기반 입출력 명세 구현
  - Pydantic 스키마를 통한 타입 안전성 확보

