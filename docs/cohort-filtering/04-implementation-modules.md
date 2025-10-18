# 모듈별 구현 계획

## Module 1: CriterionTranslator

**파일**: `src/pipeline/criterion_translator.py`

### 책임
Trial Criterion을 Pandas 필터 조건으로 변환

### 클래스 구조
```python
class CriterionTranslator:
    """Criterion → FilterCondition 변환기"""

    def __init__(self, vocab_adapter: VocabularyAdapter):
        self.vocab = vocab_adapter

    def translate(
        self,
        criterion: EnhancedTrialCriterion
    ) -> FilterCondition:
        """
        Main translation method

        Args:
            criterion: Enhanced trial criterion from Trialist parser

        Returns:
            FilterCondition ready for Pandas filtering
        """
        # 1. Extract domain from entities
        domain = self._determine_domain(criterion.entities)

        # 2. Extract OMOP concept IDs
        concept_ids = self.extract_concept_ids(criterion.entities)

        # 3. Parse temporal constraint (if exists)
        temporal = self._extract_temporal(criterion.entities)

        # 4. Parse value constraint (if exists)
        value = self._extract_value(criterion.entities)

        return FilterCondition(
            domain=domain,
            concept_ids=concept_ids,
            temporal=temporal,
            value=value
        )

    def extract_concept_ids(
        self,
        entities: List[EnhancedNamedEntity]
    ) -> List[int]:
        """
        Extract OMOP concept IDs from entities

        Prioritizes:
        1. entity.omop_concept_id (from CDMMapper)
        2. entity.code_set (multiple codes)
        3. entity.primary_code (fallback)
        """
        concept_ids = []
        for entity in entities:
            if entity.type == "concept":
                if hasattr(entity, 'omop_concept_id') and entity.omop_concept_id:
                    concept_ids.append(entity.omop_concept_id)
                elif entity.code_set:
                    concept_ids.extend(entity.code_set)
                elif entity.primary_code:
                    # Resolve primary_code to concept_id via vocabulary
                    resolved = self.vocab.lookup_code(
                        entity.code_system,
                        entity.primary_code
                    )
                    if resolved:
                        concept_ids.append(resolved.concept_id)
        return list(set(concept_ids))  # Unique

    def _extract_temporal(
        self,
        entities: List[EnhancedNamedEntity]
    ) -> Optional[TemporalCondition]:
        """Extract temporal constraint from entities"""
        for entity in entities:
            if entity.type == "temporal":
                return TemporalCondition(
                    pattern=entity.temporal_pattern or "XBeforeY",
                    anchor_event=entity.reference_point or "enrollment",
                    window=self._parse_iso_duration(entity.iso_duration or "P0D"),
                    direction=self._infer_direction(entity.temporal_pattern)
                )
        return None

    def _extract_value(
        self,
        entities: List[EnhancedNamedEntity]
    ) -> Optional[ValueCondition]:
        """Extract value constraint from entities"""
        for entity in entities:
            if entity.type == "value" or (entity.operator and entity.numeric_value):
                value = entity.numeric_value if entity.operator != "between" else entity.value_range
                return ValueCondition(
                    operator=entity.operator,
                    value=value,
                    unit=entity.unit or ""
                )
        return None

    def _parse_iso_duration(self, iso: str) -> pd.Timedelta:
        """Convert ISO 8601 duration to pd.Timedelta"""
        # P3M → 3 months → 90 days
        # P1Y → 1 year → 365 days
        # PT24H → 24 hours
        # Implementation in temporal_filter.py
        pass

    def _determine_domain(self, entities: List[EnhancedNamedEntity]) -> str:
        """Determine primary domain from entities"""
        for entity in entities:
            if entity.type == "concept":
                return entity.domain
        return "Unknown"

    def _infer_direction(self, pattern: Optional[str]) -> str:
        """Infer temporal direction from pattern"""
        if not pattern:
            return "before"
        if "Before" in pattern:
            return "before"
        elif "After" in pattern:
            return "after"
        elif "During" in pattern:
            return "during"
        return "before"
```

