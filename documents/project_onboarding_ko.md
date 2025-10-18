# Agentic Trial Emulation CLI 온보딩 가이드

신규 합류한 개발자가 저장소 전반을 빠르게 이해하고, 로컬 환경에서 파이프라인을 실행·확장할 수 있도록 정리한 가이드입니다. 이미 제공된 개별 모듈 문서를 보완해 전체 맥락, 의존성, 확장 포인트까지 한 번에 파악할 수 있도록 구성했습니다.

---

## 1. 프로젝트 개요
- **목적**: 대규모 임상 문헌을 기반으로 Trial Schema를 자동 생성하고, 실제 EHR 데이터를 통해 Real-World Evidence(RWE)를 빠르게 확보하는 Agentic 파이프라인을 CLI 형태로 제공합니다.
- **핵심 가치**: 단계별 플러그인 구조를 통해 연구 흐름(문헌 검색 → Trial 파싱 → EHR 매핑 → Cohort 추출 → 효과 분석 → 보고서화)을 자동화하면서도 구현체 교체가 쉽습니다.
- **주요 특징**
  - LangChain/LangGraph 기반 LLM 파이프라인과 합성(synthetic) 구현체를 공존시켜 네트워크가 없는 환경에서도 개발·테스트 가능
  - `workspace/<project_id>/<stage>/` 구조로 중간 산출물을 관리해 재실행 시에도 캐시처럼 활용
  - `.env` 자동 로딩, `--impl stage=name` 옵션을 통한 구현체 주입 등 운영 친화적 설계

---

## 2. 시스템 아키텍처

### 2.1 파이프라인 단계
| Stage(`cli` 서브커맨드) | 주요 역할 | 대표 입력 | 대표 출력 |
| --- | --- | --- | --- |
| `search-lit` | clinicaltrials.gov에서 임상시험 구조화 데이터 수집 | 질환 코드, 키워드, 소스 | `LitCorpus` (`corpus.jsonl`) |
| `parse-trials` | 문헌을 Trial Schema로 구조화 | 문헌 코퍼스 | `trial_schema.json` |
| `map-to-ehr` | Schema ↔ EHR 변수 매핑, 필터 명세 생성 | Trial Schema, 변수 사전 | `filter_spec.json(.sql)` |
| `filter-cohort` | 필터 명세로 Cohort 추출 | 필터 명세, 데이터 URI | `cohort.json/.parquet` |
| `analyze` | 치료 효과 추정, counterfactual 분석 | Cohort 결과, 분석 옵션 | `metrics.json`, `outcomes.json` |
| `write-report` | 보고서/시각화 번들 생성 | 분석 결과, 템플릿 | `report.md`, `figures/` |

> `run-all` 명령은 위 단계를 순차 실행하며 중간 아티팩트를 재사용합니다.

### 2.2 실행 컨텍스트
- `PipelineContext(project_id, workspace, config, hil_enabled, logger)`가 모든 구현체에 주입됩니다.
- 컨텍스트는 `cli.py`의 `create_context()`에서 생성되며, 워크스페이스 디렉터리를 보장합니다.
- 각 Stage 별 구현체는 `plugins.registry`를 통해 조회됩니다.

---

## 3. 저장소 구조 개요
```
datathon2/
├── src/rwe_cli/           # CLI 및 파이프라인 모듈
│   ├── cli.py             # 엔트리포인트, 서브커맨드 실행 로직
│   ├── config.py          # JSON/YAML 설정 로더
│   ├── context.py         # PipelineContext 정의
│   ├── models.py          # 단계별 데이터 모델, Protocol 정의
│   ├── serialization.py   # JSON/Parquet/텍스트 저장 유틸
│   └── plugins/           # 플러그인 구현체 모음
├── documents/             # 모듈별 상세 문서 (본 가이드는 project_onboarding_ko.md)
├── data/                  # MIMIC-IV 데모 데이터셋 구조
├── templates/             # 보고서 템플릿 (예: default_report.md)
└── workspace/             # 실행 결과 저장소 (프로젝트별 하위 디렉터리)
```

