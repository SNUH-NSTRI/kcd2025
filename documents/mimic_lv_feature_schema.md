# MIMIC-LV Feature Schema

- **목적**: `map-to-ehr` 및 `filter-cohort` 모듈이 활용할 MIMIC-LV(좌심실 초음파 중심 가공 데이터) 피처 스키마를 정의한다.
- **범위**: 좌심실 관련 심초음파 지표, 동반 임상 변수, 코호트 인덱싱에 필요한 공통 필드의 데이터 타입·단위·추출 경로를 명시한다.

---

## 1. 데이터셋 개요

| 항목 | 설명 |
| ---- | ---- |
| 소스 | MIMIC-IV `echodata`, `labevents`, `chartevents`, `patients`, `admissions` |
| 대상 | 좌심실 기능 평가가 기록된 성인 환자의 에코 검사 |
| 뷰 | 검사 단위(`study_id`) 기준의 wide-format 파생 테이블 |
| 인덱스 키 | `subject_id`, `hadm_id`, `stay_id`(Optional ICU), `study_id`, `study_time` |

---

## 2. 공통 메타 필드

| 필드명 | 타입 | 단위/형식 | 설명 |
| ------ | ---- | -------- | ---- |
| `subject_id` | `INT` | - | 환자 식별자 |
| `hadm_id` | `INT` | - | 입원 에피소드 ID |
| `stay_id` | `INT` | - | ICU 스테이 ID, 존재하지 않을 수 있음 |
| `study_id` | `INT` | - | Echo study ID |
| `study_time` | `TIMESTAMP` | UTC | 검사 수행 일시 |
| `index_time` | `TIMESTAMP` | UTC | Trial 인덱스 기준 시간 (cohort 산출 시 활용) |
| `age_at_study` | `DECIMAL(4,1)` | Years | 검사 시점 나이 |
| `sex` | `VARCHAR(1)` | `M`/`F`/`U` | 성별 |

---

## 3. 좌심실 구조 지표

| 필드명 | 타입 | 단위 | 허용값/범위 | 원본 컬럼 |
| ------ | ---- | ---- | ----------- | -------- |
| `lv_edv` | `DECIMAL(6,1)` | `mL` | 0–400 | `echo.lv_edv` |
| `lv_esv` | `DECIMAL(6,1)` | `mL` | 0–300 | `echo.lv_esv` |
| `lv_edvi` | `DECIMAL(6,1)` | `mL/m²` | 0–200 | 파생: `lv_edv / bsa` |
| `lv_essi` | `DECIMAL(6,1)` | `mL/m²` | 0–120 | 파생: `lv_esv / bsa` |
| `lv_mass` | `DECIMAL(7,1)` | `g` | 0–400 | `echo.lv_mass` |
| `lv_mass_index` | `DECIMAL(6,1)` | `g/m²` | 0–200 | 파생: `lv_mass / bsa` |
| `septal_wall_thickness` | `DECIMAL(5,2)` | `cm` | 0–3 | `echo.ivsd` |
| `posterior_wall_thickness` | `DECIMAL(5,2)` | `cm` | 0–3 | `echo.lvpwd` |
| `lv_outflow_gradient` | `DECIMAL(5,1)` | `mmHg` | 0–200 | `echo.lvo_resflow` |

---

## 4. 좌심실 기능 지표

| 필드명 | 타입 | 단위 | 허용값/범위 | 원본 컬럼 |
| ------ | ---- | ---- | ----------- | -------- |
| `lvef_method` | `VARCHAR(16)` | Category | `biplane`, `m-mode`, `visual`, `3d`, `unknown` | `echo.lvef_method` |
| `lvef` | `DECIMAL(5,2)` | `%` | 0–100 | `echo.lvef` |
| `global_longitudinal_strain` | `DECIMAL(5,2)` | `%` | -30 – 0 | `echo.gls` |
| `stroke_volume` | `DECIMAL(6,1)` | `mL` | 0–250 | 파생: `lv_edv - lv_esv` |
| `cardiac_output` | `DECIMAL(6,2)` | `L/min` | 0–15 | 파생: `stroke_volume * heart_rate / 1000` |
| `cardiac_index` | `DECIMAL(5,2)` | `L/min/m²` | 0–8 | 파생: `cardiac_output / bsa` |
| `ejection_time` | `DECIMAL(5,1)` | `ms` | 0–400 | `echo.lvo_et` |
| `dp_dt` | `DECIMAL(6,1)` | `mmHg/s` | 0–4000 | `echo.dpdt` |

---

## 5. 이완 기능 지표

| 필드명 | 타입 | 단위 | 허용값/범위 | 원본/파생 |
| ------ | ---- | ---- | ----------- | -------- |
| `mitral_e_velocity` | `DECIMAL(5,2)` | `m/s` | 0–2.5 | `echo.mitral_e` |
| `mitral_a_velocity` | `DECIMAL(5,2)` | `m/s` | 0–2.5 | `echo.mitral_a` |
| `e_a_ratio` | `DECIMAL(5,2)` | - | 0–3 | 파생: `mitral_e_velocity / mitral_a_velocity` |
| `mitral_e_prime` | `DECIMAL(5,2)` | `cm/s` | 0–20 | `echo.mitral_e_prime` |
| `e_e_prime_ratio` | `DECIMAL(5,2)` | - | 0–40 | 파생: `mitral_e_velocity / (mitral_e_prime / 100)` |
| `left_atrial_volume_index` | `DECIMAL(6,1)` | `mL/m²` | 0–80 | `echo.la_volume_index` |

---

## 6. 혈역학 및 바이탈 지표

