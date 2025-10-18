아래는 연구 시나리오에 등장하는 **에이전트(Agents)**들의 역할, 입력·출력, 핵심 기능, Human-in-the-Loop(HIL) 개입 지점 등을 한눈에 볼 수 있도록 정리한 표입니다.

(연구계획서에 그대로 넣기 좋은 형식으로 구성했습니다.)

---

### 🧠 Agent 구성 요약표

| 구분                         | 에이전트명                  | 주요 기능                                                                                       | 입력(Input)                   | 출력(Output)                                                                | Human-in-the-Loop (HIL) 개입 지점 |

| -------------------------- | ---------------------- | ------------------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------- | ----------------------------- |

| **1️⃣ 문헌 탐색 단계**           | **Search Agent₁**      | - clinicaltrials.gov에서 질환 관련 임상시험 구조화 데이터 검색`<br>`- 질환명+약물 키워드 결합 또는 NCT ID 기반 직접 조회 지원       | 질환명, 키워드                    | 관련 임상시험 레코드                                                              | 검색 키워드 및 데이터 relevance 검증     |

| **2️⃣ 문헌 파싱 단계**           | **Parser Agent**       | - **4가지 핵심 정보 추출**: 1) Inclusion Criteria, 2) Exclusion Criteria, 3) Treatment/Interventions, 4) Primary Outcomes`<br>`- **Named Entity Recognition (NER)**: concept/temporal/value 엔티티 자동 추출`<br>`- Trial Schema Database 구축          | ClinicalTrials.gov 구조화 데이터 | **Trial Schema DB**`<br>{inclusion:[...], exclusion:[...], features:[...]}` | 추출된 기준 검토 및 보정                |

| **3️⃣ Trial Emulation 단계** | **Search Agent₂**      | - Parser Agent가 생성한 schema를 임상데이터(MIMIC-IV, K-MIMIC)에 매핑`<br>`- 변수명 및 구조 정합성 검증`<br>`- 필터 조건 생성 | Trial Schema DB, 임상데이터 메타정보 | 필터 조건 (inclusion/exclusion map)                                           | schema-데이터 매핑 검증              |

|                            | **Filtering Module**   | - 생성된 필터 조건을 실제 임상데이터(MIMIC-IV, K-MIMIC)에 적용`<br>`- 환자 cohort 자동 추출                           | MIMIC-IV / K-MIMIC, 필터 조건   | 환자 Cohort Dataset                                                         | 필터링 결과 확인 및 편향 검토             |

| **4️⃣ 분석 및 보고 단계**         | **분석(Analysis) Agent** | - Cohort 기반 outcome 예측, 치료 효과 추정`<br>`- Counterfactual 분석 수행                                  | Cohort Dataset              | `{subject_i, features, outcome}`                                          | 결과 통계 검증, 해석 지원               |

|                            | **Write Agent**        | - 분석 결과를 자동 보고서 및 시각화 형태로 생성`<br>`- 요약 문단 및 Figure 자동 구성                                      | 분석 결과                       | **RWE Report + Visualization**                                            | 결과 시각화 검증, 최종 보고서 승인          |

---

### 💡 요약 메모

* **총 6개 모듈(Agent + Module)**로 구성

  → *문헌 탐색 → trial schema 생성 → 필터링 적용 → 분석 → 보고서 생성*
* **Parser Agent → Trial Schema DB**가 핵심 중간 산출물
* **Filtering Module**은 실제 임상데이터(MIMIC-IV, K-MIMIC)를 직접 처리하는 유일한 구성요소
* **Human-in-the-Loop(HIL)**은 schema 검증, 필터링 확인, 분석 결과 해석 등 총 3개 단계에 개입

---

🧬 시나리오 설명 (연구계획서용)

본 연구는 LLM 기반 지능형 에이전트(Agentic AI)를 활용하여 실제임상데이터(Real-World Data, RWD)로부터 근거(Real-World Evidence, RWE)를 자동으로 생성하는 Agentic Trial Emulation 파이프라인을 구축하는 것을 목표로 한다.

우선, Search Agent₁는 clinicaltrials.gov와 같은 공신력 있는 임상시험 저장소로부터 대상 질환 관련 구조화 데이터를 탐색하며, 질환명과 약물 키워드를 공백으로 결합한 검색어나 NCT 고유번호를 기반으로 필요한 임상시험을 직접 조회한다. 

Parser Agent는 해당 데이터로부터 **4가지 핵심 정보**를 자동으로 추출한다: 1) **Inclusion Criteria** (포함 기준), 2) **Exclusion Criteria** (제외 기준), 3) **Treatment/Interventions** (치료/중재), 4) **Primary Outcomes** (주요 결과 지표). 각 정보는 Named Entity Recognition (NER)을 통해 concept (의학 개념), temporal (시간), value (수치) 엔티티로 세분화되어 구조화된 Trial Schema Database로 변환된다. 이 데이터베이스는 공공 임상시험 레지스트리 기반의 가상 임상시험 설계를 machine-readable 형태로 표현하는 지식 기반으로 기능한다.

