# OMOP CDM Clinical 데이터 구하는 방법

## 개요

OHDSI WebAPI의 전체 기능을 테스트하려면 CDM 형식의 환자 데이터가 필요합니다.
하지만 **Vocabulary 검색만** 사용한다면 CDM clinical 데이터는 필요 없습니다.

## 데이터톤 환경에서의 현실적인 옵션

### ✅ Plan A: Synthea (최우선 추천)

**가장 빠르고 안정적인 방법**

#### 장점
- ⚡ 빠른 생성 속도 (1-2시간)
- 🎯 간단한 ETL 프로세스
- 📊 원하는 환자 수 조절 가능
- 🔧 낮은 실패 확률

#### 설치 및 실행

```bash
# 1. Synthea 다운로드
git clone https://github.com/synthetichealth/synthea.git
cd synthea

# 2. 합성 데이터 생성 (1000명)
./run_synthea -p 1000

# 출력: output/csv/ 디렉토리에 CSV 파일들 생성
```

#### ETL-Synthea로 CDM 변환

```bash
# 1. ETL-Synthea 도구 다운로드
git clone https://github.com/OHDSI/ETL-Synthea.git
cd ETL-Synthea

# 2. R 의존성 설치
R -e "install.packages(c('DatabaseConnector', 'SqlRender', 'devtools'))"

# 3. Vocabulary 다운로드 및 로드 (Athena에서)
# https://athena.ohdsi.org/

# 4. ETL 스크립트 실행 (R)
# ETL-Synthea/inst/sql/create_cdm_tables.sql 실행
# ETL-Synthea/R/CreateCDMTables.R 실행
```

**예상 소요 시간:**
- Synthea 데이터 생성: 30분
- Vocabulary 로드: 30분
- ETL 변환: 30분
- **총 1.5-2시간**

---

### 🔄 Plan B: Eunomia (즉시 사용 가능)

**이미 변환된 소규모 CDM 데이터셋**

#### 특징
- Synthea 기반 사전 변환 데이터
- SQLite 파일로 패키징
- R 라이브러리로 제공
- 몇 분 내 로드 가능

#### 사용 방법

```r
# R에서 실행
install.packages("Eunomia")
library(Eunomia)

# CDM 데이터베이스 생성
connectionDetails <- getEunomiaConnectionDetails()

# 데이터 확인
connection <- DatabaseConnector::connect(connectionDetails)
DatabaseConnector::querySql(connection, "SELECT COUNT(*) FROM person")
```

**PostgreSQL로 마이그레이션:**
```bash
# SQLite -> PostgreSQL 변환 도구 사용
# 또는 R의 DatabaseConnector로 테이블별 복사
```

---

### 🏥 Plan C: MIMIC-IV 데모 변환 (도전적)

**실제 중환자실 데이터 경험 가능**

#### 장점
- 실제 데이터의 복잡성
- 풍부한 임상 정보
- 연구 품질 데이터

#### 단점
- ⏰ **시간 소요 큼** (3-6시간)
- 🔧 복잡한 ETL 프로세스
- ⚠️ 환경 설정 문제 가능성

#### 프로세스

```bash
# 1. OHDSI MIMIC ETL 다운로드
git clone https://github.com/OHDSI/MIMIC.git
cd MIMIC

# 2. PostgreSQL 데이터베이스 준비
createdb mimic_omop
psql -d mimic_omop -f ddl/postgresql/OMOP_CDM_postgresql_5.4_ddl.sql

# 3. MIMIC-IV 데이터 로드
# mimiciv/3.1/ 디렉토리의 CSV 파일들을 소스 스키마에 로드

# 4. Vocabulary 로드 (Athena)
# 별도 스키마에 Vocabulary 테이블 로드

# 5. ETL 스크립트 실행
# MIMIC/etl/postgresql/*.sql 순차 실행
```

**예상 소요 시간:**
- 환경 설정: 1-2시간
- 데이터 로드: 1시간
- ETL 실행: 2-3시간
- **총 4-6시간 (디버깅 시 더 길어질 수 있음)**

---

### ⚡ Plan D: 최소 테스트 데이터 (SQL INSERT)

**극도로 빠른 프로토타이핑**

