# Agentic Trial Emulation 모듈 인터페이스 사양

- **목표**: Agentic Trial Emulation 파이프라인 각 모듈이 교체 가능한 코드 레벨 인터페이스를 공유하도록 함수 입출력 계약을 정의한다.
- **전제**: CLI는 단순 오케스트레이션 계층이며, 실제 로직은 본 사양의 추상 클래스/프로토콜을 구현한 코드에서 교체된다. 모든 구현체는 명시된 타입과 반환 값을 준수해야 한다.

---

## 1. 공통 구조

### 1.1 실행 컨텍스트

```python
@dataclass
class PipelineContext:
    project_id: str
    workspace: Path
    config: Mapping[str, Any]
    hil_enabled: bool = False
    logger: logging.Logger | None = None
```

- CLI는 각 모듈 호출 시 `PipelineContext`와 단계별 파라미터 객체를 전달한다.
- 모듈은 반환 객체를 CLI가 직렬화(`json`, `jsonl`, `parquet`)하도록 제공하며, 직접 파일을 쓰지 않는다.

### 1.2 공통 관례

- 함수는 실패 시 예외를 던지고, CLI가 이를 포착해 에러 로그를 기록한다.
- 모든 데이터 클래스는 `schema_version` 필드를 포함해 전/후방 호환성을 명시한다.
- 시간/수치 데이터는 ISO8601 문자열, UTC 타임스탬프, 명시된 단위를 사용한다.
- 구현체는 **파일 I/O를 직접 수행하지 않고** 반환 객체만 구성한다. 파일 저장, 스트리밍, 직렬화는 오케스트레이션 계층에서 처리한다.
- 반환 객체는 불변(immutable) 데이터 클래스로 취급하며, `ctx`나 공유 상태를 직접 수정하지 않는다.

---

## 2. Search Agent₁ (`search-lit`)

문헌 검색 기능을 제공하는 모듈.

### 2.1 데이터 타입

```python
@dataclass
class SearchLitParams:
    disease_code: str
    keywords: list[str]
    sources: list[str]  # 예: ["clinicaltrials"]
    max_records: int
    api_keys: Mapping[str, str] | None = None

@dataclass
class LiteratureDocument:
    source: str
    identifier: str
    title: str
    abstract: str | None
    full_text: str | None
    fetched_at: datetime.datetime
    url: str | None = None
    metadata: Mapping[str, Any] | None = None

@dataclass
class LiteratureCorpus:
    schema_version: str
    documents: Sequence[LiteratureDocument]
```

#### 입력 계약

| 파라미터 | 타입 | 필수 | 설명 |
| -------- | ---- | ---- | ---- |
| `params.disease_code` | `str` | Y | 대상 질환 코드 또는 약어 (예: `HFpEF`) |
| `params.keywords` | `list[str]` | Y | 검색 키워드 목록, 약물명이나 `NCT` ID를 포함할 수 있음 |
| `params.sources` | `list[str]` | Y | 지원 소스 식별자. 현재는 `clinicaltrials`만 허용되며, 다른 값은 무시됨 |
| `params.max_records` | `int` | Y | 1 이상 정수, 초과 시 자동 절단 |
| `params.api_keys` | `Mapping[str, str]` | N | (선택) 향후 인증용 키. 현재 clinicaltrials.gov는 키 없이 호출 가능 |
| `ctx` | `PipelineContext` | Y | 프로젝트 메타 정보. `ctx.workspace`는 존재하는 디렉터리여야 함 |

#### 출력 계약

- 반환 타입: `LiteratureCorpus`
- `schema_version`: `"lit.v1"` 고정 또는 향후 버전 문자열
- `documents`: 길이 ≤ `params.max_records`이며, 각 항목은 아래 조건을 만족
  - `identifier`는 소스 내 유일 키(PMID, NCT ID 등)
  - `fetched_at`은 UTC 타임존 정보 포함
  - 텍스트 필드(`title`, `abstract`, `full_text`)는 UTF-8 인코딩 가능한 문자열
- CLI 직렬화: `documents`를 `workspace/lit/<project_id>/corpus.jsonl`에 JSON Lines 형태로 저장
- 키워드에 `NCT` ID를 포함하면 해당 임상시험이 직접 조회되며 질환 코드가 없어도 동작
- 질환 코드와 키워드 문자열은 공백으로 결합된 하나의 쿼리로 clinicaltrials.gov에 전달된다.


