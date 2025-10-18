# OHDSI WebAPI 자체 구축 가이드

## 개요

공개 OHDSI API(`https://api.ohdsi.org/WebAPI`)가 불안정하여 자체 OHDSI WebAPI 서버를 구축합니다.

## 필요한 데이터 구성 요소

### ✅ Vocabulary 검색만 사용하는 경우 (우리 케이스)

**필요한 것:**

1. **Athena Vocabulary 데이터** (약 5-10GB)
   - `CONCEPT` - 모든 의학 용어 (약 600만 개)
   - `CONCEPT_RELATIONSHIP` - 용어 간 매핑 관계 ⭐ 가장 중요
   - `CONCEPT_ANCESTOR` - 계층 구조 (효율적 검색)
   - `CONCEPT_SYNONYM` - 동의어/별칭 (검색 개선)
   - `VOCABULARY`, `DOMAIN`, `CONCEPT_CLASS`, `DRUG_STRENGTH`

2. **WebAPI 메타데이터 스키마**
   - WebAPI가 자동 생성
   - Data Source 설정 정보 저장

**불필요한 것:**

- ❌ 실제 환자 데이터 (PERSON, CONDITION_OCCURRENCE 등)
- ❌ CDM clinical 테이블들 (비어있어도 무방)
- ❌ Results 스키마 (코호트 결과 저장용)

### 🔍 Vocabulary 전용 최소 구성

데이터베이스 구조:

```text
ohdsi_webapi (데이터베이스)
├── webapi (스키마)           # WebAPI 메타데이터 - 자동 생성
└── omop_cdm (스키마)          # Vocabulary 테이블만
    ├── CONCEPT
    ├── CONCEPT_RELATIONSHIP
    ├── CONCEPT_ANCESTOR
    ├── CONCEPT_SYNONYM
    ├── VOCABULARY
    ├── DOMAIN
    ├── CONCEPT_CLASS
    └── DRUG_STRENGTH
```

## 권장 방법: Docker (Broadsea) 사용

### 1. 사전 준비

**필요 사양:**
- CPU: 4코어 이상
- RAM: 16GB 이상
- Storage: SSD 200GB 이상
- Docker Engine 및 Docker Compose 설치

**설치:**
```bash
# Docker Desktop (Mac/Windows)
# https://www.docker.com/products/docker-desktop

# Linux
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 2. Docker Compose 설정

`docker-compose.yml` 파일 생성:

```yaml
version: '3.8'
services:
  database:
    image: ohdsi/broadsea-database:2.1.0  # PostgreSQL + Vocabulary 포함
    container_name: broadsea-database
    environment:
      - POSTGRES_PASSWORD=mysecretpassword  # 강력한 암호로 변경
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  webapi:
    image: ohdsi/broadsea-webtools:2.1.0  # WebAPI + ATLAS 포함
    container_name: broadsea-webtools
    ports:
      - "8080:8080"
    environment:
      - DATABASE_HOST=database
      - DATABASE_PORT=5432
      - POSTGRES_PASSWORD=mysecretpassword  # database와 동일
      - CDM_SCHEMA=public
      - WEBAPI_SCHEMA=ohdsi
      - RESULTS_SCHEMA=ohdsi_results
    depends_on:
      database:
        condition: service_healthy

volumes:
  postgres_data:
```

### 3. 실행

```bash
# 컨테이너 시작 (백그라운드)
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 상태 확인
docker-compose ps
```

### 4. 검증

#### 4.1 WebAPI 상태 확인

```bash
# API 정보 조회
curl http://localhost:8080/WebAPI/info

# 예상 응답:
# {"version": "2.13.0"}
```

#### 4.2 ATLAS UI 접속

브라우저에서 접속:
- ATLAS: `http://localhost:8080/atlas`
- WebAPI: `http://localhost:8080/WebAPI`

#### 4.3 Vocabulary 검색 테스트

```bash
# Concept 검색 테스트
curl "http://localhost:8080/WebAPI/vocabulary/search/1551099"

# 여러 개념 검색
curl "http://localhost:8080/WebAPI/vocabulary/search?query=aspirin&pageSize=10"
```

### 5. 데이터 소스 설정

