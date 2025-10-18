# Critical Care Feature Extraction Mapping

- **목적**: `parser` 에이전트와 MIMIC-IV / K-MIMIC 파이프라인이 동일한 피처 키로 임상 데이터를 정규화하도록 기준을 제공한다.
- **범위**: 중환자실 기반 모델링을 위한 핵심 생체 신호, 혈액가스, 실험실 검사, 중증도 점수.
- **버전**: `critical-care-feature-map.v1`

---

## 0. 공통 규칙

| 구분 | 지침 |
| --- | --- |
| 키 네이밍 | `snake_case` 고정 (`paO2_fiO2_ratio`, `gcs_total`). |
| 식별자 | 필수: `subject_id`, `hadm_id`; ICU 데이터 사용 시 `stay_id`, 관측 시점은 `charttime` 또는 `sample_time`. |
| 윈도우 | **Labs** ±24시간, **Vitals** ±6시간, **점수/스케일** 인덱스 타임 ±6시간. |
| 단위 | SI 기준 통일 (`mmHg`, `mmol/L`, `g/dL`, `°C`). 필요 시 parser에서 변환. |
| 결측 처리 | 원본 값 없음 → `null`. 다운스트림에서 `features_missing.<feature_key>` Boolean 제공 가능. |
| 상태 분류 | `Core`=기본 추출, `Optional`=조건부, `Dropped`=기본 파이프라인 제외(참고용). |

---

## 1. 인구학적 변수

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `age` | Core | 인덱스 시점 환자 나이 (Years, 소수 1자리) | `patients.anchor_age` 또는 `datediff(charttime, dob)` | `PAT_INFO.AGE` | 89세 상한 적용시 `is_aged_flag` 추가 고려 |
| `gender` | Core | 생물학적 성별 (`M`/`F`) | `patients.gender` | `PAT_INFO.SEX` | - |

---

## 2. 혈액가스 및 산-염기 균형

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `ph` | Core | 동맥혈 pH | `labevents` (`ITEMID` 50820/50821) | ABGA (`PH`) | 범위 6.8–7.7 검증 |
| `so2` | Core | 산소포화도 (Arterial SO₂, %) | `labevents`, `chartevents` (혈가스) | ABGA (`SO2`) | PaO₂/FiO₂ 대체 지표 |
| `po2` | Core | 동맥혈 산소분압 (mmHg) | `labevents` (`PO2`) | ABGA (`PO2`) | - |
| `pco2` | Core | 동맥혈 이산화탄소분압 (mmHg) | `labevents` (`PCO2`) | ABGA (`PCO2`) | - |
| `aado2` | Optional | A-a gradient (mmHg) | 파생: `PAO2 - PO2` | 파생 동일 | 필요한 프로젝트만 계산 |
| `paO2_fiO2_ratio` | Optional | 산소화 지수 | `po2 / fio2` | `PO2 / FIO2` | `so2` 우선 사용, 성능 비교 필요 |
| `base_excess` | Core | 염기 과잉 (mmol/L) | `labevents` (`Base Excess`) | ABGA (`BE`) | ± 값 허용 |
| `bicarbonate` | Core | 중탄산염 (mmol/L) | `labevents`, `chartevents` | ABGA (`HCO3`) | Lactate 대체 변수 |
| `total_co2` | Core | 총 CO₂ (mmol/L) | `labevents` (`TCO2`) | ABGA (`TCO2`) | - |

---

## 3. 혈액학적 지표

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `hematocrit` | Core | 헤마토크릿 (%) | `labevents` (`hematocrit`) | CBC (`HCT`) | - |
| `hemoglobin` | Core | 헤모글로빈 (g/dL) | `labevents` (`hemoglobin`) | CBC (`HGB`) | - |
| `carboxyhemoglobin` | Optional | COHb (%) | `labevents` (`COHB`) | ABGA 확장 | 드물게 측정 |
| `methemoglobin` | Optional | MetHb (%) | `labevents` (`MEHB`) | ABGA 확장 | - |

---

