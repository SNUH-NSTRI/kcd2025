# Trialist Agent 개요

**버전**: 1.0
**작성일**: 2025-10-13
**상태**: Stage 1 운영 중, Stage 2-3 개발 중

---

## 📌 Trialist란?

**Trialist**는 임상시험 프로토콜 문서를 기계가 읽을 수 있는 구조화된 형식으로 변환하는 고급 파서입니다. AI 기반 자연어 처리(NLP)를 사용하여 임상시험 문서에서 의학 개념을 추출하고, 분류하고, 표준화합니다.

### 핵심 가치

- **자동 추출**: 자유 텍스트 적격성 기준을 구조화된 데이터로 변환
- **도메인 분류**: 의학 개념을 12개 임상 도메인으로 분류
- **표준화**: UMLS 및 OMOP CDM 표준에 개념 매핑
- **향상된 정밀도**: 기존 3-type 시스템 대비 12-domain 분류
- **EHR 통합 준비**: EHR 직접 쿼리용 출력 형식

---

## 🏗️ 아키텍처

Trialist는 **3단계 파이프라인** 구조:

```
임상시험 텍스트
    ↓
[Stage 1: 향상된 NER] ✅ 운영 중
- 12개 도메인 분류
- 세분화된 엔티티 파싱
- 신뢰도 점수 부여
    ↓
[Stage 2: 표준화] ⚠️ 부분 구현
- UMLS 개념 매핑
- 시간 표현 정규화
- 동의어 해결
    ↓
[Stage 3: CDM 매핑] 🚧 Placeholder
- OMOP 코드 할당
- 어휘 체계 선택
- 코드 검증
    ↓
향상된 시험 스키마
```

---

## 🎯 주요 기능

### 1. 12-도메인 분류 시스템

| 도메인 | 설명 | 예시 |
|--------|------|------|
| **Demographic** | 환자 특성 | 나이, 성별, 인종 |
| **Condition** | 질병 및 진단 | 고혈압, 당뇨병, 패혈성 쇼크 |
| **Device** | 의료 장비 | 심박조율기, 인공호흡기 |
| **Procedure** | 의료 시술 | 수술, 생검, 삽관 |
| **Drug** | 약물 | 하이드로코르티손, 아스피린 |
| **Measurement** | 검사 수치 | 혈압, 혈당, 크레아티닌 |
| **Observation** | 임상 관찰 | ICU 입원, 입원 기간 |
| **Visit** | 의료 방문 | 외래, 응급실 |
| **Negation_cue** | 부정 표현 | 없음, 제외 |
| **Temporal** | 시간 표현 | 24시간 이내, 지난 3개월 |
| **Quantity** | 수치+단위 | 50mg, 140mmHg |
| **Value** | 독립 숫자 | 18, 3.5, >2.0 |

### 2. 처리 규칙

#### 최대 세분화
복합 개념을 개별 구성 요소로 분리:
- **입력**: "비타민 C, 하이드로코르티손, 또는 티아민에 대한 알레르기"
- **출력**: 3개의 별도 알레르기 개념

#### 추론
암시적 개념 추가:
- **입력**: "18세 미만 환자"
- **출력**: 명시적 "나이" 개념 추가

#### 맥락 보존
개념과 수식어 간의 관계 유지

### 3. 신뢰도 점수

각 엔티티는 신뢰도 점수 받음 (0.0-1.0):
- **0.9-1.0**: 높은 신뢰도 (정확한 의학 용어)
- **0.7-0.9**: 중간 신뢰도 (일반 약어)
- **0.5-0.7**: 낮은 신뢰도 (모호하거나 추론된)
- **<0.5**: 매우 낮은 신뢰도 (수동 검토 필요)

---

## 🚀 빠른 시작

### 전제 조건

```bash
# Python 환경
python 3.9+

# OpenAI API 키
export OPENAI_API_KEY=your_key_here
```

### 설치

```bash
# 의존성 설치
pip install -r requirements-api.txt

# 서버 시작
npm run backend  # 백엔드 (포트 8000)
```

### 기본 사용법

```python
from pipeline.plugins import registry
from pipeline.context import PipelineContext
from pipeline.models import ParseTrialsParams

# 1. Trialist 파서 가져오기
parser = registry.get_parser('trialist')

# 2. 컨텍스트 생성
context = PipelineContext(
    project_id="test_project",
    workspace="./workspace"
)

# 3. 파서 실행
result = parser.run(params, context, corpus)

# 4. 결과 확인
print(f"포함 기준: {len(result.inclusion)}")
print(f"제외 기준: {len(result.exclusion)}")
print(f"도메인 통계: {result.domain_statistics}")
```

### API 사용

