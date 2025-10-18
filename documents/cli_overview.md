# Agentic Trial Emulation CLI 개요

- **목표**: `description.md`에 기반한 Agentic Trial Emulation 파이프라인의 CLI 중심 운영 틀 제공.
- **스코프**: 파이프라인 흐름, CLI 구조, 워크스페이스 구성, 설정, Human-in-the-Loop(HIL) 처리 및 실행 시나리오.

---

## 1. 전체 파이프라인 흐름

```
┌────────────┐ → ┌────────────────┐ → ┌──────────────┐ → ┌──────────────┐
│ search-lit │   │ parse-trials   │   │ map-to-ehr   │   │ filter-cohort│
└────────────┘   └────────────────┘   └──────────────┘   └──────────────┘
                                                                      │
                                                                      ▼
                                                            ┌────────────────┐
                                                            │ analyze-outcome│
                                                            └────────────────┘
                                                                      │
                                                                      ▼
                                                            ┌──────────────┐
                                                            │ write-report │
                                                            └──────────────┘
```

- 각 단계는 독립 CLI 서브커맨드로 구현되어 교체 가능성을 유지한다.
- 중간 산출물은 워크스페이스에 저장되어 추후 재사용 및 검증이 용이하다.

---

## 2. CLI 엔트리포인트

### 2.1 명령 구조

```
rwe --project <project_id> [global options] <subcommand> [args]
```

| 서브커맨드         | 설명                                                         |
| ---------------- | ------------------------------------------------------------ |
| `search-lit`     | 문헌 검색 및 코퍼스 생성                                       |
| `parse-trials`   | 문헌 기반 Trial Schema DB 생성                                |
| `map-to-ehr`     | Trial Schema ↔ EHR 매핑 및 필터 명세 생성                      |
| `filter-cohort`  | 필터 명세 기반 환자 코호트 추출                               |
| `analyze`        | 효과 추정 및 counterfactual 분석 수행                         |
| `write-report`   | 분석 결과 보고서 및 시각화 산출                               |
| `run-all`        | 전체 파이프라인 오케스트레이션 (필요 시 HIL 단계 포함)        |

### 2.2 공통 옵션

| 옵션                  | 타입         | 기본값             | 설명                                                                  |
| ------------------- | ----------- | ---------------- | ------------------------------------------------------------------- |
| `--config PATH`     | Path        | `./config.yaml`   | 데이터소스, API 키, 실행 파라미터 등을 관리하는 전역 설정 파일         |
| `--workspace PATH`  | Path        | `./workspace`     | 중간 산출물 저장 디렉터리 (stage별 하위 폴더 자동 생성)                |
| `--impl NAME`       | String      | stage별 default   | 교체 가능한 구현체 식별자 (예: `parser-llm`, `filter-duckdb`)         |
| `--hil`             | Flag        | 비활성            | HIL 승인 플로우 활성화                                                |
| `--metadata PATH`   | Path or URI | 없음              | 추가 메타데이터(예: 변수 사전) 경로                                   |

---

## 3. 워크스페이스 및 설정 구조

### 3.1 워크스페이스 디렉터리

```
workspace/
  └── <project_id>/
        ├── lit/
        ├── schema/
        ├── filters/
        ├── cohort/
        ├── analysis/
        └── report/
```

- 서브커맨드는 `workspace/<project_id>/<stage>/` 하위에 아티팩트를 저장한다.
- 동일 구조를 유지하여 구현체 교체 시 호환성 확보.

### 3.2 설정 파일 (`config.yaml`) 예시

```yaml
project:
  default_impls:
    search: "langgraph-search"
    parser: "gpt-4o-mini"
    mapper: "ontology-map-v1"
    filter: "duckdb"
    analyzer: "econml-dr"
    report: "jinja-markdown"
  hil:
    enable: false
    prompt_timeout_sec: 300
datasources:
  mimic:
    type: "duckdb"
    uri: "duckdb:///path/to/mimic.duckdb"
  k-mimic:
    type: "postgres"
    uri: "postgresql://user:pass@host:5432/kmimic"
logging:
  level: "INFO"
  file: "workspace/logs/{project_id}.log"
```

