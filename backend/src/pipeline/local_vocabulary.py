"""
Local Vocabulary Search using Pandas
Athena Vocabulary CSV 파일들을 로컬에서 검색하는 경량 시스템
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class LocalVocabulary:
    """로컬 Vocabulary CSV 파일을 사용한 검색 시스템"""

    def __init__(self, vocab_dir: str = "vocabulary"):
        """
        Args:
            vocab_dir: Vocabulary CSV 파일들이 있는 디렉토리 경로
        """
        self.vocab_dir = Path(vocab_dir)

        if not self.vocab_dir.exists():
            raise FileNotFoundError(f"Vocabulary directory not found: {self.vocab_dir}")

        # Lazy loading - 실제 사용할 때만 로드
        self._concept = None
        self._concept_relationship = None
        self._concept_ancestor = None
        self._concept_synonym = None
        self._vocabulary = None
        self._domain = None

        logger.info(f"LocalVocabulary initialized with directory: {self.vocab_dir}")

    @property
    def concept(self) -> pd.DataFrame:
        """CONCEPT 테이블 (약 600만 개 개념)"""
        if self._concept is None:
            logger.info("Loading CONCEPT.csv...")
            self._concept = pd.read_csv(
                self.vocab_dir / "CONCEPT.csv",
                sep="\t",
                dtype={
                    "concept_id": int,
                    "concept_name": str,
                    "domain_id": str,
                    "vocabulary_id": str,
                    "concept_class_id": str,
                    "standard_concept": str,
                    "concept_code": str,
                    "valid_start_date": str,
                    "valid_end_date": str,
                    "invalid_reason": str,
                },
                na_values=[""],
                keep_default_na=False
            )
            logger.info(f"Loaded {len(self._concept):,} concepts")
        return self._concept

    @property
    def concept_relationship(self) -> pd.DataFrame:
        """CONCEPT_RELATIONSHIP 테이블 (개념 간 매핑)"""
        if self._concept_relationship is None:
            logger.info("Loading CONCEPT_RELATIONSHIP.csv...")
            self._concept_relationship = pd.read_csv(
                self.vocab_dir / "CONCEPT_RELATIONSHIP.csv",
                sep="\t",
                dtype={
                    "concept_id_1": int,
                    "concept_id_2": int,
                    "relationship_id": str,
                }
            )
            logger.info(f"Loaded {len(self._concept_relationship):,} relationships")
        return self._concept_relationship

    @property
    def concept_ancestor(self) -> pd.DataFrame:
        """CONCEPT_ANCESTOR 테이블 (계층 구조)"""
        if self._concept_ancestor is None:
            logger.info("Loading CONCEPT_ANCESTOR.csv...")
            self._concept_ancestor = pd.read_csv(
                self.vocab_dir / "CONCEPT_ANCESTOR.csv",
                sep="\t",
                dtype={
                    "ancestor_concept_id": int,
                    "descendant_concept_id": int,
                    "min_levels_of_separation": int,
                    "max_levels_of_separation": int,
                }
            )
            logger.info(f"Loaded {len(self._concept_ancestor):,} ancestor relationships")
        return self._concept_ancestor

    @property
    def concept_synonym(self) -> pd.DataFrame:
        """CONCEPT_SYNONYM 테이블 (동의어)"""
        if self._concept_synonym is None:
            logger.info("Loading CONCEPT_SYNONYM.csv...")
            self._concept_synonym = pd.read_csv(
                self.vocab_dir / "CONCEPT_SYNONYM.csv",
                sep="\t",
                dtype={
                    "concept_id": int,
                    "concept_synonym_name": str,
                }
            )
            logger.info(f"Loaded {len(self._concept_synonym):,} synonyms")
        return self._concept_synonym

    def search_concepts(
        self,
        query: str,
        domain: Optional[str] = None,
        vocabulary: Optional[str] = None,
        standard_only: bool = True,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        개념 검색

        Args:
            query: 검색어
            domain: 도메인 필터 (예: "Drug", "Condition")
            vocabulary: Vocabulary 필터 (예: "RxNorm", "SNOMED")
            standard_only: 표준 개념만 반환
            limit: 최대 결과 수

        Returns:
            검색 결과 DataFrame
        """
        concepts = self.concept.copy()

        # 검색어로 필터링 (대소문자 구분 없음)
        query_lower = query.lower()
        mask = concepts["concept_name"].str.lower().str.contains(query_lower, na=False)

        # 동의어 검색도 포함
        synonym_concepts = self.concept_synonym[
            self.concept_synonym["concept_synonym_name"].str.lower().str.contains(query_lower, na=False)
        ]["concept_id"].unique()

        mask = mask | concepts["concept_id"].isin(synonym_concepts)

        concepts = concepts[mask]

        # 표준 개념 필터
        if standard_only:
            concepts = concepts[concepts["standard_concept"] == "S"]

        # 도메인 필터
        if domain:
            concepts = concepts[concepts["domain_id"] == domain]

        # Vocabulary 필터
        if vocabulary:
            concepts = concepts[concepts["vocabulary_id"] == vocabulary]

        # 정렬 및 제한
        concepts = concepts.head(limit)

        return concepts

    def get_concept_by_id(self, concept_id: int) -> Optional[Dict]:
        """개념 ID로 조회"""
        result = self.concept[self.concept["concept_id"] == concept_id]
        if len(result) == 0:
            return None
        return result.iloc[0].to_dict()

    def get_concept_mappings(
        self,
        concept_id: int,
        relationship_id: str = "Maps to"
    ) -> pd.DataFrame:
        """
        개념 매핑 조회 (소스 → 표준)

        Args:
            concept_id: 소스 개념 ID
            relationship_id: 관계 타입 (기본: "Maps to")

        Returns:
            매핑된 표준 개념들
        """
        # 관계 조회
        mappings = self.concept_relationship[
            (self.concept_relationship["concept_id_1"] == concept_id) &
            (self.concept_relationship["relationship_id"] == relationship_id)
        ]

        # 표준 개념 정보 가져오기
        target_ids = mappings["concept_id_2"].tolist()
        target_concepts = self.concept[self.concept["concept_id"].isin(target_ids)]

        return target_concepts

    def get_concept_ancestors(
        self,
        concept_id: int,
        max_levels: Optional[int] = None
    ) -> pd.DataFrame:
        """
        개념의 상위 계층 조회

        Args:
            concept_id: 개념 ID
            max_levels: 최대 계층 깊이

        Returns:
            상위 개념들
        """
        ancestors = self.concept_ancestor[
            self.concept_ancestor["descendant_concept_id"] == concept_id
        ]

        if max_levels is not None:
            ancestors = ancestors[
                ancestors["min_levels_of_separation"] <= max_levels
            ]

        # 상위 개념 정보 가져오기
        ancestor_ids = ancestors["ancestor_concept_id"].tolist()
        ancestor_concepts = self.concept[self.concept["concept_id"].isin(ancestor_ids)]

        # 계층 정보 추가
        result = ancestor_concepts.merge(
            ancestors[["ancestor_concept_id", "min_levels_of_separation"]],
            left_on="concept_id",
            right_on="ancestor_concept_id",
            how="left"
        )

        return result.sort_values("min_levels_of_separation")

    def get_concept_descendants(
        self,
        concept_id: int,
        max_levels: Optional[int] = None
    ) -> pd.DataFrame:
        """
        개념의 하위 계층 조회

        Args:
            concept_id: 개념 ID
            max_levels: 최대 계층 깊이

        Returns:
            하위 개념들
        """
        descendants = self.concept_ancestor[
            self.concept_ancestor["ancestor_concept_id"] == concept_id
        ]

        if max_levels is not None:
            descendants = descendants[
                descendants["min_levels_of_separation"] <= max_levels
            ]

        # 하위 개념 정보 가져오기
        descendant_ids = descendants["descendant_concept_id"].tolist()
        descendant_concepts = self.concept[self.concept["concept_id"].isin(descendant_ids)]

        # 계층 정보 추가
        result = descendant_concepts.merge(
            descendants[["descendant_concept_id", "min_levels_of_separation"]],
            left_on="concept_id",
            right_on="descendant_concept_id",
            how="left"
        )

        return result.sort_values("min_levels_of_separation")

    def search_and_map(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        검색 후 표준 개념으로 매핑 (원스톱)

        Args:
            query: 검색어
            domain: 도메인 필터
            limit: 최대 결과 수

        Returns:
            표준 개념 리스트
        """
        # 먼저 비표준 개념 포함하여 검색
        results = self.search_concepts(
            query=query,
            domain=domain,
            standard_only=False,
            limit=limit * 2  # 매핑 후 limit에 맞추기 위해 더 많이 검색
        )

        standard_concepts = []
        seen_ids = set()

        for _, concept in results.iterrows():
            concept_id = concept["concept_id"]

            # 이미 표준 개념이면 바로 추가
            if concept["standard_concept"] == "S":
                if concept_id not in seen_ids:
                    standard_concepts.append(concept.to_dict())
                    seen_ids.add(concept_id)
            else:
                # 표준 개념으로 매핑
                mappings = self.get_concept_mappings(concept_id)
                for _, mapped in mappings.iterrows():
                    mapped_id = mapped["concept_id"]
                    if mapped_id not in seen_ids:
                        standard_concepts.append(mapped.to_dict())
                        seen_ids.add(mapped_id)

            if len(standard_concepts) >= limit:
                break

        return standard_concepts[:limit]


# Singleton 인스턴스
_vocab_instance: Optional[LocalVocabulary] = None


def get_vocabulary(vocab_dir: str = "vocabulary") -> LocalVocabulary:
    """Vocabulary 싱글톤 인스턴스 가져오기"""
    global _vocab_instance
    if _vocab_instance is None:
        _vocab_instance = LocalVocabulary(vocab_dir)
    return _vocab_instance