```bash
# 시험 파싱
curl -X POST "http://localhost:8000/api/pipeline/parse-trials" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "nct03389555"}'

# Trialist 정보 조회
curl "http://localhost:8000/api/trialist/info"
```

---

## 📊 출력 형식

### 향상된 시험 스키마

```json
{
  "schema_version": "trialist.v1",
  "disease_code": "enhanced_trial",
  "inclusion": [
    {
      "id": "inc_1",
      "description": "18세 이상 성인 환자",
      "entities": [
        {
          "text": "성인",
          "domain": "Demographic",
          "confidence": 0.95,
          "standard_name": "Adult",
          "umls_cui": "C0001675"
        }
      ]
    }
  ],
  "domain_statistics": {
    "Demographic": 3,
    "Condition": 8,
    "Drug": 5
  }
}
```

### 단계별 출력 파일

```
workspace/{project_id}/trialist_output/
├── stage1_ner_output.json           # NER 결과
├── stage2_standardization_output.json # 표준화된 개념
└── stage3_cdm_mapping_output.json    # CDM 코드
```

---

## ⚠️ 현재 제한사항

### 구현 상태

| 기능 | 상태 | 완성도 |
|------|------|--------|
| Stage 1: 향상된 NER | ✅ 운영 중 | 95% |
| Stage 2: 표준화 | ⚠️ 프로토타입 | 32% |
| Stage 3: CDM 매핑 | 🚧 Placeholder | 10% |

### 알려진 제한사항

#### 1. 어휘 커버리지 (~3%)
- 약 30개 의학 개념만 실제 UMLS 매핑 보유
- 대부분 개념은 퍼지 매칭 또는 placeholder 사용
- **영향**: 희귀 질환에 대한 제한적 표준화

#### 2. Placeholder CDM 코드
- Stage 3는 해시 기반 가짜 코드 생성
- 실제 EHR 쿼리에 사용 불가
- **영향**: 실제 의료 데이터베이스 쿼리 불가

#### 3. API 통합 미구현
- UMLS API 클라이언트 없음
- OHDSI Athena API 통합 없음
- **영향**: 하드코딩된 어휘를 넘어서 확장 불가

#### 4. 언어 지원
- 영어만 지원
- 다국어 지원 없음
- **영향**: 영어 시험으로 제한

#### 5. 성능
- 캐싱 미구현
- 순차 처리만 가능
- **영향**: 대량 배치 처리 시 느림

### 지원되는 개념 (Stage 2)

**질병** (~12개): 심부전, 심근경색, 뇌졸중, 당뇨병, 고혈압, COPD, 천식, 패혈증, 폐렴, COVID-19, 외상성 뇌손상, 만성 신장 질환

**약물** (~8개): 아스피린, 인슐린, 메트포르민, 아토르바스타틴, 리시노프릴, 와파린, 비타민 C, 하이드로코르티손

**측정** (~5개): 혈압, 심박수, 혈당, 크레아티닌, 헤모글로빈

**시술** (~3개): 삽관, 투석, 수술

**장비** (~2개): 심박조율기, 인공호흡기

---

## 🛣️ 개발 로드맵

### Phase 1: UMLS API 통합 (10일) 🔴 Critical
**목표**: 완전한 개념 표준화

- UMLS REST API 클라이언트 구현
- 응답 캐싱 추가 (LRU + Redis)
- 오프라인 표준화기와 통합
- 폴백 로직 생성 (API → 오프라인)
- 통합 테스트 작성

**영향**: 30개 대신 1,000+ 개념 표준화

### Phase 2: OHDSI Athena 통합 (10일) 🔴 Critical
**목표**: 실제 OMOP CDM 코드

- Athena API 클라이언트 구현
- 도메인별 어휘 매핑
- OMOP에 대한 코드 검증
- "Maps to" 관계 해결
- 통합 테스트 작성

**영향**: 실제 ICD-10/RxNorm/LOINC 코드 생성

### Phase 3: OMOP 어휘 데이터베이스 (7일) 🟡 Medium
**목표**: 오프라인 기능 + 속도

- OMOP 어휘 다운로드
- PostgreSQL에 로드
- 데이터베이스 클라이언트 생성
- DB 쿼리로 API 호출 대체
- API를 폴백으로 유지

**영향**: 10배 빠름, 오프라인 작동

### Phase 4: 테스트 & 검증 (5일) 🔴 Critical
**목표**: 정확성 보장

- 100개 개념 골드 스탠다드 데이터셋 생성
- 정밀도/재현율/F1 측정
- 성능 벤치마킹
- 엣지 케이스 테스트
- 임상 전문가 검증

**영향**: 운영 배포에 대한 신뢰

### Phase 5: 운영 강화 (5일) 🟡 Medium
**목표**: 안정성

