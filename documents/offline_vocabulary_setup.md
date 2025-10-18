# Offline Vocabulary Setup for Trialist Agent

## 🎯 내부망 환경을 위한 오프라인 어휘 구축 방안

내부망 환경에서 Trialist Agent의 Stage 2 (Standardization) 및 Stage 3 (CDM Mapping)을 구현하기 위해 필요한 어휘 데이터를 로컬로 구축하는 방법을 제시합니다.

## 📋 필요 데이터 소스

### 1. UMLS (Unified Medical Language System)
**다운로드 방법:**
- **공식 사이트**: https://www.nlm.nih.gov/research/umls/
- **라이선스**: 무료 (UMLS Metathesaurus License Agreement 필요)
- **파일 크기**: ~15GB (압축), ~50GB (압축 해제)
- **파일 형태**: MySQL dump, RRF files

**주요 테이블:**
```
MRCONSO.RRF  - Concept names and sources (핵심)
MRSTY.RRF    - Semantic types
MRREL.RRF    - Related concepts
MRRANK.RRF   - Source ranking
MRSAT.RRF    - Simple attributes
```

### 2. OHDSI Athena Vocabularies
**다운로드 방법:**
- **사이트**: https://athena.ohdsi.org/
- **계정**: 무료 등록 후 다운로드
- **파일 크기**: ~5GB (압축)
- **업데이트**: 월별

**주요 파일:**
```
CONCEPT.csv           - All concepts
CONCEPT_RELATIONSHIP.csv - Relationships between concepts
CONCEPT_SYNONYM.csv   - Alternative names
VOCABULARY.csv        - Vocabulary metadata
DOMAIN.csv           - Domain classifications
```

### 3. 개별 표준 어휘
- **ICD-10-CM**: CDC에서 무료 제공
- **RxNorm**: NLM에서 무료 제공
- **LOINC**: Regenstrief Institute (무료 등록)
- **SNOMED CT**: 국가별 라이선스 (한국: 건강보험심사평가원)

## 🗄️ 로컬 데이터베이스 설계

### SQLite 기반 경량 구조
```sql
-- concepts 테이블: 모든 개념 정보
CREATE TABLE concepts (
    concept_id INTEGER PRIMARY KEY,
    concept_name TEXT NOT NULL,
    domain_id TEXT,
    vocabulary_id TEXT,
    concept_class_id TEXT,
    concept_code TEXT,
    valid_start_date DATE,
    valid_end_date DATE,
    invalid_reason TEXT
);

-- concept_synonyms 테이블: 동의어 매핑
CREATE TABLE concept_synonyms (
    synonym_id INTEGER PRIMARY KEY,
    concept_id INTEGER,
    synonym_name TEXT,
    language_concept_id INTEGER,
    FOREIGN KEY (concept_id) REFERENCES concepts (concept_id)
);

-- concept_relationships 테이블: 개념 간 관계
CREATE TABLE concept_relationships (
    relationship_id INTEGER PRIMARY KEY,
    concept_id_1 INTEGER,
    concept_id_2 INTEGER,
    relationship_id_code TEXT,
    valid_start_date DATE,
    valid_end_date DATE,
    FOREIGN KEY (concept_id_1) REFERENCES concepts (concept_id),
    FOREIGN KEY (concept_id_2) REFERENCES concepts (concept_id)
);

-- domain_mapping 테이블: Trialist domain 매핑
CREATE TABLE domain_mapping (
    mapping_id INTEGER PRIMARY KEY,
    trialist_domain TEXT,  -- "Condition", "Drug", etc.
    omop_domain_id TEXT,   -- "Condition", "Drug", etc.
    vocabulary_preference INTEGER  -- 1=primary, 2=secondary
);
```

### 인덱스 최적화
```sql
CREATE INDEX idx_concepts_name ON concepts(concept_name);
CREATE INDEX idx_concepts_code ON concepts(concept_code);
CREATE INDEX idx_synonyms_name ON concept_synonyms(synonym_name);
CREATE INDEX idx_synonyms_concept ON concept_synonyms(concept_id);
```

## 🛠️ 구현 계획

