# Local Vocabulary 사용 가이드

## 개요

WebAPI 서버 없이 Athena Vocabulary CSV 파일을 Pandas로 직접 검색하는 경량 시스템입니다.

## 장점

- ✅ **간단함**: 서버 설치 불필요, CSV 파일만 있으면 됨
- ✅ **빠름**: 로컬 메모리에서 검색 (첫 로딩 후 빠름)
- ✅ **가벼움**: PostgreSQL, Tomcat 등 불필요
- ✅ **이식성**: 어디서든 실행 가능

## 사전 준비

### 1. Vocabulary 다운로드

1. https://athena.ohdsi.org/ 접속
2. 계정 생성/로그인
3. Vocabulary 다운로드
4. `vocabulary/` 디렉토리에 압축 해제

```bash
# 프로젝트 루트에 vocabulary 디렉토리 생성
mkdir -p vocabulary
cd vocabulary

# ZIP 파일 압축 해제
unzip vocabularies_*.zip
```

### 2. 필요한 파일 확인

```
vocabulary/
├── CONCEPT.csv               (필수) 828MB
├── CONCEPT_RELATIONSHIP.csv  (필수) 1.8GB
├── CONCEPT_ANCESTOR.csv      (필수) 1.5GB
├── CONCEPT_SYNONYM.csv       (필수) 197MB
├── VOCABULARY.csv            (선택) 6KB
└── DOMAIN.csv                (선택) 2KB
```

## 기본 사용법

### 초기화

```python
from src.pipeline.local_vocabulary import get_vocabulary

# Vocabulary 인스턴스 생성 (싱글톤)
vocab = get_vocabulary(vocab_dir="vocabulary")
```

### 1. 개념 검색

```python
# 기본 검색
results = vocab.search_concepts("diabetes", limit=10)

# 도메인 필터 (Drug, Condition, Procedure 등)
results = vocab.search_concepts("aspirin", domain="Drug", limit=10)

# Vocabulary 필터 (RxNorm, SNOMED, ICD10CM 등)
results = vocab.search_concepts("E11", vocabulary="ICD10CM", limit=10)

# 비표준 개념 포함
results = vocab.search_concepts("diabetes", standard_only=False, limit=10)

# 결과 확인
print(results[["concept_id", "concept_name", "domain_id", "vocabulary_id"]])
```

### 2. 특정 개념 조회

```python
# ID로 조회
concept = vocab.get_concept_by_id(201826)  # Type 2 diabetes

if concept:
    print(f"Name: {concept['concept_name']}")
    print(f"Domain: {concept['domain_id']}")
    print(f"Vocabulary: {concept['vocabulary_id']}")
```

### 3. 개념 매핑 (소스 → 표준)

```python
# ICD10CM → SNOMED 매핑
icd_concept_id = 45552588  # ICD10CM: E11
mappings = vocab.get_concept_mappings(icd_concept_id, relationship_id="Maps to")

print(mappings[["concept_id", "concept_name", "vocabulary_id"]])
```

### 4. 계층 구조 조회

```python
# 상위 개념 (부모)
ancestors = vocab.get_concept_ancestors(201826, max_levels=3)
print(ancestors[["concept_id", "concept_name", "min_levels_of_separation"]])

# 하위 개념 (자식)
descendants = vocab.get_concept_descendants(201826, max_levels=2)
print(descendants[["concept_id", "concept_name", "min_levels_of_separation"]])
```

### 5. 원스톱 검색 및 매핑

```python
# 검색 → 표준 개념으로 자동 매핑
standard_concepts = vocab.search_and_map("aspirin", domain="Drug", limit=5)

for concept in standard_concepts:
    print(f"ID: {concept['concept_id']}")
    print(f"Name: {concept['concept_name']}")
    print(f"Vocabulary: {concept['vocabulary_id']}")
    print()
```

## 실전 예제

### 예제 1: 약물 검색

```python
from src.pipeline.local_vocabulary import get_vocabulary

vocab = get_vocabulary()

# 메트포르민 검색
results = vocab.search_and_map("metformin", domain="Drug", limit=10)

for drug in results:
    print(f"✓ {drug['concept_name']} (ID: {drug['concept_id']})")
```

### 예제 2: 질병 코드 매핑

```python
# ICD-10 코드 → SNOMED 표준 개념
icd10_results = vocab.search_concepts(
    "E11",
    vocabulary="ICD10CM",
    standard_only=False
)

for _, icd_concept in icd10_results.iterrows():
    print(f"\nICD-10: {icd_concept['concept_name']}")

    # 표준 개념으로 매핑
    mappings = vocab.get_concept_mappings(icd_concept['concept_id'])
    for _, mapping in mappings.iterrows():
        print(f"  → SNOMED: {mapping['concept_name']}")
```

### 예제 3: 질병 계층 탐색