#### 사용 시기
- 즉시 테스트가 필요할 때
- WebAPI 기능 확인만 하면 될 때
- 다른 방법이 실패했을 때

#### 예시: 환자 1명 데이터

```sql
-- 사전 조건: Vocabulary 테이블 로드 완료

-- 1. 환자 정보
INSERT INTO cdm.person (person_id, gender_concept_id, year_of_birth, race_concept_id, ethnicity_concept_id)
VALUES (1, 8507, 1978, 8527, 38003563);
-- 8507: MALE, 8527: White, 38003563: Not Hispanic

-- 2. 관찰 기간
INSERT INTO cdm.observation_period (observation_period_id, person_id,
    observation_period_start_date, observation_period_end_date, period_type_concept_id)
VALUES (1, 1, '2023-01-01', '2023-12-31', 32828);

-- 3. 외래 방문
INSERT INTO cdm.visit_occurrence (visit_occurrence_id, person_id, visit_concept_id,
    visit_start_date, visit_end_date, visit_type_concept_id)
VALUES (1, 1, 9202, '2023-01-10', '2023-01-10', 44818518);
-- 9202: Outpatient visit

-- 4. 제2형 당뇨병 진단
INSERT INTO cdm.condition_occurrence (condition_occurrence_id, person_id,
    condition_concept_id, condition_start_date, condition_type_concept_id, visit_occurrence_id)
VALUES (1, 1, 201826, '2023-01-10', 32020, 1);
-- 201826: Type 2 diabetes mellitus

-- 5. 메트포르민 처방
INSERT INTO cdm.drug_exposure (drug_exposure_id, person_id, drug_concept_id,
    drug_exposure_start_date, drug_type_concept_id, visit_occurrence_id)
VALUES (1, 1, 1503297, '2023-01-10', 38000177, 1);
-- 1503297: Metformin
```

**소요 시간: 5-10분**

---

## 우리 상황에 맞는 선택

### Vocabulary 검색만 사용하는 경우

**CDM clinical 데이터 불필요!**

우리가 사용하는 기능:
- `search_standard_concepts()` ✅
- `get_concept_mappings()` ✅
- `get_concept_ancestors()` ✅

이 기능들은 **Vocabulary 테이블만** 사용합니다.

### 전체 WebAPI 기능 테스트가 필요한 경우

**추천 순서:**

1. **Synthea + ETL-Synthea** (Plan A)
   - 데이터톤에서 가장 현실적
   - 1-2시간 내 완료 가능

2. **Eunomia** (Plan B)
   - 즉시 사용 가능
   - PostgreSQL 마이그레이션 필요

3. **최소 SQL INSERT** (Plan D)
   - 긴급 상황용
   - 5-10분 내 완료

4. **MIMIC-IV 변환** (Plan C)
   - 시간 여유가 있을 때만
   - 4-6시간 소요

---

## 필요한 구성요소 정리

### 모든 방법에 공통으로 필요
- PostgreSQL 데이터베이스
- **OMOP Vocabulary** (Athena에서 다운로드, 필수!)
- CDM 5.4 스키마 정의

### Vocabulary만 사용 시
```
데이터베이스 구조:
├── webapi (스키마)      # WebAPI 메타데이터
└── omop_cdm (스키마)     # Vocabulary 테이블만
    └── CONCEPT, CONCEPT_RELATIONSHIP, etc.
```

### 전체 CDM 사용 시
```
데이터베이스 구조:
├── webapi (스키마)       # WebAPI 메타데이터
├── omop_cdm (스키마)      # Vocabulary + Clinical 테이블
│   ├── CONCEPT (Vocabulary)
│   ├── PERSON (Clinical)
│   ├── VISIT_OCCURRENCE (Clinical)
│   └── ... 기타 CDM 테이블
└── cdm_results (스키마)   # 분석 결과 저장
```

---

## 참고 자료

- [Synthea](https://github.com/synthetichealth/synthea)
- [ETL-Synthea](https://github.com/OHDSI/ETL-Synthea)
- [OHDSI MIMIC](https://github.com/OHDSI/MIMIC)
- [Eunomia](https://github.com/OHDSI/Eunomia)
- [OMOP CDM GitHub](https://github.com/OHDSI/CommonDataModel)
- [OHDSI Athena](https://athena.ohdsi.org/)