## 4. 활력징후 및 생리적 지표

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `temperature` | Core | 체온 (°C) | `chartevents.Temperature` | VITAL (`BT`) | 화씨 입력 시 변환 |
| `heart_rate` | Core | 심박수 (bpm) | `chartevents.heart_rate` | VITAL (`HR`) | 결측 시 BP·CO 기반 보간 |
| `sbp` | Core | 수축기 혈압 (mmHg) | `chartevents.Systolic BP` | VITAL (`SBP`) | invasive/outlet 우선순위 정의 |
| `dbp` | Core | 이완기 혈압 (mmHg) | `chartevents.Diastolic BP` | VITAL (`DBP`) | - |
| `mbp` | Core | 평균 동맥압 (mmHg) | `chartevents.MAP` | VITAL (`MBP`) | - |
| `respiratory_rate` | Core | 호흡수 (breaths/min) | `chartevents.Respiratory Rate` | VITAL (`RR`) | - |
| `spo2` | Core | Pulse oximetry (%) | `chartevents.SpO2` | VITAL (`SPO2`) | - |
| `urine_output` | Dropped | 시간당 소변량 (mL/hr) | `outputevents` | `OUTPUT.URINE` | 기본 파이프라인 제외, `fluid_balance_status` 활용 |

---

## 5. 장기 기능 및 중증도 점수

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `apache_ii_score` | Core | APACHE II 총점 | `chartevents` 파생 or 계산 모듈 | 중증도 데이터셋 | SOFA 대체 기본 값 |
| `sofa_score` | Dropped | Sequential Organ Failure Assessment | 파생 | 파생 | 불균형으로 기본 제외 |
| `gcs_total` | Core | GCS 총점 | `chartevents.GCS - Total` | VITAL (`GCS_TOTAL`) | - |
| `gcs_motor` | Core | GCS Motor | `chartevents.GCS - Motor` | VITAL (`GCS_M`) | - |
| `gcs_verbal` | Core | GCS Verbal | `chartevents.GCS - Verbal` | VITAL (`GCS_V`) | - |
| `gcs_eyes` | Core | GCS Eye | `chartevents.GCS - Eye` | VITAL (`GCS_E`) | - |
| `gcs_unable` | Optional | GCS 측정 불가 플래그 | `chartevents` | VITAL (`GCS_UNABLE`) | Boolean |

---

## 6. 전해질 및 대사 지표

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `sodium` | Core | Na⁺ (mmol/L) | `labevents` (`ITEMID` 50983) | LAB (`Na`) | - |
| `potassium` | Core | K⁺ (mmol/L) | `labevents` (50971) | LAB (`K`) | - |
| `chloride` | Core | Cl⁻ (mmol/L) | `labevents` (50902) | LAB (`Cl`) | - |
| `calcium` | Core | Ca²⁺ (mg/dL) | `labevents` (50893/50894) | LAB (`Ca`) | 이온화 vs 총 칼슘 구분 |
| `glucose` | Core | 혈당 (mg/dL) | `labevents` (50809/50931) | LAB (`Glucose`) | - |
| `anion_gap` | Dropped | 음이온 차 (mmol/L) | `labevents` (50868) | LAB 파생 | lactate 대체로 제외 |

---

## 7. 간 기능 관련 변수

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `ast` | Core | AST (U/L) | `labevents` (`AST`) | LAB (`AST`) | - |
| `alt` | Core | ALT (U/L) | `labevents` (`ALT`) | LAB (`ALT`) | - |
| `alp` | Core | ALP (U/L) | `labevents` (`ALP`) | LAB (`ALP`) | - |
| `ggt` | Optional | GGT (U/L) | `labevents` (`GGT`) | LAB (`GGT`) | - |
| `ldh` | Dropped | LD/LDH (U/L) | `labevents` (`LDH`) | LAB (`LD`) | 모델 성능 영향 낮음 |
| `ck` | Dropped | CK/CPK (U/L) | `labevents` (`CK`, `CPK`) | LAB (`CK`) | - |
| `ck_mb` | Core | CK-MB (ng/mL) | `labevents` (`CK-MB`) | LAB (`CKMB`) | - |

---

## 8. 응고 관련 지표

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `d_dimer` | Core | D-dimer (µg/mL FEU) | `labevents` (`D-Dimer`) | LAB (`DDIMER`) | - |
| `fibrinogen` | Core | Fibrinogen (mg/dL) | `labevents` | LAB (`FIBRINOGEN`) | - |
| `thrombin_time` | Dropped | Thrombin time (sec) | `labevents` | LAB | PT/aPTT로 대체 |
| `inr` | Core | 국제정상화비 | `labevents` (`INR`) | LAB (`INR`) | - |
| `pt` | Core | 프로트롬빈 시간 (sec) | `labevents` (`PT`) | LAB (`PT`) | - |
| `aptt` | Core | 활성화 부분 트롬보플라스틴 시간 (sec) | `labevents` (`aPTT`) | LAB (`APTT`) | - |