### Phase 1: 데이터 수집 및 전처리
```python
# vocabulary_builder.py
class VocabularyBuilder:
    def __init__(self, data_dir: Path, db_path: Path):
        self.data_dir = data_dir
        self.db_path = db_path
    
    def download_umls(self):
        """UMLS 데이터 다운로드 (수동 다운로드 후 처리)"""
        
    def download_athena(self):
        """Athena 데이터 다운로드"""
        
    def process_umls_files(self):
        """UMLS RRF 파일들을 SQLite로 변환"""
        
    def process_athena_files(self):
        """Athena CSV 파일들을 SQLite로 변환"""
        
    def build_unified_database(self):
        """통합 어휘 DB 구축"""
```

### Phase 2: 오프라인 표준화 모듈
```python
# offline_standardizer.py  
class OfflineStandardizer:
    def __init__(self, db_path: Path):
        self.db = sqlite3.connect(db_path)
        self._setup_fuzzy_matching()
    
    def standardize_concept(self, text: str, domain: str) -> StandardizedConcept:
        """텍스트를 표준 개념으로 매핑"""
        
    def find_best_matches(self, text: str, limit: int = 5):
        """유사도 기반 매칭"""
        
    def get_domain_vocabularies(self, trialist_domain: str) -> List[str]:
        """도메인별 우선 어휘 반환"""
```

### Phase 3: 고급 매칭 알고리즘
```python
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz
import re

class ConceptMatcher:
    def __init__(self, db_connection):
        self.db = db_connection
        self.abbreviation_map = self._load_abbreviations()
    
    def fuzzy_match(self, query: str, threshold: float = 0.8):
        """퍼지 매칭을 통한 개념 검색"""
        
    def exact_match(self, query: str):
        """정확한 매칭"""
        
    def abbreviation_expand(self, text: str):
        """약어 확장 (MI -> Myocardial Infarction)"""
        
    def semantic_match(self, query: str, domain: str):
        """도메인별 의미론적 매칭"""
```

## 📦 데이터 준비 스크립트

### 1. UMLS 데이터 처리
```python
# scripts/build_umls_db.py
import pandas as pd
import sqlite3
from pathlib import Path

def process_mrconso_file(rrf_path: Path, db_path: Path):
    """MRCONSO.RRF 파일을 SQLite로 변환"""
    
    # RRF 파일 컬럼 정의
    columns = [
        'CUI', 'LAT', 'TS', 'LUI', 'STT', 'SUI', 'ISPREF', 'AUI',
        'SAUI', 'SCUI', 'SDUI', 'SAB', 'TTY', 'CODE', 'STR', 'SRL', 'SUPPRESS', 'CVF'
    ]
    
    # 청크별로 처리 (메모리 효율성)
    chunk_size = 10000
    
    with sqlite3.connect(db_path) as conn:
        for chunk in pd.read_csv(rrf_path, sep='|', names=columns, 
                                 chunksize=chunk_size, dtype=str):
            # 영어만 필터링
            chunk = chunk[chunk['LAT'] == 'ENG']
            
            # 필요한 컬럼만 선택
            processed = chunk[['CUI', 'STR', 'SAB', 'CODE']].copy()
            processed.columns = ['umls_cui', 'concept_name', 'source', 'source_code']
            
            # SQLite에 삽입
            processed.to_sql('umls_concepts', conn, if_exists='append', index=False)

if __name__ == "__main__":
    # 사용 예시
    umls_dir = Path("data/umls/2024AA/META")
    db_path = Path("vocabularies/umls.db")
    
    process_mrconso_file(umls_dir / "MRCONSO.RRF", db_path)
```