### 테스트 케이스
```python
def test_simple_condition():
    """Test: Age >= 18 years"""
    criterion = create_test_criterion(
        text="Age >= 18 years",
        domain="Measurement",
        concept_id=3004,
        operator=">=",
        value=18
    )

    translator = CriterionTranslator(vocab_adapter)
    condition = translator.translate(criterion)

    assert condition.domain == "Measurement"
    assert 3004 in condition.concept_ids
    assert condition.value.operator == ">="
    assert condition.value.value == 18

def test_temporal_condition():
    """Test: TBI within 3 months before ICU"""
    criterion = create_test_criterion(
        text="TBI within 3 months before ICU admission",
        domain="Condition",
        concept_ids=[12345, 67890],
        temporal_pattern="XBeforeYwithTime",
        iso_duration="P3M",
        anchor="icu_admission"
    )

    translator = CriterionTranslator(vocab_adapter)
    condition = translator.translate(criterion)

    assert condition.domain == "Condition"
    assert set(condition.concept_ids) == {12345, 67890}
    assert condition.temporal.pattern == "XBeforeYwithTime"
    assert condition.temporal.window == pd.Timedelta(days=90)
```

---

## Module 2: PandasCohortFilter (Core Engine)

**파일**: `src/pipeline/pandas_cohort_filter.py`

### 책임
Pandas DataFrame 연산으로 코호트 필터링 수행