---

## 9. 신기능 관련 변수

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `bun` | Core | 혈중 요소 질소 (mg/dL) | `labevents` (51006) | LAB (`BUN`) | `bun_creatinine_pair` 로 validation |
| `creatinine` | Core | 혈청 크레아티닌 (mg/dL) | `labevents` (50912) | LAB (`CREA`) | Creatinine clearance 대체 |
| `creatinine_clearance` | Dropped | 크레아티닌 청소율 | Cockcroft-Gault 파생 | 동일 | 기본 제외, 필요시 파생 |
| `fluid_balance_status` | Core | 24h 순수 체액 밸런스 (mL) | 파생: `inputevents` vs `outputevents` | `INPUT/OUTPUT` | `urine_output` 대체 |

---

## 10. 혈청 단백 및 기타 생화학 지표

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `albumin` | Core | 알부민 (g/dL) | `labevents` (50862) | LAB (`Albumin`) | - |
| `globulin` | Core | 글로불린 (g/dL) | 총단백-알부민 파생 | LAB | 아웃리어 검증 필요 |
| `total_protein` | Core | 총단백 (g/dL) | `labevents` (50976) | LAB (`TP`) | - |

---

## 11. 백혈구 및 세포 구성 요소

| Feature Key | Status | Description | MIMIC Source | K-MIMIC Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `wbc` | Core | 백혈구 (10³/µL) | `labevents` (51300) | CBC (`WBC`) | - |
| `platelets` | Core | 혈소판 (10³/µL) | `labevents` (51265) | CBC (`PLT`) | - |
| `abs_basophils` | Optional | 절대 호염구 | CBC 파생 | CBC | 비율→절대 변환 필요 |
| `abs_eosinophils` | Optional | 절대 호산구 | CBC 파생 | CBC | - |
| `abs_neutrophils` | Core | 절대 호중구 (ANC) | CBC 파생 | CBC | - |
| `abs_lymphocytes` | Core | 절대 림프구 (ALC) | CBC 파생 | CBC | - |
| `abs_monocytes` | Optional | 절대 단핵구 | CBC 파생 | CBC | - |
| `immature_granulocytes` | Optional | 미성숙 과립구 (%, 또는 절대) | CBC 파생 | CBC (`IG`) | 단위 표기 필수 |

---

## :gear: Dropped & Substituted Summary

- **Dropped (기본 파이프라인 제외)**: `urine_output`, `anion_gap`, `ldh`, `ck`, `thrombin_time`, `sofa_score`, `creatinine_clearance`, `lactate`.
- **Substitution Rules**
  - `lactate` → `bicarbonate`, `ph`.
  - `paO2_fiO2_ratio` ↔ `so2`: 모델에서 성능 비교 후 하나 선택.
  - `heart_rate` 결측 시 `cardiac_output` (파생) 또는 혈압 variability 활용.
  - `sofa_score` → `apache_ii_score` 기본 사용.
  - `thrombin_time` → `pt`, `aptt`.
  - `urine_output` → `fluid_balance_status`.

> Parser 구현 시 `Dropped` 항목은 옵션 플래그(`include_optional=false`)일 때 제외, 과거 스키마 호환이 필요하면 별도 설정으로 활성화한다.

---

## 12. 구현 체크리스트

- **Alias 사전**: 위 테이블의 Feature Key별로 영문/한글/약어 매핑 (`ex: {"Age": "age", "나이": "age"}`).
- **단위 변환**: `f_to_c`, `kpa_to_mmhg`, `meq_to_mmol` 등 유틸 함수 공통 모듈화.
- **시간창 정렬**: 동일 피처 다중 측정 시 `|charttime - index_time|` 최소값 선택.
- **품질 검증**: 범위 밖 값 clip 또는 플래그 (`ph` < 6.8 등).
- **로깅**: Dropped/Substituted 적용 여부를 row-level 또는 metadata(`feature_manifest.json`)에 기록.

---

## 13. 향후 업데이트 메모

- K-MIMIC 버전별 코드 시스템 상이 → `code_mapping.yaml` 파일 별도 관리.
- `immature_granulocytes` 단위 (절대/%) 통일 필요.
- APACHE II 하위 컴포넌트 확장 시 동일 포맷으로 세부 테이블 추가 검토.
- 향후 `cardiac_output`, `stroke_volume` 등 hemodynamic 파생 변수 편입 예정.