### 3.3 메타데이터 스키마 예시

- **EHR 변수 사전 (`ehr_dictionary.json`)**
  ```json
  {
    "tables": {
      "labevents": {
        "columns": {
          "itemid": {"description": "LOINC code", "concepts": ["BNP"]},
          "valuenum": {"unit": "pg/mL"}
        }
      }
    },
    "mappings": {
      "BNP": {"concept_id": 50822, "preferred_unit": "pg/mL"}
    }
  }
  ```
- **피처 설정 (`features.yaml`)**
  ```yaml
  transformations:
    baseline_bnp:
      source: "labevents"
      window_hours: [-24, 0]
      agg: "latest"
  ```

---

## 4. Human-in-the-Loop(HIL) 처리

| 단계             | 트리거                                     | CLI 동작                                       |
| ---------------- | ------------------------------------------ | --------------------------------------------- |
| Schema 검증      | `parse-trials` 완료 후                     | Trial Schema 요약 출력 및 승인 여부 질의        |
| 필터 결과 검토   | `filter-cohort` 실행 후                    | 코호트 요약 및 샘플 미리보기 제공, 승인 대기    |
| 결과 해석        | `analyze` 종료 후                          | 주요 통계 지표 표시, 보고서 생성 여부 확인      |
| 최종 보고서 승인 | `write-report` 실행 전 (`--hil` 활성 시)   | Draft 마크다운 경로 안내, 승인 시 PDF 변환 진행 |

- HIL 프롬프트는 `PromptManager` 모듈로 위임해 CLI ↔ 웹 전환이 가능하도록 설계한다.

---

## 5. 실행 시나리오 예시

```bash
# 1. 문헌 검색
rwe --project hfpef-001 search-lit \
  --disease-code "HFpEF" \
  --keywords "sacubitril valsartan randomized" \
  --sources clinicaltrials

# 단일 임상시험 조회 예시
rwe --project hfpef-001 search-lit --keyword NCT05818397 --sources clinicaltrials

# 2. Trial Schema 생성
rwe --project hfpef-001 parse-trials --llm-provider gpt-4o

# 3. EHR 매핑
rwe --project hfpef-001 map-to-ehr --ehr-source mimic --metadata configs/mimic_dict.json

# 4. 코호트 필터링 (HIL 승인 포함)
rwe --project hfpef-001 filter-cohort --input-uri duckdb:///data/mimic.duckdb --hil

# 5. 분석 및 보고
rwe --project hfpef-001 analyze --treatment-column treatment --outcome-column mortality_30d
rwe --project hfpef-001 write-report --template docs/report_template.md --format pdf

# 6. (표시용) Stimula What-if
rwe --project hfpef-001 stimula --vary LVEF_LT=35,40,45 --vary AGE_MIN=50,60
```

---

## 6. 향후 확장 포인트

- 다중 프로젝트 배치 실행 (`rwe run-all --project-list`).
- Airflow, Prefect와의 스케줄링 연동.
- 감사 로그 및 PHI 마스킹 옵션을 통한 규정 준수 강화.
- 온프레미스 모델, 규칙 기반 엔진 등으로 모듈 교체 시 동일 I/O 계약 유지.
- CLI 컴포넌트를 gRPC/REST API로 래핑하여 웹 오케스트레이터와 연계.

---

## 7. 구현 체크리스트

- [ ] `rwe` CLI 엔트리포인트 및 공통 옵션 처리
- [ ] 워크스페이스 디렉터리 초기화 유틸리티
- [ ] 설정/메타데이터 로딩 모듈
- [ ] HIL 프롬프트 매니저 및 로깅
- [ ] 전체 실행 로그 및 에러 처리 표준화