### 2.2 함수 시그니처

```python
class LiteratureFetcher(Protocol):
    def run(self, params: SearchLitParams, ctx: PipelineContext) -> LiteratureCorpus: ...
```

- 구현체는 API 호출, 캐시 사용 등을 자유롭게 선택하되, 반환 객체는 `LiteratureCorpus`여야 한다.
- CLI는 반환된 corpus를 `workspace/lit/<project_id>/corpus.jsonl`로 직렬화한다.

---

## 3. Parser Agent (`parse-trials`)

문헌에서 Trial Schema를 추출한다.

### 3.1 데이터 타입

```python
@dataclass
class ParseTrialsParams:
    llm_provider: str
    prompt_template: str
    validation_resources: Mapping[str, Any] | None = None

@dataclass
class TrialCriterion:
    id: str
    description: str
    category: str        # inclusion | exclusion
    kind: str            # demographic | clinical | lab | etc.
    value: Mapping[str, Any]

@dataclass
class TrialFeature:
    name: str
    source: str
    unit: str | None
    time_window: tuple[int, int] | None
    metadata: Mapping[str, Any] | None = None

@dataclass
class TrialSchema:
    schema_version: str
    inclusion: Sequence[TrialCriterion]
    exclusion: Sequence[TrialCriterion]
    features: Sequence[TrialFeature]
    metadata: Mapping[str, Any]
```

### 3.2 함수 시그니처

```python
class TrialSchemaExtractor(Protocol):
    def run(
        self,
        params: ParseTrialsParams,
        ctx: PipelineContext,
        corpus: LiteratureCorpus,
    ) -> TrialSchema: ...
```

- 입력 corpus는 Search 모듈의 반환값을 그대로 사용한다.
- CLI는 결과를 `workspace/schema/<project_id>/trial_schema.json`으로 저장한다.

#### 입력 계약

| 파라미터 | 타입 | 필수 | 설명 |
| -------- | ---- | ---- | ---- |
| `params.llm_provider` | `str` | Y | 사용 LLM 또는 엔진 식별자. 구현체는 지원 목록을 검증 |
| `params.prompt_template` | `str` | Y | 추출 프롬프트 템플릿 경로 또는 식별자 |
| `params.validation_resources` | `Mapping[str, Any]` | N | 온톨로지, 용어집 등 보조 자료. `validation_resources["feature_schema"]`에 `mimic_lv_feature_schema` 경로 전달 시 해당 스키마를 로드해 피처 유효성 검사 수행 |
| `corpus.schema_version` | `str` | Y | `"lit.v1"` 등 지원 버전. 미지원 시 `UnsupportedSchemaVersion` |
| `corpus.documents` | `Sequence[LiteratureDocument]` | Y | 최소 1개 이상. |
| `ctx` | `PipelineContext` | Y | `ctx.config`에서 추가 하이퍼파라미터를 참조 가능 |

#### 출력 계약

- 반환 타입: `TrialSchema`
- `schema_version`: `"schema.v1"` 고정 (또는 향후 버전)
- `inclusion` 및 `exclusion` 항목 조건
  - `id` 고유 문자열 (`inc_01` 형식 권장)
  - `category`는 `inclusion`/`exclusion` 중 하나로 자동 설정
  - `value`는 JSON 직렬화 가능한 딕셔너리이며 단위 명시 필요
- `features`
  - `time_window`는 `(start_hour, end_hour)` 튜플. start ≤ end
  - `metadata`에는 문헌 근거(`"source_ids": [...]`) 포함 권장
- `metadata`
  - 최소 키: `"disease_code"`, `"literature"` (문헌 ID 리스트)
- **도메인 스키마 연계**: 좌심실 초음파 기반 연구의 경우 `metadata["feature_schema"]`에 `mimic-lv.v1` 등 스키마 식별자를 포함하고, `TrialFeature` 중 `source == "mimic_lv"` 항목은 `documents/mimic_lv_feature_schema.md`에 정의된 필드명과 일치해야 한다.
- CLI 직렬화: JSON 한 개 파일, UTF-8, 프리티 프린트 옵션 사용
- 유효성 실패 시 `SchemaExtractionError` 예외를 발생시켜야 한다.

---

## 4. Search Agent₂ (`map-to-ehr`)

Trial Schema를 실제 EHR 구조에 매핑해 필터 명세를 생성한다.

### 4.1 데이터 타입