---

## 4. 핵심 모듈 설명
- `cli.py`
  - `build_parser()`에서 전 단계 공통 옵션과 서브커맨드 인자를 정의합니다.
  - `parse_impl_overrides()`/`resolve_impl_name()`으로 `--impl stage=name` 옵션과 설정 파일(`config.project.default_impls`)을 결합합니다.
  - `run_*` 함수가 각 Stage 구현체를 호출하고, 결과를 `serialization` 유틸을 활용해 디스크에 저장합니다.
  - `.env` 파일을 자동 로딩하여 API 키 등 민감 정보 관리가 용이합니다.
- `models.py`
  - 단계별 데이터 구조를 `dataclass`로 정의하고, `LiteratureFetcher`, `TrialParser` 등 Protocol로 인터페이스를 명확히 합니다.
  - 각 Stage가 어떤 입력/출력을 주고받아야 하는지 타입 수준에서 확인할 수 있습니다.
- `serialization.py`
  - JSON/JSONL/텍스트/Parquet 기록을 담당합니다.
  - `pyarrow`가 없을 경우 JSON으로 graceful fallback 하므로 선택적 의존성을 허용합니다.
- `plugins/`
  - `__init__.py`에서 Registry 패턴을 구현해 `synthetic`, `langgraph-*`, `mimic-demo` 등을 등록합니다.
  - 새 구현체를 추가하려면 모듈 생성 → 팩토리 함수 작성 → Registry에 `register_*` 호출을 추가하면 됩니다.

---

## 5. 플러그인 구현체 한눈에 보기
| Stage | 기본 구현체 | 대체 구현체 | 주요 의존성 | 비고 |
| --- | --- | --- | --- | --- |
| Literature (`search-lit`) | `synthetic` | `langgraph-search` | `requests` | clinicaltrials.gov 구조화 데이터 |
| Parser (`parse-trials`) | `synthetic` | `langgraph` | `langgraph`, `langchain`, `langchain-openai` | LLM 체인, JSON 출력 검증 |
| Mapper (`map-to-ehr`) | `synthetic` | `mimic-demo` | `pandas` | 변수사전/Schema 매핑 |
| Cohort (`filter-cohort`) | `synthetic` | `mimic-demo` | `pandas` | MIMIC-IV 데모 CSV 파일 필요 |
| Analyzer (`analyze`) | `synthetic` | (추가 여지) | 기본 내장 RNG | 치료효과 synthetic 산출 |
| Report (`write-report`) | `synthetic` | (추가 여지) | 없음 | 마크다운 템플릿 기반 보고서 |

> Stage 별 alias (`STAGE_ALIAS`): `search-lit→search`, `parse-trials→parser`, `map-to-ehr→mapper`, `filter-cohort→filter`, `analyze→analyzer`, `write-report→report`.

---

## 6. 실행 환경 및 의존성

### 6.1 기본 환경
- 권장 Python 버전: **3.10 이상** (패턴 매칭, `list[str]` 타입힌트 등 최신 문법 사용)
- 패키지 관리는 `pip` 또는 `uv` 등 자유롭게 사용하되, `PYTHONPATH=src` 설정이 필요합니다.
- 필수/선택 의존성 예시:
  ```bash
  pip install langchain langchain-community langchain-openai langgraph \
              requests pandas pymupdf pyarrow
  ```
  - `langchain-openai` 사용 시 OpenAI API 키를 환경 변수 `OPENAI_API_KEY`로 설정합니다.
  - clinicaltrials.gov API는 키 없이 호출 가능하지만, 일시적 오류에 대비해 재시도 로직을 두면 안정적입니다.

### 6.2 설정 파일
- 기본 경로는 `config.yaml`이며 미존재 시 빈 설정(`{}`)으로 동작합니다.
- `project.default_impls`에 Stage 별 기본 구현체를 선언하면 `--impl` 없이도 원하는 플러그인을 선택할 수 있습니다.