### 2. Athena 데이터 처리
```python
# scripts/build_athena_db.py
def process_athena_concepts(csv_dir: Path, db_path: Path):
    """Athena CONCEPT.csv를 SQLite로 변환"""
    
    concept_df = pd.read_csv(csv_dir / "CONCEPT.csv", sep='\t')
    
    # Trialist domain 매핑 추가
    domain_mapping = {
        'Condition': ['Condition'],
        'Drug': ['Drug'], 
        'Measurement': ['Measurement'],
        'Procedure': ['Procedure'],
        'Device': ['Device'],
        'Observation': ['Observation'],
        'Visit': ['Visit']
    }
    
    with sqlite3.connect(db_path) as conn:
        concept_df.to_sql('athena_concepts', conn, if_exists='replace', index=False)
        
        # 도메인 매핑 테이블 생성
        mapping_rows = []
        for trialist_domain, omop_domains in domain_mapping.items():
            for i, omop_domain in enumerate(omop_domains, 1):
                mapping_rows.append({
                    'trialist_domain': trialist_domain,
                    'omop_domain_id': omop_domain,
                    'vocabulary_preference': i
                })
        
        mapping_df = pd.DataFrame(mapping_rows)
        mapping_df.to_sql('domain_mapping', conn, if_exists='replace', index=False)
```

## 🔧 Trialist Parser 오프라인 모드 구현

```python
# trialist_offline_stages.py
from pathlib import Path
import sqlite3
from typing import List, Optional, Tuple

class OfflineStandardizationStage:
    def __init__(self, vocab_db_path: Path):
        self.db_path = vocab_db_path
        self.db = None
    
    def __enter__(self):
        self.db = sqlite3.connect(self.db_path)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()
    
    def standardize_entity(self, entity: EnhancedNamedEntity) -> EnhancedNamedEntity:
        """Entity를 표준화"""
        
        # 1. 정확한 매칭 시도
        exact_match = self._exact_match(entity.text, entity.domain)
        if exact_match:
            return self._create_standardized_entity(entity, exact_match)
        
        # 2. 퍼지 매칭 시도  
        fuzzy_matches = self._fuzzy_match(entity.text, entity.domain)
        if fuzzy_matches:
            best_match = fuzzy_matches[0]  # 최고 점수
            if best_match['similarity'] > 0.8:
                return self._create_standardized_entity(entity, best_match)
        
        # 3. 표준화 실패시 원본 반환
        return entity
    
    def _exact_match(self, text: str, domain: str) -> Optional[dict]:
        """정확한 텍스트 매칭"""
        query = """
        SELECT ac.concept_id, ac.concept_name, ac.vocabulary_id, ac.concept_code,
               uc.umls_cui
        FROM athena_concepts ac
        LEFT JOIN umls_concepts uc ON LOWER(ac.concept_name) = LOWER(uc.concept_name)
        JOIN domain_mapping dm ON ac.domain_id = dm.omop_domain_id
        WHERE LOWER(ac.concept_name) = LOWER(?)
          AND dm.trialist_domain = ?
          AND ac.invalid_reason IS NULL
        ORDER BY dm.vocabulary_preference
        LIMIT 1
        """
        
        cursor = self.db.execute(query, (text.lower(), domain))
        row = cursor.fetchone()
        
        if row:
            return {
                'concept_id': row[0],
                'concept_name': row[1], 
                'vocabulary_id': row[2],
                'concept_code': row[3],
                'umls_cui': row[4],
                'similarity': 1.0
            }
        return None
    
    def _fuzzy_match(self, text: str, domain: str, limit: int = 5) -> List[dict]:
        """유사도 기반 매칭"""
        # SQLite LIKE 검색으로 후보 축소
        query = """
        SELECT ac.concept_id, ac.concept_name, ac.vocabulary_id, ac.concept_code,
               uc.umls_cui
        FROM athena_concepts ac
        LEFT JOIN umls_concepts uc ON LOWER(ac.concept_name) = LOWER(uc.concept_name)
        JOIN domain_mapping dm ON ac.domain_id = dm.omop_domain_id
        WHERE ac.concept_name LIKE ?
          AND dm.trialist_domain = ?
          AND ac.invalid_reason IS NULL
        ORDER BY dm.vocabulary_preference
        LIMIT 50
        """
        
        cursor = self.db.execute(query, (f"%{text[:3]}%", domain))
        candidates = cursor.fetchall()
        
        # Python에서 유사도 계산
        matches = []
        for candidate in candidates:
            similarity = self._calculate_similarity(text, candidate[1])
            if similarity > 0.6:  # 임계값
                matches.append({
                    'concept_id': candidate[0],
                    'concept_name': candidate[1],
                    'vocabulary_id': candidate[2], 
                    'concept_code': candidate[3],
                    'umls_cui': candidate[4],
                    'similarity': similarity
                })
        
        return sorted(matches, key=lambda x: x['similarity'], reverse=True)[:limit]
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """텍스트 유사도 계산"""
        from difflib import SequenceMatcher
        
        # 전처리
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # 정확한 매칭
        if text1 == text2:
            return 1.0
        
        # 순차 유사도
        seq_sim = SequenceMatcher(None, text1, text2).ratio()
        
        # 단어 기반 유사도 (선택사항)
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if words1 and words2:
            word_sim = len(words1.intersection(words2)) / len(words1.union(words2))
            return max(seq_sim, word_sim)
        
        return seq_sim
    
    def _create_standardized_entity(self, original: EnhancedNamedEntity, match: dict) -> EnhancedNamedEntity:
        """표준화된 entity 생성"""
        return EnhancedNamedEntity(
            text=original.text,
            type=original.type,
            domain=original.domain,
            start=original.start,
            end=original.end,
            confidence=original.confidence,
            # 표준화 정보 추가
            standard_name=match['concept_name'],
            umls_cui=match['umls_cui'],
            code_system=match['vocabulary_id'],
            code_set=[match['concept_code']] if match['concept_code'] else None,
            primary_code=match['concept_code'],
            metadata={
                **(original.metadata or {}),
                'standardization': {
                    'method': 'offline_exact' if match['similarity'] == 1.0 else 'offline_fuzzy',
                    'similarity_score': match['similarity'],
                    'concept_id': match['concept_id']
                }
            }
        )
```