### 클래스 구조
```python
class PandasCohortFilter:
    """Pandas 기반 코호트 필터링 엔진"""

    def __init__(self, data_root: Path):
        self.data_root = data_root
        self._cache: Dict[str, pd.DataFrame] = {}
        self.temporal_filter = TemporalFilter()
        self.value_filter = ValueFilter()

    # ========== Table Loading ==========
    @lru_cache(maxsize=10)
    def load_table(self, table_name: str) -> pd.DataFrame:
        """
        Load OMOP CDM table with caching

        Supports:
        - Parquet: table_name.parquet
        - CSV: table_name.csv, table_name.csv.gz
        """
        parquet_path = self.data_root / f"{table_name}.parquet"
        if parquet_path.exists():
            return pd.read_parquet(parquet_path)

        csv_path = self.data_root / f"{table_name}.csv.gz"
        if csv_path.exists():
            return pd.read_csv(csv_path, compression='gzip')

        csv_path = self.data_root / f"{table_name}.csv"
        if csv_path.exists():
            return pd.read_csv(csv_path)

        raise FileNotFoundError(f"Table not found: {table_name}")

    # ========== Domain Filters ==========
    def filter_by_condition(
        self,
        condition: FilterCondition,
        cohort: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Filter by Condition domain

        Process:
        1. Load condition_occurrence table
        2. Filter by person_id (early filtering)
        3. Filter by concept_id
        4. Apply temporal constraint (if exists)
        5. Return person_ids that meet criteria
        """
        # 1. Load table
        condition_df = self.load_table("condition_occurrence")

        # 2. Early filtering (only current cohort patients)
        condition_df = condition_df[
            condition_df['person_id'].isin(cohort['person_id'])
        ]

        # 3. Concept ID filtering
        condition_df = condition_df[
            condition_df['condition_concept_id'].isin(condition.concept_ids)
        ]

        # 4. Temporal constraint
        if condition.temporal:
            condition_df = self.temporal_filter.apply_constraint(
                df=condition_df,
                temporal=condition.temporal,
                cohort=cohort,
                date_col='condition_start_date'
            )

        # 5. Extract qualified person_ids
        qualified_persons = condition_df['person_id'].unique()

        # 6. Update cohort
        return cohort[cohort['person_id'].isin(qualified_persons)]

    def filter_by_drug(
        self,
        condition: FilterCondition,
        cohort: pd.DataFrame
    ) -> pd.DataFrame:
        """Filter by Drug domain"""
        drug_df = self.load_table("drug_exposure")
        drug_df = drug_df[drug_df['person_id'].isin(cohort['person_id'])]
        drug_df = drug_df[drug_df['drug_concept_id'].isin(condition.concept_ids)]

        if condition.temporal:
            drug_df = self.temporal_filter.apply_constraint(
                df=drug_df,
                temporal=condition.temporal,
                cohort=cohort,
                date_col='drug_exposure_start_date'
            )

        qualified_persons = drug_df['person_id'].unique()
        return cohort[cohort['person_id'].isin(qualified_persons)]

    def filter_by_measurement(
        self,
        condition: FilterCondition,
        cohort: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Filter by Measurement domain (with value constraints)

        Handles both:
        - Existence: "Has eGFR measurement"
        - Value: "eGFR < 60"
        """
        measurement_df = self.load_table("measurement")
        measurement_df = measurement_df[
            measurement_df['person_id'].isin(cohort['person_id'])
        ]
        measurement_df = measurement_df[
            measurement_df['measurement_concept_id'].isin(condition.concept_ids)
        ]

        # Value constraint
        if condition.value:
            measurement_df = self.value_filter.apply_constraint(
                df=measurement_df,
                value_condition=condition.value,
                value_col='value_as_number'
            )

        # Temporal constraint
        if condition.temporal:
            measurement_df = self.temporal_filter.apply_constraint(
                df=measurement_df,
                temporal=condition.temporal,
                cohort=cohort,
                date_col='measurement_date'
            )

        qualified_persons = measurement_df['person_id'].unique()
        return cohort[cohort['person_id'].isin(qualified_persons)]

    def filter_by_procedure(
        self,
        condition: FilterCondition,
        cohort: pd.DataFrame
    ) -> pd.DataFrame:
        """Filter by Procedure domain"""
        procedure_df = self.load_table("procedure_occurrence")
        procedure_df = procedure_df[
            procedure_df['person_id'].isin(cohort['person_id'])
        ]
        procedure_df = procedure_df[
            procedure_df['procedure_concept_id'].isin(condition.concept_ids)
        ]

        if condition.temporal:
            procedure_df = self.temporal_filter.apply_constraint(
                df=procedure_df,
                temporal=condition.temporal,
                cohort=cohort,
                date_col='procedure_date'
            )

        qualified_persons = procedure_df['person_id'].unique()
        return cohort[cohort['person_id'].isin(qualified_persons)]

    # ========== Inclusion/Exclusion Logic ==========
    def apply_inclusion_criteria(
        self,
        criteria: List[FilterCondition],
        initial_cohort: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Apply inclusion criteria (AND logic)

        Process:
        - Start with initial cohort
        - Apply each criterion sequentially
        - Cohort shrinks with each criterion
        """
        cohort = initial_cohort.copy()

        for i, condition in enumerate(criteria):
            logger.info(f"Applying inclusion criterion {i+1}/{len(criteria)}")
            logger.info(f"  Cohort size before: {len(cohort)}")

            cohort = self._apply_single_criterion(condition, cohort)

            logger.info(f"  Cohort size after: {len(cohort)}")

            if len(cohort) == 0:
                logger.warning("Cohort empty after criterion - stopping")
                break

        return cohort

    def apply_exclusion_criteria(
        self,
        criteria: List[FilterCondition],
        cohort: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Apply exclusion criteria (NOT logic)

        Process:
        - Find patients meeting ANY exclusion criterion
        - Remove them from cohort
        """
        excluded_person_ids = set()

        for i, condition in enumerate(criteria):
            logger.info(f"Applying exclusion criterion {i+1}/{len(criteria)}")

            # Find patients meeting this exclusion criterion
            excluded = self._apply_single_criterion(condition, cohort)
            new_excluded = set(excluded['person_id'])

            logger.info(f"  Patients excluded: {len(new_excluded)}")
            excluded_person_ids.update(new_excluded)

        # Remove all excluded patients
        logger.info(f"Total patients excluded: {len(excluded_person_ids)}")
        return cohort[~cohort['person_id'].isin(excluded_person_ids)]

    def _apply_single_criterion(
        self,
        condition: FilterCondition,
        cohort: pd.DataFrame
    ) -> pd.DataFrame:
        """Route to appropriate domain filter"""
        if condition.domain == "Condition":
            return self.filter_by_condition(condition, cohort)
        elif condition.domain == "Drug":
            return self.filter_by_drug(condition, cohort)
        elif condition.domain == "Measurement":
            return self.filter_by_measurement(condition, cohort)
        elif condition.domain == "Procedure":
            return self.filter_by_procedure(condition, cohort)
        else:
            logger.warning(f"Unknown domain: {condition.domain}")
            return cohort  # No filtering
```

