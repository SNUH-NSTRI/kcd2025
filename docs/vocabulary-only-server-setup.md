# Vocabulary 전용 OHDSI WebAPI 서버 구축 가이드

## 개요

데이터톤용으로 Vocabulary 검색 기능만 제공하는 경량 OHDSI WebAPI 서버를 구축합니다.
Docker 없이 자체 서버에 직접 설치합니다.

## 시스템 요구사항

### 하드웨어
- **CPU**: 4코어 이상
- **RAM**: 8GB 이상 (Vocabulary만 사용 시)
- **Storage**: SSD 50GB 이상

### 소프트웨어
- **OS**: Ubuntu 20.04+ / CentOS 7+ / macOS
- **PostgreSQL**: 12 이상
- **Java**: JDK 11
- **Maven**: 3.5+
- **Git**: 최신 버전

---

## Step 1: 환경 준비

### 1.1 Java 11 설치

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install openjdk-11-jdk -y
java -version  # 확인

# CentOS/RHEL
sudo yum install java-11-openjdk-devel -y

# macOS
brew install openjdk@11
```

### 1.2 PostgreSQL 설치

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib -y
sudo systemctl start postgresql
sudo systemctl enable postgresql

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib -y
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# macOS
brew install postgresql@14
brew services start postgresql@14
```

### 1.3 Maven 설치

```bash
# Ubuntu/Debian
sudo apt install maven -y

# CentOS/RHEL
sudo yum install maven -y

# macOS
brew install maven

# 확인
mvn -version
```

---

## Step 2: PostgreSQL 데이터베이스 설정

### 2.1 데이터베이스 및 사용자 생성

```bash
# PostgreSQL 접속
sudo -u postgres psql

# 또는 (macOS)
psql postgres
```

```sql
-- 데이터베이스 생성
CREATE DATABASE ohdsi_vocab_only;

-- 사용자 생성 (강력한 암호 사용!)
CREATE USER ohdsi_admin WITH PASSWORD 'YourSecurePassword123!';

-- 권한 부여
GRANT ALL PRIVILEGES ON DATABASE ohdsi_vocab_only TO ohdsi_admin;

-- 접속 확인
\c ohdsi_vocab_only
```

### 2.2 스키마 생성

```sql
-- WebAPI 메타데이터용 스키마
CREATE SCHEMA webapi AUTHORIZATION ohdsi_admin;

-- Vocabulary 테이블용 스키마
CREATE SCHEMA vocab AUTHORIZATION ohdsi_admin;

-- 확인
\dn
```

### 2.3 PostgreSQL 접속 허용 설정

```bash
# pg_hba.conf 편집
sudo nano /etc/postgresql/14/main/pg_hba.conf  # Ubuntu
# 또는
sudo nano /var/lib/pgsql/data/pg_hba.conf      # CentOS

# 아래 라인 추가 (로컬 접속 허용)
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             ohdsi_admin                             md5
host    all             ohdsi_admin     127.0.0.1/32            md5
host    all             ohdsi_admin     ::1/128                 md5

# PostgreSQL 재시작
sudo systemctl restart postgresql
```

### 2.4 접속 테스트

```bash
# 로컬 접속 테스트
psql -U ohdsi_admin -d ohdsi_vocab_only -h localhost

# 암호 입력 후 접속 성공 확인
\c
```

---

## Step 3: OMOP Vocabulary 다운로드 및 로드

### 3.1 Athena에서 Vocabulary 다운로드

1. https://athena.ohdsi.org/ 접속
2. 계정 생성/로그인
3. **Download** 탭 클릭
4. 기본 Vocabulary 선택 (또는 전체 선택)
5. **Download Vocabularies** 클릭
6. 이메일로 받은 링크에서 ZIP 파일 다운로드

```bash
# 다운로드 폴더 생성
mkdir -p ~/vocabulary_download
cd ~/vocabulary_download

# ZIP 파일 압축 해제
unzip vocabularies_*.zip
```