```python
@dataclass
class MapToEHRParams:
    ehr_source: str             # 예: "mimic", "k-mimic"
    variable_dictionary: Mapping[str, Any]
    output_format: Literal["json", "sql"] = "json"

@dataclass
class VariableMapping:
    schema_feature: str
    ehr_table: str
    column: str
    concept_id: int | None
    transform: Mapping[str, Any] | None = None

@dataclass
class FilterExpression:
    criterion_id: str
    expr: Mapping[str, Any]     # 내부 DSL (op, field, value 등)

@dataclass
class FilterSpec:
    schema_version: str
    ehr_source: str
    variable_map: Sequence[VariableMapping]
    inclusion_filters: Sequence[FilterExpression]
    exclusion_filters: Sequence[FilterExpression]
    lineage: Mapping[str, Any]
```

### 4.2 함수 시그니처

```python
class EHRMapper(Protocol):
    def run(
        self,
        params: MapToEHRParams,
        ctx: PipelineContext,
        schema: TrialSchema,
    ) -> FilterSpec: ...
```

- CLI는 `FilterSpec`을 JSON 또는 SQL 텍스트로 직렬화해 `workspace/filters/<project_id>/filter_spec.*`에 저장한다.

#### 입력 계약

| 파라미터 | 타입 | 필수 | 설명 |
| -------- | ---- | ---- | ---- |
| `params.ehr_source` | `str` | Y | 지원 데이터 소스 식별자 (`"mimic"`, `"k-mimic"` 등) |
| `params.variable_dictionary` | `Mapping[str, Any]` | Y | 테이블·컬럼 메타데이터. 필수 키(`tables`, `mappings`) 존재 |
| `params.output_format` | `Literal["json","sql"]` | Y | 직렬화 대상 포맷. 구현체는 지원 여부 확인 |
| `schema.schema_version` | `str` | Y | `"schema.v1"` 등 지원 버전 |
| `schema.inclusion/exclusion` | `Sequence[TrialCriterion]` | Y | 비어 있으면 `ValueError` |
| `ctx.config["datasources"]` | `Mapping[str, Any]` | N | 연결 정보 사용 가능 |

#### 출력 계약

- 반환 타입: `FilterSpec`
- `schema_version`: `"filters.v1"` 고정
- `variable_map`
  - `schema_feature`는 TrialFeature 이름과 일치해야 한다.
  - `concept_id` 없음 허용(`None`), 단 `transform`에 단위 변환 정의 필요 시 포함.
- `inclusion_filters`/`exclusion_filters`
  - `expr` 필드 구조: `{ "table": str, "field": str, "op": str, "value": Any }`
  - 지원 연산자: `["=", "!=", ">", ">=", "<", "<=", "in", "between", "exists"]`
  - 연산자 미지원 시 `UnsupportedFilterExpression` 예외
- `lineage` 필수 키: `"schema_version"`, `"generated_at"`(ISO8601), `"mapper_impl"`
- CLI 직렬화:
  - `output_format="json"` → JSON 파일
  - `output_format="sql"` → SQL 문자열을 `.sql` 파일에 저장

---

## 5. Filtering Module (`filter-cohort`)

필터 명세를 적용해 코호트를 구축한다.

### 5.1 데이터 타입

```python
@dataclass
class FilterCohortParams:
    input_uri: str              # duckdb://, postgres://, parquet:// 등
    sample_size: int | None = None
    dry_run: bool = False
    parallelism: int = 1

@dataclass
class CohortRow:
    subject_id: int | str
    stay_id: int | str | None
    matched_criteria: Sequence[str]
    index_time: datetime.datetime
    features: Mapping[str, Any] | None = None

@dataclass
class CohortResult:
    schema_version: str
    rows: Iterable[CohortRow]
    summary: Mapping[str, Any]
```

### 5.2 함수 시그니처

```python
class CohortExtractor(Protocol):
    def run(
        self,
        params: FilterCohortParams,
        ctx: PipelineContext,
        filter_spec: FilterSpec,
    ) -> CohortResult: ...
```

- CLI는 `rows`를 Parquet으로 변환하여 `workspace/cohort/<project_id>/cohort.parquet`에 저장하고, `summary`를 JSON으로 기록한다.

#### 입력 계약