```python
# Type 2 diabetes의 상위/하위 개념
diabetes_id = 201826

# 상위 카테고리
print("상위 개념:")
ancestors = vocab.get_concept_ancestors(diabetes_id, max_levels=3)
for _, ancestor in ancestors.iterrows():
    level = ancestor['min_levels_of_separation']
    indent = "  " * level
    print(f"{indent}↑ {ancestor['concept_name']}")

# 하위 세부 유형
print("\n하위 개념:")
descendants = vocab.get_concept_descendants(diabetes_id, max_levels=2)
for _, descendant in descendants.iterrows():
    level = descendant['min_levels_of_separation']
    indent = "  " * level
    print(f"{indent}↓ {descendant['concept_name']}")
```

## 성능 최적화

### Lazy Loading

CSV 파일은 실제 사용할 때만 로드됩니다:

```python
vocab = get_vocabulary()  # 빠름 (파일 로드 안 함)

# 첫 검색 시 CONCEPT.csv 로드 (9초)
results = vocab.search_concepts("diabetes")

# 이후 검색은 빠름 (메모리에서)
results = vocab.search_concepts("aspirin")
```

### 메모리 관리

대용량 CSV 파일로 인해 메모리 사용량이 높을 수 있습니다:

- CONCEPT.csv: ~2GB RAM
- CONCEPT_RELATIONSHIP.csv: ~4GB RAM
- CONCEPT_ANCESTOR.csv: ~3GB RAM

**총 메모리 사용량: 약 8-10GB**

필요한 테이블만 사용하려면:

```python
# 직접 속성 접근 (필요한 것만)
concept_df = vocab.concept  # CONCEPT만 로드
```

## 기존 OHDSIClient와 비교

### OHDSIClient (WebAPI 방식)

```python
from src.pipeline.clients.ohdsi_client import OHDSIClient

client = OHDSIClient("https://api.ohdsi.org/WebAPI")
results = client.search_standard_concepts("diabetes")
```

**문제점:**
- ❌ 외부 API 의존 (불안정)
- ❌ 네트워크 필요
- ❌ 속도 느림

### LocalVocabulary (로컬 방식)

```python
from src.pipeline.local_vocabulary import get_vocabulary

vocab = get_vocabulary()
results = vocab.search_concepts("diabetes")
```

**장점:**
- ✅ 완전히 독립적
- ✅ 오프라인 작동
- ✅ 빠른 속도 (메모리)

## 통합 사용

기존 코드를 최소한으로 수정하여 사용:

```python
from src.pipeline.local_vocabulary import get_vocabulary

# 기존 OHDSIClient 대신 LocalVocabulary 사용
vocab = get_vocabulary()

def search_standard_concepts(query: str, domain: str = None) -> list:
    """OHDSIClient 호환 인터페이스"""
    results = vocab.search_and_map(query, domain=domain, limit=10)
    return results
```

## 트러블슈팅

### 문제 1: FileNotFoundError

```
FileNotFoundError: Vocabulary directory not found: vocabulary
```

**해결:**
```bash
# vocabulary 디렉토리 확인
ls -la vocabulary/

# 없으면 생성 및 파일 복사
mkdir -p vocabulary
cp ~/Downloads/vocabulary_download_v5_*/*.csv vocabulary/
```

### 문제 2: MemoryError

```
MemoryError: Unable to allocate array
```

**해결:**
- 메모리 8GB 이상 권장
- 다른 프로그램 종료
- Swap 메모리 활성화

### 문제 3: 검색 속도 느림

**해결:**
```python
# 첫 로딩 후에는 빠름 (캐싱)
vocab = get_vocabulary()

# 첫 검색 (느림 - CSV 로딩)
results1 = vocab.search_concepts("diabetes")  # 9초

# 이후 검색 (빠름 - 메모리에서)
results2 = vocab.search_concepts("aspirin")   # 0.5초
```

### 문제 4: 빈 검색 결과

```python
# 표준 개념이 없는 경우
results = vocab.search_concepts("E11", standard_only=True)  # Empty

# 비표준 포함하여 검색
results = vocab.search_concepts("E11", standard_only=False)  # OK

# 또는 vocabulary 필터 사용
results = vocab.search_concepts("E11", vocabulary="ICD10CM", standard_only=False)
```

## 주의사항

1. **초기 로딩 시간**: 첫 검색 시 CSV 로딩으로 9-15초 소요
2. **메모리 사용량**: 8-10GB RAM 필요 (대용량 CSV)
3. **Vocabulary 업데이트**: Athena에서 정기적으로 재다운로드 필요
4. **표준 개념**: `standard_concept='S'`인 것만 사용 권장

## 참고 자료

- [OHDSI Athena](https://athena.ohdsi.org/)
- [OMOP CDM Vocabulary](https://ohdsi.github.io/CommonDataModel/cdm54.html#CONCEPT)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