### 3.2 Vocabulary 테이블 생성

```sql
-- PostgreSQL 접속
psql -U ohdsi_admin -d ohdsi_vocab_only -h localhost

-- vocab 스키마로 전환
SET search_path TO vocab;
```

```sql
-- CONCEPT 테이블
CREATE TABLE vocab.concept (
    concept_id INTEGER NOT NULL,
    concept_name VARCHAR(255) NOT NULL,
    domain_id VARCHAR(20) NOT NULL,
    vocabulary_id VARCHAR(20) NOT NULL,
    concept_class_id VARCHAR(20) NOT NULL,
    standard_concept VARCHAR(1),
    concept_code VARCHAR(50) NOT NULL,
    valid_start_date DATE NOT NULL,
    valid_end_date DATE NOT NULL,
    invalid_reason VARCHAR(1)
);

-- CONCEPT_RELATIONSHIP 테이블
CREATE TABLE vocab.concept_relationship (
    concept_id_1 INTEGER NOT NULL,
    concept_id_2 INTEGER NOT NULL,
    relationship_id VARCHAR(20) NOT NULL,
    valid_start_date DATE NOT NULL,
    valid_end_date DATE NOT NULL,
    invalid_reason VARCHAR(1)
);

-- CONCEPT_ANCESTOR 테이블
CREATE TABLE vocab.concept_ancestor (
    ancestor_concept_id INTEGER NOT NULL,
    descendant_concept_id INTEGER NOT NULL,
    min_levels_of_separation INTEGER NOT NULL,
    max_levels_of_separation INTEGER NOT NULL
);

-- CONCEPT_SYNONYM 테이블
CREATE TABLE vocab.concept_synonym (
    concept_id INTEGER NOT NULL,
    concept_synonym_name VARCHAR(1000) NOT NULL,
    language_concept_id INTEGER NOT NULL
);

-- VOCABULARY 테이블
CREATE TABLE vocab.vocabulary (
    vocabulary_id VARCHAR(20) NOT NULL,
    vocabulary_name VARCHAR(255) NOT NULL,
    vocabulary_reference VARCHAR(255),
    vocabulary_version VARCHAR(255),
    vocabulary_concept_id INTEGER NOT NULL
);

-- DOMAIN 테이블
CREATE TABLE vocab.domain (
    domain_id VARCHAR(20) NOT NULL,
    domain_name VARCHAR(255) NOT NULL,
    domain_concept_id INTEGER NOT NULL
);

-- CONCEPT_CLASS 테이블
CREATE TABLE vocab.concept_class (
    concept_class_id VARCHAR(20) NOT NULL,
    concept_class_name VARCHAR(255) NOT NULL,
    concept_class_concept_id INTEGER NOT NULL
);

-- DRUG_STRENGTH 테이블
CREATE TABLE vocab.drug_strength (
    drug_concept_id INTEGER NOT NULL,
    ingredient_concept_id INTEGER NOT NULL,
    amount_value NUMERIC,
    amount_unit_concept_id INTEGER,
    numerator_value NUMERIC,
    numerator_unit_concept_id INTEGER,
    denominator_value NUMERIC,
    denominator_unit_concept_id INTEGER,
    box_size INTEGER,
    valid_start_date DATE NOT NULL,
    valid_end_date DATE NOT NULL,
    invalid_reason VARCHAR(1)
);
```

### 3.3 CSV 데이터 로드