| 파라미터 | 타입 | 필수 | 설명 |
| -------- | ---- | ---- | ---- |
| `params.input_uri` | `str` | Y | 데이터 접근 경로. 지원 스킴인지 확인 (duckdb/postgres/parquet 등) |
| `params.sample_size` | `int` | N | 양수일 경우 상위 N개 레코드만 반환 |
| `params.dry_run` | `bool` | N | `True` 시 실제 질의 실행 없이 실행 가능 여부만 검증 |
| `params.parallelism` | `int` | N | 1 이상 정수. 구현체가 지원하지 않으면 무시 또는 경고 |
| `filter_spec.schema_version` | `str` | Y | `"filters.v1"` 필요. |
| `filter_spec.inclusion_filters` | `Sequence[FilterExpression]` | Y | 최소 1개 이상. |
| `ctx.config["datasources"]` | `Mapping[str, Any]` | N | 연결 자격 증명/옵션을 꺼내 사용 |

#### 출력 계약

- 반환 타입: `CohortResult`
- `schema_version`: `"cohort.v1"`
- `rows`
  - `Iterable`이지만 반복 가능한 객체(iterator 재사용 가능 여부 문서화 필요)
  - `matched_criteria`는 `criterion_id` 목록
  - `index_time`은 UTC `datetime`
- `summary` 필수 키: `"total_subjects"`, `"exclusion_counts"`, `"generated_at"`
- `dry_run=True`일 때
  - `rows`는 빈 시퀀스
  - `summary["dry_run"] = true` 포함
- CLI 직렬화는 다음 스키마 준수
  - Parquet 컬럼: `subject_id`, `stay_id`, `matched_criteria`(LIST<STRING>), `index_time`(TIMESTAMP), `features`(MAP<STRING,VALUE> Optional)

---

## 6. 분석 Agent (`analyze`)

코호트 기반 분석 및 counterfactual 평가를 수행한다.

### 6.1 데이터 타입

```python
@dataclass
class AnalyzeParams:
    treatment_column: str
    outcome_column: str
    estimators: Sequence[str]
    feature_config: Mapping[str, Any] | None = None
    log_to: str | None = None

@dataclass
class OutcomeRecord:
    subject_id: int | str
    propensity: float | None
    ate: float | None
    cate_group: str | None
    predicted_outcome: float | None
    metadata: Mapping[str, Any] | None = None

@dataclass
class AnalysisMetrics:
    schema_version: str
    outcomes: Iterable[OutcomeRecord]
    metrics: Mapping[str, Any]
```

### 6.2 함수 시그니처

```python
class OutcomeAnalyzer(Protocol):
    def run(
        self,
        params: AnalyzeParams,
        ctx: PipelineContext,
        cohort: CohortResult,
    ) -> AnalysisMetrics: ...
```

- CLI는 `outcomes`를 Parquet으로, `metrics`를 JSON으로 직렬화해 `workspace/analysis/<project_id>/...`에 저장한다.

#### 입력 계약

| 파라미터 | 타입 | 필수 | 설명 |
| -------- | ---- | ---- | ---- |
| `params.treatment_column` | `str` | Y | 코호트 데이터 내 치료 변수 이름 |
| `params.outcome_column` | `str` | Y | 코호트 데이터 내 결과 변수 이름 |
| `params.estimators` | `Sequence[str]` | Y | 사용할 추정기 식별자 목록. 비어 있으면 `ValueError` |
| `params.feature_config` | `Mapping[str, Any]` | N | 전처리/파생변수 설정 |
| `params.log_to` | `str` | N | 실험 관리 시스템 URI. 지원 포맷이 아니면 `UnsupportedLoggingTarget` |
| `cohort.schema_version` | `str` | Y | `"cohort.v1"` 필요 |
| `cohort.rows` | `Iterable[CohortRow]` | Y | 최소 1개 이상, 아니면 `EmptyCohortError` |
| `ctx` | `PipelineContext` | Y | 난수 시드, 공통 설정 등에 접근 가능 |

#### 출력 계약

- 반환 타입: `AnalysisMetrics`
- `schema_version`: `"analysis.v1"`
- `outcomes` 조건
  - 각 `subject_id`는 입력 코호트와 동일하게 유지
  - `propensity`, `ate`, `predicted_outcome`는 NaN 대신 `None` 사용
  - `metadata`에 모델별 세부 지표 포함 가능 (예: SHAP 값)
- `metrics` 필수 키: `"estimators"`(사용 추정기 리스트), `"generated_at"`, `"summary"`
- CLI 직렬화: Parquet 컬럼 (`subject_id`, `propensity`, `ate`, `cate_group`, `predicted_outcome`), JSON(`metrics`)