ATLAS UI에서 설정:
1. `http://localhost:8080/atlas/#/configure` 접속
2. Data Sources 추가
3. 연결 정보 입력:
   - Name: My Local CDM
   - Connection: `jdbc:postgresql://database:5432/postgres`
   - Username: postgres
   - Password: mysecretpassword
   - CDM Schema: public

또는 SQL로 직접 설정:

```sql
-- PostgreSQL에 접속
docker exec -it broadsea-database psql -U postgres

-- Source 등록
INSERT INTO ohdsi.source (source_id, source_name, source_key, source_connection, source_dialect, cdm_database_schema)
VALUES (1, 'My Local CDM', 'MY_CDM',
        'jdbc:postgresql://database:5432/postgres?user=postgres&password=mysecretpassword',
        'postgresql', 'public');

-- Daimon 등록
-- 🔍 Vocabulary 전용 구성: daimon_type=1만 사용 (CDM, Results 제외)
INSERT INTO ohdsi.source_daimon (source_daimon_id, source_id, daimon_type, table_qualifier, priority)
VALUES
    (1, 1, 1, 'public', 2);      -- Vocabulary만 활성화

-- 전체 기능 사용시 (환자 데이터 있는 경우):
-- (1, 1, 0, 'public', 2),      -- CDM
-- (2, 1, 1, 'public', 2),      -- Vocabulary
-- (3, 1, 2, 'ohdsi_results', 2); -- Results
```

### 6. 코드 수정

`src/pipeline/clients/ohdsi_client.py` 수정:

```python
class OHDSIClient:
    def __init__(self, base_url: str = "http://localhost:8080/WebAPI"):
        """로컬 OHDSI WebAPI 사용"""
        self.base_url = base_url
        # ... 나머지 코드
```

환경 변수로 설정:

```bash
# .env 파일
OHDSI_WEBAPI_URL=http://localhost:8080/WebAPI
```

### 7. 관리 명령어

```bash
# 중지
docker-compose stop

# 재시작
docker-compose restart

# 완전 삭제 (데이터 유지)
docker-compose down

# 완전 삭제 (데이터 포함)
docker-compose down -v

# 로그 확인
docker-compose logs webapi
docker-compose logs database
```

## 대안: 수동 설치

자세한 커스터마이징이 필요한 경우:

### 구성요소
- PostgreSQL 12+
- Java JDK 11
- Apache Tomcat 9+
- Maven 3.5+

### 설치 단계

1. **WebAPI 소스 클론**
```bash
git clone https://github.com/OHDSI/WebAPI.git
cd WebAPI
```

2. **PostgreSQL 설정**
```sql
CREATE DATABASE ohdsi_webapi;
CREATE USER ohdsi_admin WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE ohdsi_webapi TO ohdsi_admin;

CREATE SCHEMA webapi AUTHORIZATION ohdsi_admin;
CREATE SCHEMA omop_cdm AUTHORIZATION ohdsi_admin;
CREATE SCHEMA cdm_results AUTHORIZATION ohdsi_admin;
```

3. **Maven 빌드**
```bash
# ~/.m2/settings.xml 설정 후
mvn clean package -DskipTests
```

4. **Tomcat 배포**
```bash
cp target/WebAPI.war $TOMCAT_HOME/webapps/
```

5. **Vocabulary 로드**
- [OHDSI Athena](https://athena.ohdsi.org/)에서 다운로드
- [CommonDataModel](https://github.com/OHDSI/CommonDataModel) 스크립트 사용

## 트러블슈팅

### 문제: 컨테이너가 시작되지 않음
```bash
# 로그 확인
docker-compose logs

# 포트 충돌 확인
lsof -i :8080
lsof -i :5432
```

### 문제: Vocabulary 검색이 안됨
- Data Sources가 올바르게 설정되었는지 확인
- ATLAS UI에서 Data Sources 상태 확인 (초록색 체크)

### 문제: 메모리 부족
```yaml
# docker-compose.yml에 추가
services:
  webapi:
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
```

## 참고 자료

- [OHDSI WebAPI GitHub](https://github.com/OHDSI/WebAPI)
- [Broadsea Documentation](https://github.com/OHDSI/Broadsea)
- [OHDSI Athena](https://athena.ohdsi.org/)
- [OHDSI Forums](https://forums.ohdsi.org/)