```bash
# 로드 스크립트 생성
cat > ~/vocabulary_download/load_vocab.sh << 'EOF'
#!/bin/bash

VOCAB_DIR=~/vocabulary_download
DB_NAME=ohdsi_vocab_only
DB_USER=ohdsi_admin
DB_SCHEMA=vocab

echo "Loading Vocabulary tables..."

psql -U $DB_USER -d $DB_NAME -h localhost << SQL
SET search_path TO $DB_SCHEMA;

\echo 'Loading CONCEPT...'
\COPY concept FROM '${VOCAB_DIR}/CONCEPT.csv' WITH DELIMITER E'\t' CSV HEADER QUOTE E'\b';

\echo 'Loading CONCEPT_RELATIONSHIP...'
\COPY concept_relationship FROM '${VOCAB_DIR}/CONCEPT_RELATIONSHIP.csv' WITH DELIMITER E'\t' CSV HEADER QUOTE E'\b';

\echo 'Loading CONCEPT_ANCESTOR...'
\COPY concept_ancestor FROM '${VOCAB_DIR}/CONCEPT_ANCESTOR.csv' WITH DELIMITER E'\t' CSV HEADER QUOTE E'\b';

\echo 'Loading CONCEPT_SYNONYM...'
\COPY concept_synonym FROM '${VOCAB_DIR}/CONCEPT_SYNONYM.csv' WITH DELIMITER E'\t' CSV HEADER QUOTE E'\b';

\echo 'Loading VOCABULARY...'
\COPY vocabulary FROM '${VOCAB_DIR}/VOCABULARY.csv' WITH DELIMITER E'\t' CSV HEADER QUOTE E'\b';

\echo 'Loading DOMAIN...'
\COPY domain FROM '${VOCAB_DIR}/DOMAIN.csv' WITH DELIMITER E'\t' CSV HEADER QUOTE E'\b';

\echo 'Loading CONCEPT_CLASS...'
\COPY concept_class FROM '${VOCAB_DIR}/CONCEPT_CLASS.csv' WITH DELIMITER E'\t' CSV HEADER QUOTE E'\b';

\echo 'Loading DRUG_STRENGTH...'
\COPY drug_strength FROM '${VOCAB_DIR}/DRUG_STRENGTH.csv' WITH DELIMITER E'\t' CSV HEADER QUOTE E'\b';

\echo 'Vocabulary loading complete!'
SQL
EOF

chmod +x ~/vocabulary_download/load_vocab.sh
```

```bash
# 로드 실행 (10-30분 소요)
./load_vocab.sh
```

### 3.4 인덱스 생성 (성능 향상)

```sql
-- PostgreSQL 접속
psql -U ohdsi_admin -d ohdsi_vocab_only -h localhost

SET search_path TO vocab;

-- CONCEPT 인덱스
CREATE UNIQUE INDEX idx_concept_concept_id ON concept (concept_id);
CREATE INDEX idx_concept_code ON concept (concept_code);
CREATE INDEX idx_concept_vocab_id ON concept (vocabulary_id);
CREATE INDEX idx_concept_domain_id ON concept (domain_id);
CREATE INDEX idx_concept_class_id ON concept (concept_class_id);

-- CONCEPT_RELATIONSHIP 인덱스
CREATE INDEX idx_concept_relationship_id_1 ON concept_relationship (concept_id_1);
CREATE INDEX idx_concept_relationship_id_2 ON concept_relationship (concept_id_2);
CREATE INDEX idx_concept_relationship_id_3 ON concept_relationship (relationship_id);

-- CONCEPT_ANCESTOR 인덱스
CREATE INDEX idx_concept_ancestor_id_1 ON concept_ancestor (ancestor_concept_id);
CREATE INDEX idx_concept_ancestor_id_2 ON concept_ancestor (descendant_concept_id);

-- CONCEPT_SYNONYM 인덱스
CREATE INDEX idx_concept_synonym_id ON concept_synonym (concept_id);

-- Primary Keys
ALTER TABLE concept ADD CONSTRAINT xpk_concept PRIMARY KEY (concept_id);
ALTER TABLE vocabulary ADD CONSTRAINT xpk_vocabulary PRIMARY KEY (vocabulary_id);
ALTER TABLE domain ADD CONSTRAINT xpk_domain PRIMARY KEY (domain_id);
ALTER TABLE concept_class ADD CONSTRAINT xpk_concept_class PRIMARY KEY (concept_class_id);

-- Vacuum Analyze (통계 업데이트)
VACUUM ANALYZE;
```

---