---

## 7. Write Agent (`write-report`)

분석 결과를 보고서와 시각화로 변환한다.

### 7.1 데이터 타입

```python
@dataclass
class WriteReportParams:
    template_path: Path
    output_format: Literal["markdown", "pdf"] = "markdown"
    hil_review: bool = False

@dataclass
class FigureArtifact:
    name: str
    description: str | None
    data: bytes            # 이미지 바이너리
    media_type: str        # 예: "image/png"

@dataclass
class ReportBundle:
    schema_version: str
    report_body: str       # Markdown 본문
    figures: Sequence[FigureArtifact]
    extra_files: Sequence[tuple[str, bytes]] | None = None
```

### 7.2 함수 시그니처

```python
class ReportGenerator(Protocol):
    def run(
        self,
        params: WriteReportParams,
        ctx: PipelineContext,
        analysis: AnalysisMetrics,
    ) -> ReportBundle: ...
```

- CLI는 `report_body`를 `report.md`, `figures`를 개별 파일로 저장하고, PDF 변환은 별도 유틸리티를 통해 수행한다.

#### 입력 계약

| 파라미터 | 타입 | 필수 | 설명 |
| -------- | ---- | ---- | ---- |
| `params.template_path` | `Path` | Y | 템플릿 파일 경로. 존재하지 않을 경우 `FileNotFoundError` |
| `params.output_format` | `Literal["markdown","pdf"]` | Y | CLI가 후처리할 대상 포맷 |
| `params.hil_review` | `bool` | N | `True` 시 초안 승인 절차 필요 |
| `analysis.schema_version` | `str` | Y | `"analysis.v1"` 필요 |
| `analysis.outcomes` | `Iterable[OutcomeRecord]` | Y | 최소 1개 이상의 레코드. |
| `ctx` | `PipelineContext` | Y | 보고서 메타 정보(`project_id` 등) 제공 |

#### 출력 계약

- 반환 타입: `ReportBundle`
- `schema_version`: `"report.v1"`
- `report_body`
  - Markdown 표준 준수, UTF-8
  - 헤더에 프로젝트 식별자 및 생성 일시 포함 권장
- `figures`
  - `name`은 파일명 안전 문자열 (공백 대신 `-`)
  - `data`는 바이너리. CLI가 파일로 기록
  - `media_type`은 MIME 타입(`image/png`, `image/svg+xml`, ...)
- `extra_files`
  - `(상대경로, bytes)` 튜플 목록. 필요 없으면 `None`
- CLI 직렬화:
  - Markdown → `report.md`
  - `figures` → `figures/<name>.<ext>`
  - `output_format="pdf"`일 경우, CLI가 별도 렌더러 호출

---

## 8. 확장 및 검증 가이드

- **플러그인 등록**: 각 프로토콜 구현체는 `rwe.plugins.<stage>` 네임스페이스에 등록하여 동적 로딩한다.
- **유닛 테스트**: 구현체별로 `run()` 함수가 기대 타입을 반환하는지, 필수 필드가 채워졌는지 검증한다.
- **스키마 검증**: `pydantic` 또는 `jsonschema` 기반 검증기를 활용해 직렬화 전후 동일성을 확보한다.
- **버전 호환성**: `schema_version` 변경 시 마이그레이션 함수를 제공하고, CLI에 호환 가능 버전을 명시한다.
- **에러 처리**: 공통 예외(`ModuleExecutionError`)를 상속받아 구현체별 상세 원인을 포함하도록 한다.
- **직렬화 규약**: CLI는 반환 객체를 `asdict()` 혹은 커스텀 인코더로 JSON/Parquet화한다. 구현체는 `bytes` 필드 외에 직렬화 불가 타입을 반환하지 않는다.
- **로깅/추적**: 심각한 오류 전 `ctx.logger`에 구조화 로그를 기록하고, `summary`/`metrics`에 `generated_at` 포함.

--- 

## 9. 체크리스트

- [ ] 각 단계 프로토콜과 데이터 클래스 정의
- [ ] 직렬화/역직렬화 유틸리티 구현
- [ ] 플러그인 디스커버리 및 등록 메커니즘 구축
- [ ] 타입/스키마 검증을 포함한 테스트 스위트 작성
- [ ] HIL 단계에서 사용할 프롬프트/검토 훅 구현