## 📋 설치 및 설정 가이드

### 1. 데이터 다운로드 스크립트
```bash
#!/bin/bash
# setup_offline_vocab.sh

echo "Setting up offline vocabularies for Trialist Agent..."

# 디렉토리 생성
mkdir -p data/vocabularies
mkdir -p data/raw/umls
mkdir -p data/raw/athena

# UMLS 다운로드 안내 (수동)
echo "1. UMLS 다운로드:"
echo "   - https://uts.nlm.nih.gov/uts/ 에서 계정 생성"
echo "   - UMLS Metathesaurus 다운로드"
echo "   - data/raw/umls/ 에 압축 해제"
echo ""

# Athena 다운로드 안내 (수동)
echo "2. Athena 다운로드:"
echo "   - https://athena.ohdsi.org/ 에서 계정 생성"
echo "   - 필요한 vocabulary 선택 후 다운로드"
echo "   - data/raw/athena/ 에 압축 해제"
echo ""

# 처리 스크립트 실행
echo "3. 데이터 처리 중..."
python scripts/build_vocabulary_db.py

echo "오프라인 어휘 설정 완료!"
```

### 2. 통합 빌드 스크립트
```python
# scripts/build_vocabulary_db.py
def main():
    """오프라인 어휘 DB 통합 빌드"""
    
    raw_data_dir = Path("data/raw")
    vocab_db_path = Path("data/vocabularies/trialist_vocab.db")
    
    print("Building offline vocabulary database...")
    
    # 1. UMLS 처리
    if (raw_data_dir / "umls/META").exists():
        print("Processing UMLS data...")
        process_umls_data(raw_data_dir / "umls/META", vocab_db_path)
    
    # 2. Athena 처리  
    if (raw_data_dir / "athena").exists():
        print("Processing Athena data...")
        process_athena_data(raw_data_dir / "athena", vocab_db_path)
    
    # 3. 인덱스 생성
    print("Creating database indexes...")
    create_indexes(vocab_db_path)
    
    print(f"Vocabulary database created: {vocab_db_path}")
    print(f"Database size: {vocab_db_path.stat().st_size / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    main()
```

이 방법으로 완전히 오프라인 환경에서도 Trialist Agent의 표준화 및 CDM 매핑 기능을 구현할 수 있습니다. 초기 데이터 다운로드만 인터넷이 필요하고, 이후에는 모든 처리가 로컬에서 진행됩니다.