- 지수 백오프를 사용한 재시도 로직
- 서킷 브레이커 패턴
- 모니터링 및 알림
- 우아한 성능 저하
- 배포 문서화

**영향**: 운영 준비된 시스템

### 전체 타임라인
- **순차**: 7.5주 (개발자 1명)
- **병렬**: 5주 (개발자 2명)

---

## 🔧 문제 해결

### 일반적인 문제

#### 문제: "trialist 파서를 찾을 수 없음"

**원인**: Trialist 미등록 또는 가져오기 오류

**해결책**:
```python
from pipeline.plugins import registry
print(registry.list_parsers())  # 'trialist' 포함해야 함
```

#### 문제: "OPENAI_API_KEY를 찾을 수 없음"

**원인**: 환경 변수 누락

**해결책**:
```bash
echo "OPENAI_API_KEY=sk-..." >> .env
```

#### 문제: "Stage 2가 standard_name을 반환하지 않음"

**원인**: 오프라인 어휘에 개념 없음

**해결책**:
- `src/pipeline/offline_standardizer.py:48-303`에서 지원되는 개념 확인
- 필요시 사용자 정의 매핑 추가
- UMLS API 통합 대기 (Phase 1)

#### 문제: "생성된 코드가 가짜처럼 보임"

**예상 동작**: Stage 3는 현재 placeholder 코드 생성

**설명**: 실제 OMOP CDM 코드는 OHDSI 통합 필요 (Phase 2)

**해결 방법**: 현재는 코드 대신 `standard_name`과 `umls_cui` 사용

---

## 📚 문서 참조

### 주요 문서

1. **기술 사양**: `documents/trialist_agent_specification.md`
   - 3단계 처리 파이프라인 설계
   - 12-domain 분류 체계
   - OMOP CDM 매핑 전략

2. **구현 상태**: `documents/trialist_implementation_status.md`
   - 완료된 기능
   - 대기 중인 작업
   - 사용 방법

3. **중요 평가**: `documents/trialist_critical_assessment.md`
   - 상세 완성도 분석 (47%)
   - 어휘 커버리지 (~3%)
   - 구현 로드맵

4. **사용자 가이드**: `documents/TRIALIST_USER_GUIDE.md` (영문)
   - 전체 사용 가이드
   - 예제 및 모범 사례
   - 문제 해결

5. **통합 완료**: `documents/trialist_integration_complete.md`
   - 기본 파서로 통합
   - API 엔드포인트
   - 출력 예시

### 테스트 파일

- `test_trialist_parser.py` - 기본 테스트
- `test_stage2_standardization.py` - Stage 2 테스트
- `test_nct03389555.py` - 실제 시험 예제
- `test_offline_standardizer.py` - 오프라인 표준화기 테스트

---

## 💡 모범 사례

### 1. Stage 1만 사용하여 시작
운영 환경에서는 Stage 1 (NER)만 신뢰하고 API 통합될 때까지 Stage 2/3 출력 무시

### 2. 신뢰도 점수 검증
신뢰도 임계값으로 엔티티 필터링:
```python
high_conf_entities = [
    e for e in result.inclusion[0].entities
    if e.confidence >= 0.8
]
```

### 3. 도메인 통계 사용
파싱 결과 건전성 확인:
```python
stats = result.domain_statistics
if stats.get("Condition", 0) == 0:
    print("경고: 질병을 찾을 수 없습니다!")
```

### 4. 중간 출력 저장
디버깅을 위해 항상 단계 출력 파일 확인:
```bash
ls -lh workspace/{project_id}/trialist_output/
```

### 5. 배치 처리
여러 시험의 경우 배치로 처리:
```python
for trial_batch in chunks(trials, batch_size=10):
    results = [parser.run(...) for trial in trial_batch]
```

---

## 🎯 결론

Trialist는 다음과 같은 강력한 임상시험 파싱 시스템입니다:

✅ **운영 준비된 NER** (95% 완료)
- 12-domain 분류
- 높은 정밀도 엔티티 추출
- 포괄적인 메타데이터

⚠️ **프로토타입 표준화** (32% 완료)
- 제한적 어휘 커버리지
- 기본 UMLS 매핑
- API 통합 누락

🚧 **Placeholder CDM 매핑** (10% 완료)
- 가짜 코드 생성
- OMOP 통합 필요
- 운영 준비 안 됨

**권장사항**: 운영 환경에서는 Stage 1 (NER) 사용. 표준화 및 CDM 매핑에 의존하기 전에 Phase 1-2 대기.

**다음 단계**:
1. 현재 제한사항 검토
2. Phase 1 (UMLS 통합) 계획
3. 검증 데이터셋 생성
4. 운영 준비 상태를 향해 반복

---

**문서 버전**: 1.0
**유지관리자**: RWE 플랫폼 팀
**마지막 검토**: 2025-10-13