---

## Module 3: TemporalFilter

**파일**: `src/pipeline/temporal_filter.py`

### 구현 상세
```python
class TemporalFilter:
    """시간 제약 처리"""

    def apply_constraint(
        self,
        df: pd.DataFrame,
        temporal: TemporalCondition,
        cohort: pd.DataFrame,
        date_col: str = 'event_date'
    ) -> pd.DataFrame:
        """
        Apply temporal constraint to DataFrame

        Args:
            df: Event DataFrame (condition, drug, etc.)
            temporal: Temporal constraint
            cohort: Cohort DataFrame (for anchor time lookup)
            date_col: Column name for event date

        Returns:
            Filtered DataFrame
        """
        # Get anchor times for each person
        anchor_times = self._get_anchor_times(
            person_ids=df['person_id'].unique(),
            anchor_event=temporal.anchor_event,
            cohort=cohort
        )

        # Apply pattern
        if temporal.pattern == "XBeforeY":
            return self._pattern_XBeforeY(df, anchor_times, date_col)
        elif temporal.pattern == "XBeforeYwithTime":
            return self._pattern_XBeforeYwithTime(
                df, anchor_times, temporal.window, date_col
            )
        elif temporal.pattern == "XAfterY":
            return self._pattern_XAfterY(df, anchor_times, date_col)
        elif temporal.pattern == "XAfterYwithTime":
            return self._pattern_XAfterYwithTime(
                df, anchor_times, temporal.window, date_col
            )
        elif temporal.pattern == "XWithinTime":
            return self._pattern_XWithinTime(
                df, anchor_times, temporal.window, date_col
            )
        else:
            logger.warning(f"Unknown pattern: {temporal.pattern}")
            return df

    def _get_anchor_times(
        self,
        person_ids: np.ndarray,
        anchor_event: str,
        cohort: pd.DataFrame
    ) -> pd.Series:
        """
        Get anchor event times for each person

        Anchor events:
        - "enrollment": cohort_start_date
        - "icu_admission": ICU admission date from visit_occurrence
        - "baseline": Same as enrollment
        - Custom: Look up in cohort DataFrame
        """
        if anchor_event in ["enrollment", "baseline"]:
            return cohort.set_index('person_id')['cohort_start_date']

        elif anchor_event == "icu_admission":
            # Load visit_occurrence and find ICU visits
            visit_df = pd.read_parquet("data/visit_occurrence.parquet")
            icu_visits = visit_df[
                visit_df['visit_concept_id'].isin(ICU_VISIT_CONCEPTS)
            ]
            return icu_visits.groupby('person_id')['visit_start_date'].min()

        else:
            # Try to find in cohort DataFrame
            if anchor_event in cohort.columns:
                return cohort.set_index('person_id')[anchor_event]
            else:
                logger.warning(f"Unknown anchor event: {anchor_event}")
                return cohort.set_index('person_id')['cohort_start_date']

    @staticmethod
    def _pattern_XBeforeY(
        df: pd.DataFrame,
        anchor_times: pd.Series,
        date_col: str
    ) -> pd.DataFrame:
        """X occurs before Y"""
        df = df.copy()
        df['anchor_time'] = df['person_id'].map(anchor_times)
        return df[df[date_col] < df['anchor_time']]

    @staticmethod
    def _pattern_XBeforeYwithTime(
        df: pd.DataFrame,
        anchor_times: pd.Series,
        window: pd.Timedelta,
        date_col: str
    ) -> pd.DataFrame:
        """X occurs within N days before Y"""
        df = df.copy()
        df['anchor_time'] = df['person_id'].map(anchor_times)
        df['window_start'] = df['anchor_time'] - window

        return df[
            (df[date_col] >= df['window_start']) &
            (df[date_col] <= df['anchor_time'])
        ]

    @staticmethod
    def _pattern_XWithinTime(
        df: pd.DataFrame,
        anchor_times: pd.Series,
        window: pd.Timedelta,
        date_col: str
    ) -> pd.DataFrame:
        """X occurs within N days before or after Y"""
        df = df.copy()
        df['anchor_time'] = df['person_id'].map(anchor_times)
        df['time_diff'] = (df[date_col] - df['anchor_time']).abs()

        return df[df['time_diff'] <= window]

    @staticmethod
    def parse_iso_duration(iso: str) -> pd.Timedelta:
        """
        Parse ISO 8601 duration to pandas Timedelta

        Examples:
        - P3M → 90 days (3 months)
        - P1Y → 365 days (1 year)
        - PT24H → 24 hours
        - P7D → 7 days
        """
        if not iso.startswith("P"):
            raise ValueError(f"Invalid ISO duration: {iso}")

        iso = iso[1:]  # Remove 'P'

        # Handle time component (PT24H)
        if "T" in iso:
            date_part, time_part = iso.split("T")
            # Parse time part
            if "H" in time_part:
                hours = int(time_part.replace("H", ""))
                return pd.Timedelta(hours=hours)
            # Add minutes, seconds if needed

        # Handle date component
        if "Y" in iso:
            years = int(iso.replace("Y", ""))
            return pd.Timedelta(days=years * 365)
        elif "M" in iso:
            months = int(iso.replace("M", ""))
            return pd.Timedelta(days=months * 30)
        elif "D" in iso:
            days = int(iso.replace("D", ""))
            return pd.Timedelta(days=days)

        return pd.Timedelta(days=0)
```