### 6.3 데이터 리소스
- `data/` 디렉터리에 PhysioNet MIMIC-IV 데모 CSV가 배치되어 있으며, `documents/mimic_demo_data_usage_ko.md`에서 상세 사용법을 참고합니다.
- 실 데이터 사용 시 `--map-to-ehr` 또는 `--filter-cohort` 단계에서 `--ehr-source`와 `--input-uri`를 적절히 지정해야 합니다.

---

## 7. CLI 실행 흐름 예시
```bash
# 0. PYTHONPATH 설정
export PYTHONPATH=src

# 1. 문헌 검색 (LangGraph 구현체)
python -m rwe_cli --project demo --workspace workspace \
  --impl search-lit=langgraph-search \
  search-lit --disease-code HFpEF \
  --keyword sacubitril --keyword valsartan \
  --source clinicaltrials --max-records 5

# 1-1. 특정 임상시험(NCT) 직접 조회
python -m rwe_cli --project demo --workspace workspace \
  --impl search-lit=langgraph-search \
  search-lit --keyword NCT05818397 --source clinicaltrials

# 2. Trial Schema 생성 (LangGraph parser)
python -m rwe_cli --project demo parse-trials \
  --impl parse-trials=langgraph --llm-provider gpt-4o-mini

# 3. Schema ↔ EHR 매핑
python -m rwe_cli --project demo map-to-ehr \
  --ehr-source mimic --dictionary documents/mimic_lv_feature_schema.md

# 4. Cohort 추출 (데모 데이터)
python -m rwe_cli --project demo filter-cohort \
  --impl filter-cohort=mimic-demo \
  --input-uri data

# 5. 분석 및 보고서
python -m rwe_cli --project demo analyze --estimator ate-synthetic
python -m rwe_cli --project demo write-report --template templates/default_report.md

# 6. (표시용) Stimula What-if
python -m rwe_cli --project demo stimula --vary LVEF_LT=35,40,45 --vary AGE_MIN=50,60
```
- `run-all` 명령을 사용하면 위 명령을 순차 실행하며 `--impl` 옵션도 재활용됩니다.
- 실행 로그는 기본적으로 stdout에 출력되며, 추가 로깅 설정은 `config.yaml`의 `logging` 섹션으로 확장할 수 있습니다.

---

## 8. 워크스페이스 아티팩트 구조
| 경로 | 주요 파일 | 내용 |
| --- | --- | --- |
| `workspace/<project>/lit/` | `corpus.jsonl`, `manifest.json`, `pdf/` | 문헌 원문 및 메타데이터, PMC PDF |
| `workspace/<project>/schema/` | `trial_schema.json` | 추출된 Trial Schema |
| `workspace/<project>/filters/` | `filter_spec.json`, `filter_spec.sql` | EHR 매핑 명세 및 선택적 SQL 표현 |
| `workspace/<project>/cohort/` | `cohort.json`, `cohort.parquet` | 환자 Cohort 스냅샷 |
| `workspace/<project>/analysis/` | `metrics.json`, `outcomes.json` | 분석 지표와 개인별 counterfactual |
| `workspace/<project>/report/` | `report.md`, `figures/*.png` | 마크다운 보고서와 시각화 |

---

## 9. 확장 가이드
- **새 Stage 구현체 추가**
  1. `src/rwe_cli/plugins/<module>.py`에 클래스 구현 (`models` Protocol 준수).
  2. `plugins/__init__.py`에서 `registry.register_<stage>("name", Factory)` 호출 추가.
  3. 필요시 전용 문서를 `documents/`에 작성하고, README나 본 가이드에 링크합니다.
- **인자 확장**
  - `cli.py`의 `build_parser()`에서 서브커맨드 인자를 추가하고, 대응되는 `run_*` 함수에서 전달.
  - 중간 산출물이 필요하면 `serialization.py` 유틸을 활용해 저장 포맷을 통일합니다.