## Step 4: WebAPI 빌드 및 설치

### 4.1 WebAPI 소스 다운로드

```bash
cd ~
git clone https://github.com/OHDSI/WebAPI.git
cd WebAPI
```

### 4.2 Maven 설정

```bash
# Maven settings.xml 생성
mkdir -p ~/.m2
cat > ~/.m2/settings.xml << 'EOF'
<settings>
  <profiles>
    <profile>
      <id>webapi-postgresql</id>
      <properties>
        <datasource.driver>org.postgresql.Driver</datasource.driver>
        <datasource.url>jdbc:postgresql://localhost:5432/ohdsi_vocab_only</datasource.url>
        <datasource.username>ohdsi_admin</datasource.username>
        <datasource.password>YourSecurePassword123!</datasource.password>
        <datasource.dialect>postgresql</datasource.dialect>
        <flyway.datasource.driver>${datasource.driver}</flyway.datasource.driver>
        <flyway.datasource.url>${datasource.url}</flyway.datasource.url>
        <flyway.datasource.username>${datasource.username}</flyway.datasource.username>
        <flyway.datasource.password>${datasource.password}</flyway.datasource.password>
        <flyway.locations>classpath:db/migration/postgresql</flyway.locations>
        <flyway.schemas>webapi</flyway.schemas>
      </properties>
    </profile>
  </profiles>
  <activeProfiles>
    <activeProfile>webapi-postgresql</activeProfile>
  </activeProfiles>
</settings>
EOF
```

### 4.3 WebAPI 빌드

```bash
cd ~/WebAPI

# 빌드 실행 (10-15분 소요)
mvn clean package -DskipTests

# 빌드 결과 확인
ls -lh target/WebAPI.war
```

### 4.4 Tomcat 설치

```bash
# Tomcat 9 다운로드
cd /opt
sudo wget https://dlcdn.apache.org/tomcat/tomcat-9/v9.0.93/bin/apache-tomcat-9.0.93.tar.gz
sudo tar -xzf apache-tomcat-9.0.93.tar.gz
sudo mv apache-tomcat-9.0.93 tomcat9
sudo chown -R $USER:$USER /opt/tomcat9
```

### 4.5 WebAPI 배포

```bash
# WAR 파일 복사
cp ~/WebAPI/target/WebAPI.war /opt/tomcat9/webapps/

# Tomcat 시작
/opt/tomcat9/bin/startup.sh

# 로그 확인 (배포 진행 상황)
tail -f /opt/tomcat9/logs/catalina.out
```

**예상 로그:**
```
INFO: Deployment of web application archive [/opt/tomcat9/webapps/WebAPI.war] has finished in [X] ms
```

---

## Step 5: Vocabulary 전용 Data Source 설정

### 5.1 WebAPI 메타데이터 확인

```bash
# WebAPI 상태 확인
curl http://localhost:8080/WebAPI/info

# 예상 응답:
# {"version": "2.13.0"}
```

### 5.2 Data Source 등록

```sql
-- PostgreSQL 접속
psql -U ohdsi_admin -d ohdsi_vocab_only -h localhost

-- Source 등록
INSERT INTO webapi.source (
    source_id,
    source_name,
    source_key,
    source_connection,
    source_dialect,
    cdm_database_schema
)
VALUES (
    1,
    'Vocabulary Only Source',
    'VOCAB_ONLY',
    'jdbc:postgresql://localhost:5432/ohdsi_vocab_only?user=ohdsi_admin&password=YourSecurePassword123!',
    'postgresql',
    'vocab'
);

-- 🔍 Vocabulary daimon만 활성화 (CDM, Results 제외)
INSERT INTO webapi.source_daimon (
    source_daimon_id,
    source_id,
    daimon_type,
    table_qualifier,
    priority
)
VALUES (1, 1, 1, 'vocab', 2);
-- daimon_type=1: Vocabulary만
-- daimon_type=0 (CDM), 2 (Results) 생략 -> 경량 구성

-- 확인
SELECT * FROM webapi.source;
SELECT * FROM webapi.source_daimon;
```