---

## Module 4: ValueFilter

**파일**: `src/pipeline/value_filter.py`

### 구현 상세
```python
class ValueFilter:
    """값 비교 조건 처리"""

    def apply_constraint(
        self,
        df: pd.DataFrame,
        value_condition: ValueCondition,
        value_col: str = 'value_as_number'
    ) -> pd.DataFrame:
        """
        Apply value comparison constraint

        Operators: >=, <=, >, <, =, between
        """
        operator = value_condition.operator
        value = value_condition.value

        if operator == ">=":
            return df[df[value_col] >= value]
        elif operator == "<=":
            return df[df[value_col] <= value]
        elif operator == ">":
            return df[df[value_col] > value]
        elif operator == "<":
            return df[df[value_col] < value]
        elif operator == "=":
            return df[df[value_col] == value]
        elif operator == "between":
            min_val, max_val = value
            return df[
                (df[value_col] >= min_val) &
                (df[value_col] <= max_val)
            ]
        else:
            logger.warning(f"Unknown operator: {operator}")
            return df

    def convert_unit(
        self,
        df: pd.DataFrame,
        from_unit: str,
        to_unit: str,
        value_col: str = 'value_as_number'
    ) -> pd.DataFrame:
        """
        Unit conversion (optional future enhancement)

        Examples:
        - kg → lbs: multiply by 2.20462
        - cm → inch: multiply by 0.393701
        - mg/dL → mmol/L (glucose): multiply by 0.0555
        """
        conversion_factors = {
            ("kg", "lbs"): 2.20462,
            ("lbs", "kg"): 0.453592,
            ("cm", "inch"): 0.393701,
            ("inch", "cm"): 2.54,
        }

        key = (from_unit, to_unit)
        if key in conversion_factors:
            df = df.copy()
            df[value_col] = df[value_col] * conversion_factors[key]

        return df
```

---

## Module 5: CohortBuilder

**파일**: `src/pipeline/cohort_builder.py`

### 구현 상세는 [05-examples.md](05-examples.md) 참조

---

**다음 문서**: [05-examples.md](05-examples.md)