- **HIL 플로우 도입**
  - 현재 `--hil` 플래그는 컨텍스트에 플래그로 전달되며, 구현체 내부에서 체크해 사용자 승인 플로우를 만들 수 있습니다.

---

## 10. 품질 관리 및 테스트 전략
- 현 시점에서는 자동화 테스트가 포함되어 있지 않으므로, 신규 기능 추가 시 다음을 권장합니다.
  - 최소 단위 테스트: 순수 함수(예: `_compose_query`, `_solve_pow`)는 pytest 기반 테스트를 추가.
  - 로컬 통합 테스트: `workspace/test-run` 등 별도 워크스페이스로 `run-all` 실행 후 아티팩트를 검수.
  - 네트워크/외부 API를 사용하는 구현체는 예외 처리를 `RuntimeError` 등으로 감싸 CLI에서 사용자 메시지가 명확히 드러나게 합니다.
- 코드 변경 시 `documents/` 내 관련 문서를 업데이트하여 문서-코드 간 괴리를 줄입니다.

---

## 11. 참고 문서 모음
- `documents/cli_overview.md`: CLI 구조와 파이프라인 플로우 개요
- `documents/cli_design.md`: 설계 배경과 의사결정 기록
- `documents/langgraph_search_usage.md`: LangGraph 문헌 검색 구현체 상세
- `documents/langgraph_parser_usage.md`: LangGraph Trial Parser 사용법
- `documents/mimic_demo_data_usage_ko.md`: MIMIC 데모 데이터셋 활용법
- `documents/mimic_lv_feature_schema.md`: EHR 변수 매핑 참고 스키마
- `documents/description.md`: 전체 Agent 구성 개요 및 연구 시나리오 설명

---

## 12. 자주 묻는 질문(FAQ)
- **Q. clinicaltrials.gov 호출 시 오류가 발생합니다.**  
  A. 일시적인 500/503 응답이 발생할 수 있으므로 짧은 지연을 두고 2~3회 재시도하거나 백오프 전략을 적용하세요.
- **Q. 원문 PDF는 어디에서 확인하나요?**  
  A. Search Agent₁는 구조화된 임상시험 데이터를 수집하며, PDF 다운로드 기능은 제공하지 않습니다. 원문 논문이 필요한 경우 clinicaltrials.gov 레코드에 포함된 참고 링크를 수동으로 확인하세요.
- **Q. 약물 이름만으로 검색이 가능한가요?**  
  A. 가능합니다. `--keyword`에 약물명을 넣으면 자동으로 질환 코드와 결합된 검색어(공백 구분)가 생성되며 Intervention 이름을 중심으로 결과가 반환됩니다. `NCT` ID를 넣으면 해당 임상시험이 직접 반환됩니다.
- **Q. LLM 호출 비용이 걱정됩니다.**  
  A. 개발 초기에는 `synthetic` 구현체를 사용해 전체 파이프라인을 검증한 뒤, 필요한 Stage만 LangGraph 기반 구현체로 교체하세요.
- **Q. 새 API 키를 어떻게 주입하나요?**  
  A. 루트 경로 `.env`에 `OPENAI_API_KEY=...` 형식으로 추가하면 CLI 실행 시 자동으로 환경 변수에 로드됩니다.

---

## 13. 다음 단계 제안
1. `synthetic` 구현체로 `run-all`을 실행해 워크스페이스 구조를 체감합니다.
2. LangGraph 기반 `search-lit` / `parse-trials`로 실제 문헌을 파이프라인에 연결해 봅니다.
3. 필요한 Stage에 대해 신규 구현체를 설계하고, Registry에 등록하며 테스트 케이스를 준비합니다.

필요한 추가 정보가 있다면 언제든 기존 문서나 소스 코드를 참고하고, 팀에 질문을 남겨 주세요. 환영합니다! 🎉
