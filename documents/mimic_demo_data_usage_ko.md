# mimic-demo 데이터 활용 문서

## 개요
- `mimic-demo` 플러그인은 `data/` 디렉터리에 포함된 MIMIC-IV 데모 세트를 사용해 실제 코호트를 생성한다.
- CLI 실행 시 `--impl map-to-ehr=mimic-demo`, `--impl filter-cohort=mimic-demo` 옵션을 통해 이 플러그인을 선택할 수 있다.
- 입력 URI는 `mimic-demo:///절대경로` 또는 로컬 경로/`file://` 형식을 지원하며, 기본 워크스페이스(`workspace/`) 기준 상대 경로도 허용된다.

## 데이터 소스
- **대상 환자 목록**: `data/demo_subject_id.csv`에서 `subject_id`를 로드해 이후 모든 테이블을 해당 환자로 제한한다.
- **환자 기본 정보**: `data/hosp/patients.csv.gz`에서 성별, 기준 연령(`anchor_age`), 기준 연도(`anchor_year`)를 읽어 나이를 계산한다.
- **입원 기록**: `data/hosp/admissions.csv.gz`에서 입원 ID(`hadm_id`), 입·퇴원 시점을 확보해 인덱스 시각의 기본값으로 사용한다.
- **ICU 체류 정보**: `data/icu/icustays.csv.gz`에서 ICU `stay_id`와 `intime`을 가져와 가장 이른 ICU 방문을 매칭한다(존재하는 경우).
- **심초음파 LVEF**: `data/icu/chartevents.csv.gz`에서 `itemid=227008`(Ejection Fraction)을 스트리밍으로 읽어 최신 측정값을 사용한다.
- **실험실 검사**:
  - BNP: `data/hosp/labevents.csv.gz`, `itemid=50823`에서 ±24시간 내 가장 가까운 결과.
  - Creatinine: `itemid=50912`에서 ±48시간 내 측정값을 사용해 eGFR을 계산한다.
- **투약 정보**: `data/hosp/prescriptions.csv.gz`에서 약물명이 `sacubitril` 또는 `entresto`를 포함하는 행을 찾아 ARNI 처방 여부를 결정한다.

## 피처 및 기준 계산
- **나이**: `anchor_age`에 `admittime.year - anchor_year`를 더해 입원 시점을 기준으로 환자 나이를 추정한다.
- **LVEF 누락 시 처리**: 측정값이 없으면 `subject_id`, `hadm_id` 기반 단순 규칙으로 25–44% 사이 값을 생성해 필터 평가가 가능하도록 한다.
- **eGFR**: 크레아티닌과 나이, 성별을 이용해 CKD-EPI 공식을 변형해 계산한다.
- **인클루전/익스클루전 평가**: `TrialSchema` 기준(예: 나이 범위, LVEF < 40%, eGFR < 30)에 맞춰 대상자를 필터하고 통과한 기준 ID를 `matched_criteria`에 기록한다.

## 산출물
- `workspace/<project_id>/filters/filter_spec.json`: mimic-demo 매퍼가 생성한 변수 매핑 및 기준 표현식.
- `workspace/<project_id>/cohort/cohort.json`: 각 환자별 `subject_id`, `stay_id`, 인덱스 시각, 매칭된 기준, 파생 피처(LVEF, BNP, eGFR, on_arnI 등)를 포함한다.
- `workspace/<project_id>/cohort/summary.json`: 필터링 결과 요약(전체 인원, 각 기준 별 탈락 건수, 데이터 루트 등 메타 정보).
- 이후 단계(`analysis`, `report`) 역시 이 코호트를 기반으로 메트릭과 보고서를 생성한다.

## 실행 예시
```bash
PYTHONPATH=src python -m rwe_cli --project demo --workspace workspace \
  --impl map-to-ehr=mimic-demo --impl filter-cohort=mimic-demo \
  run-all --disease-code HF --keyword sacubitril --keyword valsartan \
  --source clinicaltrials --estimator dr \
  --template templates/default_report.md \
  --input-uri mimic-demo:///Users/kyh/datathon2/data
```
- 실행 후 `workspace/demo/` 경로에서 단계별 결과물을 확인할 수 있다.