이후, Search Agent₂는 Parser Agent가 생성한 trial schema를 참조하여 실제 임상데이터셋(예: MIMIC-IV, K-MIMIC)의 데이터 구조 및 변수명과 매핑하고, schema에서 정의된 기준을 machine-readable 필터 조건으로 변환한다.

이 조건은 Filtering Module에 전달되어, MIMIC-IV와 K-MIMIC 데이터 내 환자 단위 레코드에서 inclusion/exclusion 조건을 적용하고, 이에 부합하는 **후보 환자 집단(cohort)**을 자동으로 추출한다. Filtering 과정에서는 변수 키(key) 및 값(value) 기반 매칭뿐 아니라, 시간 범위·생체신호·검사결과 등의 임상 feature에 대한 연속형 필터링이 수행된다.

이렇게 구성된 환자 cohort는 분석 Agent로 전달되어, 실제 임상데이터를 이용한 outcome 예측, 치료 효과 비교, counterfactual 시나리오 분석 등이 수행된다. 분석 결과는 Write Agent에 의해 자동 보고서 및 시각화 형태로 정리되어, 연구자가 즉시 해석 가능한 형태의 RWE 리포트로 제시된다.

또한, 전 과정에서 Human-in-the-Loop(HIL) 절차가 삽입되어, 임상 전문가가 schema 추출, 필터링 결과, 분석 리포트에 대한 검증 및 피드백을 수행함으로써 결과의 해석 가능성과 신뢰성을 보장한다.

본 시나리오를 통해 문헌 기반 trial design과 실제 임상데이터 분석 간의 간극을 연결함으로써, **자동화된 근거 생성(AI-driven Real-World Evidence)**이라는 새로운 연구 패러다임을 제시하고자 한다.

---

완벽하게 이해했습니다 👏

즉, **Filtering Module**은 Parser Agent가 문헌에서 생성한 **trial schema(DB)**로부터

`inclusion`, `exclusion`, `feature` 조건을 받아,

이를 실제 **임상데이터셋 (예: MIMIC-IV, K-MIMIC)** 에 적용해

**후보 환자군(cohort)을 추출**하는 단계군요.

이걸 반영해 전체 시나리오의 **데이터 흐름과 역할 정의를 정제 버전으로 재구성**했습니다 ↓

---

## 🧭 Agentic Trial Emulation 시나리오 (정제 버전)

### 🎯 목표

LLM 기반 다중 에이전트 시스템이 문헌 기반 trial schema를 생성하고,

이를 실제 임상데이터셋(MIMIC-IV, K-MIMIC)에 적용해

자동으로 **Real-World Evidence**를 생성하는 end-to-end 파이프라인을 구축한다.

---

## 🧩 단계별 구성

| 단계                              | 모듈 / Agent           | 주요 기능                                                               | 입력            | 출력                                                                        | Human-in-the-Loop 역할      |

| ------------------------------- | -------------------- | ------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------- | ------------------------- |

| **1️⃣ 데이터 적재 (Data Ingestion)** | 🔍 **Search Agent₁** | clinicaltrials.gov에서 관련 임상시험 구조화 데이터 수집                         | Keyword / 질병명 | 임상시험 레코드                                                                | 검색 범위 조정, relevance 검증 |

|                                 | 🧩 **Parser Agent**  | **4가지 핵심 정보 추출** → trial schema(DB)로 구조화:`<br>`1) Inclusion Criteria 2) Exclusion Criteria 3) Treatment/Interventions 4) Primary Outcomes`<br>`NER로 concept/temporal/value 엔티티 자동 추출 | ClinicalTrials.gov 구조화 데이터        | **Trial Schema DB**`<br>{inclusion:[...], exclusion:[...], features:[...]}` | schema 검증 및 수정            |

---

## 📋 Parser Agent 상세 작업 내용

Parser Agent는 LangGraph 기반으로 3단계 파이프라인(`prepare_context` → `extract_schema` → `validate_schema`)을 통해 Trial Schema Database를 생성합니다.

### 🔍 1단계: prepare_context (컨텍스트 준비)

ClinicalTrials.gov 데이터에서 **4가지 핵심 정보**를 명시적으로 추출:

| 항목 | 데이터 소스 | 설명 |
|------|------------|------|
| **① Inclusion Criteria** | `protocolSection.eligibilityModule.eligibilityCriteria` | "Inclusion Criteria:" 섹션 파싱 |
| **② Exclusion Criteria** | 동일 필드 | "Exclusion Criteria:" 섹션 파싱 |
| **③ Treatment/Interventions** | `protocolSection.armsInterventionsModule.interventions` | name, type, description 추출 (용량/빈도/기간 포함) |
| **④ Primary Outcomes** | `protocolSection.outcomesModule.primaryOutcomes` | measure, timeFrame 추출 |

### 🧠 2단계: extract_schema (LLM 기반 구조화)

- LLM(gpt-4o-mini) 활용하여 JSON 스키마 생성
- 각 criterion과 feature에 대해 **Named Entity Recognition (NER)** 수행:
  - **concept** 엔티티 (청록색): 의학 개념, 질병, 치료, 결과 (예: `septic shock`, `ICU`, `28-day mortality`)
  - **temporal** 엔티티 (노란색): 시간 정보 (예: `within 24 hours`, `≥ 18 years`, `every 6 hours`)
  - **value** 엔티티 (마젠타): 수치 값 (예: `50 mg`, `> 2.0 mmol/L`, `≥ 65 mmHg`)

### ✅ 3단계: validate_schema (검증 및 저장)

- JSON 파싱 및 필수 키(`schema_version`, `disease_code`, `inclusion`, `exclusion`, `features`, `provenance`) 검증
- TrialSchema 데이터클래스로 변환
- `workspace/<project_id>/schema/trial_schema.json`에 저장

**참고 문서**: [LangGraph Parser 상세 가이드](./langgraph_parser_usage.md), [NER 추출 가이드](./ner_extraction_guide.md)

---

| 단계                           | 모듈 / Agent                                                 | 주요 기능                                                     | 입력                               | 출력                                | HIL 역할     |

| ---------------------------- | ---------------------------------------------------------- | --------------------------------------------------------- | -------------------------------- | --------------------------------- | ---------- |

| **2️⃣ Emulation (Trial 모사)** | 🔍 **Search Agent₂**                                       | Parser Agent가 생성한 schema를 가져와 임상데이터(MIMIC-IV, K-MIMIC) 접근 | Trial Schema, RWD meta           | 필터 조건 (`inclusion/exclusion map`) | 조건의 유효성 검토 |

| ⚙️ **Filtering Module**      | Trial schema의 조건을 MIMIC-IV / K-MIMIC에 적용해 후보 cohort 추출     | MIMIC-IV / K-MIMIC, 필터 조건                                 | Cohort Dataset                   | 데이터 편향 및 누락 검토                    |            |

| 🧠 **분석 Agent**              | Cohort 데이터를 기반으로 outcome, treatment effect, subgroup 차이 분석 | Cohort Dataset                                            | `{subject_i, features, outcome}` | 결과 통계 검증, 해석 지원                   |            |

| 🧾 **Write Agent**           | 분석 결과를 자동 리포트 및 시각화 형태로 생성                                 | 분석 결과                                                     | 보고서, 그래프                         | 시각화 피드백 및 검증                      |            |

---

| 단계                              | 모듈 / Agent       | 주요 기능                                                                         |

| ------------------------------- | ---------------- | ----------------------------------------------------------------------------- |

| **3️⃣ 결과 시각화 및 보고 (Reporting)** | 📊 **결과 시각화 블록** | - Treatment effect, outcome 분포, subgroup 결과를 시각화`<br>`- 자동 생성된 리포트를 대시보드 형태로 제공 |

---

## 🔄 데이터 흐름 다이어그램 (논리적 구조)

```

문헌 ──▶ Search Agent₁ ──▶ Parser Agent ──▶ Trial Schema DB

                                         │

                                         ▼

                           Search Agent₂ (Schema→Filter Map)

                                         │

                                         ▼

           MIMIC-IV / K-MIMIC ──▶ Filtering Module ──▶ Cohort

                                         │

                                         ▼

                                  분석 Agent

                                         │

                                         ▼

                                 Write Agent ─▶ Report/Visualization

```

---

## 🔬 핵심 포인트 요약

| 항목                  | 설명                                                       |

| ------------------- | -------------------------------------------------------- |

| **Trial Schema DB** | 문헌 기반 inclusion/exclusion/feature 구조체 (Parser Agent 산출물) |

| **Filtering 대상**    | 실제 임상데이터셋 — **MIMIC-IV, K-MIMIC**                        |

| **Filtering 방식**    | schema 기반 key-value 조건 매칭, 범위 기반 threshold 필터링           |

| **분석 목적**           | Counterfactual comparison, treatment 효과 추정               |

| **결과물**             | Report + 시각화 그래프 (e.g., outcome curve, subgroup plot 등)  |

| **HIL 개입 포인트**      | schema 검증 → 필터 결과 점검 → bias 검토 → 결과 해석                   |