| 필드명 | 타입 | 단위 | 허용값/범위 | 원본 |
| ------ | ---- | ---- | ----------- | ---- |
| `heart_rate` | `INT` | `bpm` | 20–200 | `chartevents.heart_rate` (에코 ±1시간 평균) |
| `systolic_bp` | `INT` | `mmHg` | 60–220 | `chartevents.sbp` |
| `diastolic_bp` | `INT` | `mmHg` | 30–140 | `chartevents.dbp` |
| `mean_bp` | `INT` | `mmHg` | 30–160 | `chartevents.map` |
| `resp_rate` | `INT` | `breaths/min` | 6–50 | `chartevents.resp_rate` |
| `spo2` | `DECIMAL(5,2)` | `%` | 70–100 | `chartevents.spo2` |

---

## 7. 실험실/바이오마커

| 필드명 | 타입 | 단위 | 허용값/범위 | 원본 |
| ------ | ---- | ---- | ----------- | ---- |
| `bnp` | `DECIMAL(7,1)` | `pg/mL` | 0–50000 | `labevents.itemid=50823` |
| `nt_pro_bnp` | `DECIMAL(7,1)` | `pg/mL` | 0–100000 | `labevents.itemid=51003` |
| `creatinine` | `DECIMAL(5,2)` | `mg/dL` | 0–15 | `labevents.itemid=50912` |
| `bun` | `DECIMAL(5,1)` | `mg/dL` | 0–150 | `labevents.itemid=51006` |
| `sodium` | `DECIMAL(4,1)` | `mmol/L` | 110–170 | `labevents.itemid=50983` |
| `potassium` | `DECIMAL(4,1)` | `mmol/L` | 2–8 | `labevents.itemid=50971` |
| `chloride` | `DECIMAL(4,1)` | `mmol/L` | 70–130 | `labevents.itemid=50902` |
| `hemoglobin` | `DECIMAL(4,1)` | `g/dL` | 5–20 | `labevents.itemid=51221` |

- 실험실 값은 `study_time` ±24시간 내 최근값을 선택하며, 다중 측정 시 가장 가까운 결과 사용.
- 결측 발생 시 `None`으로 채우고, 별도 마스크는 `features_missing.<field>` Boolean 컬럼으로 제공 가능.

---

## 8. 치료/약물 맥락

| 필드명 | 타입 | 단위 | 허용값/범위 | 파생 방법 |
| ------ | ---- | ---- | ----------- | -------- |
| `on_beta_blocker` | `BOOLEAN` | - | - | `prescriptions.drug` 리스트에서 β-차단제 여부 |
| `on_ace_arb` | `BOOLEAN` | - | - | ACE inhibitor 또는 ARB 처방 여부 |
| `on_arnI` | `BOOLEAN` | - | - | sacubitril/valsartan 처방 여부 |
| `diuretic_dose_mg` | `DECIMAL(6,1)` | `mg furosemide eq.` | 0–1000 | 24시간 내 루프 이뇨제 용량 합산, furosemide 등가 환산 |
| `inotrope_support` | `BOOLEAN` | - | - | dobutamine/milrinone/epinephrine 정맥 투여 여부 |

---

## 9. 품질 관리 필드

| 필드명 | 타입 | 설명 |
| ------ | ---- | ---- |
| `data_quality_flag` | `VARCHAR(16)` | `ok`, `partial`, `failed` 중 하나 |
| `missing_ratio` | `DECIMAL(4,2)` | 전체 피처 중 결측 비율 |
| `source_tables` | `ARRAY<VARCHAR>` | 참조한 원본 테이블 목록 (예: `["echodata", "chartevents"]`) |
| `generated_at` | `TIMESTAMP` | 레코드 생성 시각 (UTC) |
| `generator_version` | `VARCHAR(16)` | 파이프라인 버전 (예: `mimic-lv.v1`) |

---

## 10. 스키마 검증 규칙

- **기본 키**: (`subject_id`, `hadm_id`, `study_id`)
- **null 허용**
  - 핵심 지표(`lvef`, `lv_edv`, `lv_esv`)는 최소 한 개 이상 존재해야 함
  - 기타 연속값은 결측 허용, 대신 `missing_ratio` 업데이트 필수
- **범위 검증**
  - 음수값 허용 컬럼 없음 (단, `global_longitudinal_strain`은 음수 허용)
  - 범위 위반 시 `data_quality_flag`를 `failed`로 설정하고 로그 기록
- **단위 일관성**
  - 모든 길이/부피는 SI 단위 사용. 필요 시 입력 단계에서 변환
- **타임스탬프 검증**
  - `study_time`은 `admit_time` 이후, `discharge_time` 이전이어야 함

---

## 11. 출력 형태

- 기본 스토리지: `workspace/features/mimic-lv/<project_id>/mimic_lv_features.parquet`
- Parquet 스키마 예시
  - `subject_id` (`INT64`)
  - `study_time` (`TIMESTAMP[us, UTC]`)
  - `lvef` (`DOUBLE`)
  - ... (상기 필드 순서)
- JSON 메타: `workspace/features/mimic-lv/<project_id>/schema_manifest.json`
  ```json
  {
    "schema_version": "mimic-lv.v1",
    "primary_keys": ["subject_id", "hadm_id", "study_id"],
    "row_count": 1234,
    "generated_at": "2025-01-01T00:00:00Z"
  }
  ```

---

## 12. 향후 확장

- 3D echo 또는 strain imaging이 없는 경우를 위한 대체 피처 정의 (`gls` 미측정 시 파생값 제거).
- ICU 밖 일반병동 환자 포함 시 `ward_id` 추가.
- Telemetry, invasive hemodynamics(arterial line) 통합.
- 자동 단위 변환 모듈 도입을 위한 `unit_source` 필드 추가.

