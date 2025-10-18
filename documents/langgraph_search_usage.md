# LangGraph 기반 Search Agent 사용 가이드

## 1. 개요
- `LangGraphLiteratureFetcher`는 clinicaltrials.gov API를 호출해 임상시험 구조화 데이터를 수집한다.
- CLI에서 `--impl search-lit=langgraph-search` 옵션으로 선택할 수 있다.
- 질환 코드와 약물(키워드)을 공백으로 결합한 자연어 쿼리를 사용하며, `NCT` ID를 직접 지정해 단일 임상시험을 조회할 수도 있다.
- **ClinicalTrials.gov API의 전체 응답 데이터**를 `metadata.full_study_data`에 저장하여 모든 정보를 보존한다.

## 2. 의존성
```bash
pip install requests
```
- clinicaltrials.gov API는 별도의 키 없이 사용할 수 있다.

## 3. 실행 예시
```bash
PYTHONPATH=src python -m rwe_cli --project demo --workspace workspace \
  --impl search-lit=langgraph-search \
  search-lit --disease-code HFpEF \
  --keyword sacubitril --keyword valsartan \
  --source clinicaltrials --max-records 5
```
- 수집된 레코드는 `workspace/demo/lit/corpus.jsonl`로 저장되고, 각 문서는 NCT ID를 identifier로 가진다.
- 이후 `parse-trials` 단계에서 `--impl parse-trials=langgraph`와 함께 사용하면 clinicaltrials.gov 기반 Trial Schema 파이프라인을 만들 수 있다.

### 3.1 NCT ID 직접 조회
```bash
PYTHONPATH=src python -m rwe_cli --project demo --workspace workspace \
  --impl search-lit=langgraph-search \
  search-lit --keyword NCT05818397 --source clinicaltrials
```
- `--keyword`에 `NCT` 번호를 넣으면 해당 임상시험 레코드가 직접 반환되며, 다른 질환 코드나 키워드는 필요 없다.

## 4. 저장되는 데이터 구조

각 문서의 `metadata` 필드에 다음 정보가 포함됩니다:

### 4.1 최상위 메타데이터 (빠른 접근용)
- `nct_id`: NCT 식별자
- `phase`: 임상시험 단계 (예: ["PHASE3"])
- `conditions`: 질환 목록 (예: ["Septic Shock"])
- `status`: 연구 상태 (예: "COMPLETED", "RECRUITING")
- `arms_interventions`: 연구 그룹 및 중재 정보
- `eligibility`: 포함/제외 기준 (성별, 나이, 상세 criteria)
- `outcomes`: Primary/Secondary 결과 지표
- `sponsors`: 스폰서 및 협력 기관
- `contacts_locations`: 연구 기관 및 연락처
- `design`: 연구 설계 정보 (연구 유형, 참여자 수 등)

### 4.2 전체 원본 데이터
- `full_study_data`: **ClinicalTrials.gov API의 전체 응답 객체**
  - `protocolSection`: 12개 모듈 전체 포함
    - identificationModule
    - statusModule
    - sponsorCollaboratorsModule
    - oversightModule
    - descriptionModule
    - conditionsModule
    - designModule
    - armsInterventionsModule
    - outcomesModule
    - eligibilityModule
    - contactsLocationsModule
    - referencesModule
  - 약 11KB 크기 (NCT04134403 기준)
  - 모든 원본 정보를 보존하여 추후 분석 가능

## 5. 참고
- 현재 지원 소스는 `clinicaltrials` 하나이며, 다른 소스를 추가하려면 `LangGraphLiteratureFetcher`에 전용 로더를 확장하면 된다.
- clinicaltrials.gov API 호출 시 일시적인 500 오류가 발생할 수 있으므로 재시도를 권장한다.
- 구조화 데이터만 수집하므로 PDF 다운로드나 원문 추출 단계는 수행되지 않는다.
- `--require-full-text` 옵션은 clinicaltrials.gov 레코드에 해당되지 않으며, 전달되더라도 구조화 데이터는 그대로 반환된다.
- 동일한 임상시험이 질환·약물 조합 및 NCT ID 조회 모두에 매칭될 경우 자동으로 중복이 제거된다.
- **전체 데이터 크기**: 단일 문서 약 18KB (metadata), corpus.jsonl 파일 약 21KB