---

## Step 6: 검증 및 테스트

### 6.1 WebAPI 상태 확인

```bash
# API 정보
curl http://localhost:8080/WebAPI/info

# Source 목록
curl http://localhost:8080/WebAPI/source/sources

# 예상 응답:
# [{"sourceId":1,"sourceName":"Vocabulary Only Source","sourceKey":"VOCAB_ONLY",...}]
```

### 6.2 Vocabulary 검색 테스트

```bash
# Concept 검색 (aspirin)
curl "http://localhost:8080/WebAPI/vocabulary/1/search?query=aspirin&pageSize=10" | jq

# 특정 Concept 조회 (1551099: Antibiotic)
curl "http://localhost:8080/WebAPI/vocabulary/1/concept/1551099" | jq

# Concept 계층 구조
curl "http://localhost:8080/WebAPI/vocabulary/1/concept/1551099/ancestorGraph" | jq
```

### 6.3 Python에서 테스트

```python
import requests

BASE_URL = "http://localhost:8080/WebAPI"
SOURCE_ID = 1

# Concept 검색
response = requests.get(
    f"{BASE_URL}/vocabulary/{SOURCE_ID}/search",
    params={"query": "diabetes", "pageSize": 10}
)
print(response.json())

# 특정 Concept 조회
concept_id = 201826  # Type 2 diabetes mellitus
response = requests.get(
    f"{BASE_URL}/vocabulary/{SOURCE_ID}/concept/{concept_id}"
)
print(response.json())
```

---

## Step 7: 시스템 서비스 등록 (자동 시작)

### 7.1 Tomcat 서비스 생성

```bash
sudo nano /etc/systemd/system/tomcat9.service
```

```ini
[Unit]
Description=Apache Tomcat 9 Web Application Server
After=network.target postgresql.service

[Service]
Type=forking
User=youruser
Group=youruser

Environment="JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64"
Environment="CATALINA_HOME=/opt/tomcat9"
Environment="CATALINA_BASE=/opt/tomcat9"

ExecStart=/opt/tomcat9/bin/startup.sh
ExecStop=/opt/tomcat9/bin/shutdown.sh

RestartSec=10
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable tomcat9
sudo systemctl start tomcat9

# 상태 확인
sudo systemctl status tomcat9
```

---

## Step 8: 방화벽 및 보안 설정

### 8.1 방화벽 설정

```bash
# Ubuntu (UFW)
sudo ufw allow 8080/tcp
sudo ufw allow 5432/tcp  # PostgreSQL (필요시)
sudo ufw reload

# CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### 8.2 외부 접속 허용 (선택)

외부에서 접속을 허용하려면:

```bash
# PostgreSQL 외부 접속 설정
sudo nano /etc/postgresql/14/main/postgresql.conf

# 아래 라인 수정
listen_addresses = '*'

# pg_hba.conf 수정
sudo nano /etc/postgresql/14/main/pg_hba.conf

# 외부 IP 대역 추가
host    all    ohdsi_admin    0.0.0.0/0    md5

# PostgreSQL 재시작
sudo systemctl restart postgresql
```

---

## 트러블슈팅

### 문제 1: WebAPI 시작 실패

```bash
# 로그 확인
tail -f /opt/tomcat9/logs/catalina.out

# 포트 충돌 확인
sudo lsof -i :8080

# Tomcat 재시작
/opt/tomcat9/bin/shutdown.sh
/opt/tomcat9/bin/startup.sh
```

### 문제 2: Vocabulary 검색이 안됨

```sql
-- Data Source 설정 확인
SELECT * FROM webapi.source;
SELECT * FROM webapi.source_daimon;

-- Vocabulary 테이블 데이터 확인
SELECT COUNT(*) FROM vocab.concept;
SELECT COUNT(*) FROM vocab.concept_relationship;
```

### 문제 3: 데이터베이스 접속 오류

```bash
# PostgreSQL 로그 확인
sudo tail -f /var/log/postgresql/postgresql-14-main.log

# 접속 테스트
psql -U ohdsi_admin -d ohdsi_vocab_only -h localhost

# 암호 확인
grep password ~/.m2/settings.xml
```

### 문제 4: 메모리 부족

```bash
# Tomcat 메모리 설정
nano /opt/tomcat9/bin/setenv.sh

# 아래 내용 추가
export CATALINA_OPTS="-Xms2G -Xmx4G -XX:MaxPermSize=512m"

# Tomcat 재시작
/opt/tomcat9/bin/shutdown.sh
/opt/tomcat9/bin/startup.sh
```

---

## 코드 수정 (클라이언트)

### Python 클라이언트

```python
# src/pipeline/clients/ohdsi_client.py

class OHDSIClient:
    def __init__(self, base_url: str = "http://your-server-ip:8080/WebAPI"):
        """Vocabulary 전용 OHDSI WebAPI 클라이언트"""
        self.base_url = base_url
        self.source_id = 1  # Vocabulary Only Source
        # ... 나머지 코드
```

### 환경 변수 설정

```bash
# .env 파일
OHDSI_WEBAPI_URL=http://your-server-ip:8080/WebAPI
OHDSI_SOURCE_ID=1
```

---

## 성능 최적화

### PostgreSQL 튜닝

```bash
# postgresql.conf 편집
sudo nano /etc/postgresql/14/main/postgresql.conf

# 아래 설정 추가/수정
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 1GB
work_mem = 50MB
max_connections = 100

# 재시작
sudo systemctl restart postgresql
```

### 연결 풀링

WebAPI는 기본적으로 HikariCP를 사용합니다. 추가 설정 불필요.

---

## 백업 및 복구

### 데이터베이스 백업

```bash
# Vocabulary 백업
pg_dump -U ohdsi_admin -h localhost -d ohdsi_vocab_only > vocab_backup.sql

# 압축 백업
pg_dump -U ohdsi_admin -h localhost -d ohdsi_vocab_only | gzip > vocab_backup.sql.gz
```

### 복구

```bash
# 복구
psql -U ohdsi_admin -h localhost -d ohdsi_vocab_only < vocab_backup.sql

# 압축 파일 복구
gunzip -c vocab_backup.sql.gz | psql -U ohdsi_admin -h localhost -d ohdsi_vocab_only
```

---

## 설치 체크리스트

- [ ] Java 11 설치 완료
- [ ] PostgreSQL 설치 및 시작
- [ ] Maven 설치 완료
- [ ] 데이터베이스 `ohdsi_vocab_only` 생성
- [ ] 스키마 `webapi`, `vocab` 생성
- [ ] Athena에서 Vocabulary 다운로드
- [ ] Vocabulary CSV 로드 완료
- [ ] 인덱스 생성 완료
- [ ] WebAPI 빌드 성공
- [ ] Tomcat 설치 및 WebAPI 배포
- [ ] Data Source 등록 (Vocabulary only)
- [ ] WebAPI API 호출 테스트 성공
- [ ] 시스템 서비스 등록 (선택)

---

## 예상 소요 시간

| 단계 | 소요 시간 |
|------|----------|
| 환경 준비 (Java, PostgreSQL, Maven) | 30분 |
| PostgreSQL 설정 | 15분 |
| Vocabulary 다운로드 | 30분 |
| Vocabulary 로드 | 20-30분 |
| 인덱스 생성 | 10-15분 |
| WebAPI 빌드 | 10-15분 |
| Tomcat 설치 및 배포 | 15분 |
| Data Source 설정 및 테스트 | 10분 |
| **총합** | **2.5-3시간** |

---

## 참고 자료

- [OHDSI WebAPI GitHub](https://github.com/OHDSI/WebAPI)
- [OHDSI Forums](https://forums.ohdsi.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Apache Tomcat Documentation](https://tomcat.apache.org/tomcat-9.0-doc/)
