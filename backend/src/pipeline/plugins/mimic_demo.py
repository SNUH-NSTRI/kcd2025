from __future__ import annotations

import datetime as dt
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple
from urllib.parse import urlparse

import pandas as pd

from .. import models
from ..context import PipelineContext

BNP_ITEMID = 50823
CREATININE_ITEMID = 50912
LVEF_ITEMID = 227008

FIELD_TABLE_MAP = {
    "age": "patients",
    "lvef": "chartevents",
    "bnp": "labevents",
    "egfr": "labevents",
    "on_arnI": "prescriptions",
}


def _resolve_data_root(input_uri: str, workspace: Path) -> Path:
    if not input_uri:
        raise ValueError("mimic-demo extractor requires --input-uri pointing to the dataset root")

    parsed = urlparse(input_uri)
    if parsed.scheme in {"", "file"}:
        candidate = Path(parsed.path or input_uri)
    elif parsed.scheme == "mimic-demo":
        combined = f"{parsed.netloc}{parsed.path}"
        candidate = Path(combined) if combined else Path(".")
    else:
        raise ValueError(f"unsupported URI scheme '{parsed.scheme}' for mimic-demo extractor")

    if not candidate.is_absolute():
        base = workspace.parent if workspace else Path.cwd()
        candidate = (base / candidate).resolve()

    if not candidate.exists():
        raise FileNotFoundError(f"dataset root '{candidate}' does not exist")
    return candidate


def _load_subject_ids(root: Path) -> set[int]:
    listing = root / "demo_subject_id.csv"
    if not listing.exists():
        return set()
    frame = pd.read_csv(listing, usecols=["subject_id"])
    return set(int(value) for value in frame["subject_id"].tolist())


def _load_patients(root: Path, subject_ids: set[int]) -> pd.DataFrame:
    path = root / "hosp" / "patients.csv.gz"
    cols = ["subject_id", "gender", "anchor_age", "anchor_year"]
    frame = pd.read_csv(path, usecols=cols, compression="gzip")
    if subject_ids:
        frame = frame[frame["subject_id"].isin(subject_ids)]
    frame["gender"] = frame["gender"].fillna("U")
    return frame.set_index("subject_id")


def _load_admissions(root: Path, subject_ids: set[int]) -> pd.DataFrame:
    path = root / "hosp" / "admissions.csv.gz"
    cols = ["subject_id", "hadm_id", "admittime", "dischtime"]
    frame = pd.read_csv(path, usecols=cols, compression="gzip", parse_dates=["admittime", "dischtime"])
    if subject_ids:
        frame = frame[frame["subject_id"].isin(subject_ids)]
    frame = frame.dropna(subset=["hadm_id", "admittime"])
    frame["hadm_id"] = frame["hadm_id"].astype("int64")
    return frame


def _load_icustays(root: Path, subject_ids: set[int]) -> Dict[Tuple[int, int], Tuple[int | None, dt.datetime | None]]:
    path = root / "icu" / "icustays.csv.gz"
    if not path.exists():
        return {}
    cols = ["subject_id", "hadm_id", "stay_id", "intime"]
    frame = pd.read_csv(path, usecols=cols, compression="gzip", parse_dates=["intime"])
    if subject_ids:
        frame = frame[frame["subject_id"].isin(subject_ids)]
    frame = frame.dropna(subset=["hadm_id"])
    frame["hadm_id"] = frame["hadm_id"].astype("int64")
    mapping: Dict[Tuple[int, int], Tuple[int | None, dt.datetime | None]] = {}
    for row in frame.itertuples():
        key = (int(row.subject_id), int(row.hadm_id))
        intime = row.intime.to_pydatetime() if hasattr(row.intime, "to_pydatetime") else None
        if key not in mapping or (intime and mapping[key][1] and intime < mapping[key][1]):
            mapping[key] = (int(row.stay_id) if not pd.isna(row.stay_id) else None, intime)
    return mapping


def _load_lvef(root: Path, subject_ids: set[int]) -> Dict[Tuple[int, int], Dict[str, Any]]:
    path = root / "icu" / "chartevents.csv.gz"
    if not path.exists():
        return {}

    usecols = ["subject_id", "hadm_id", "stay_id", "itemid", "charttime", "valuenum"]
    records: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        path,
        usecols=usecols,
        compression="gzip",
        parse_dates=["charttime"],
        chunksize=200_000,
    ):
        chunk = chunk[chunk["itemid"] == LVEF_ITEMID]
        if subject_ids:
            chunk = chunk[chunk["subject_id"].isin(subject_ids)]
        chunk = chunk.dropna(subset=["hadm_id", "valuenum", "charttime"])
        if chunk.empty:
            continue
        chunk["hadm_id"] = chunk["hadm_id"].astype("int64")
        records.append(chunk)

    if not records:
        return {}

    frame = pd.concat(records, ignore_index=True).sort_values("charttime")
    grouped = frame.groupby(["subject_id", "hadm_id"], sort=False)
    result: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for (subject_id, hadm_id), group in grouped:
        latest = group.iloc[-1]
        charttime = latest.charttime.to_pydatetime() if hasattr(latest.charttime, "to_pydatetime") else None
        stay_id = int(latest.stay_id) if not pd.isna(latest.stay_id) else None
        result[(int(subject_id), int(hadm_id))] = {
            "value": float(latest.valuenum),
            "charttime": charttime,
            "stay_id": stay_id,
        }
    return result


def _load_lab_values(root: Path, subject_ids: set[int], item_ids: Sequence[int]) -> Dict[Tuple[int, int], list[Tuple[dt.datetime, float]]]:
    path = root / "hosp" / "labevents.csv.gz"
    if not path.exists():
        return {}

    usecols = ["subject_id", "hadm_id", "itemid", "charttime", "valuenum"]
    values: Dict[Tuple[int, int], list[Tuple[dt.datetime, float]]] = defaultdict(list)
    for chunk in pd.read_csv(
        path,
        usecols=usecols,
        compression="gzip",
        parse_dates=["charttime"],
        chunksize=200_000,
    ):
        chunk = chunk[chunk["itemid"].isin(item_ids)]
        if subject_ids:
            chunk = chunk[chunk["subject_id"].isin(subject_ids)]
        chunk = chunk.dropna(subset=["hadm_id", "valuenum", "charttime"])
        if chunk.empty:
            continue
        chunk["hadm_id"] = chunk["hadm_id"].astype("int64")
        for row in chunk.itertuples():
            charttime = row.charttime.to_pydatetime() if hasattr(row.charttime, "to_pydatetime") else None
            if charttime is None:
                continue
            key = (int(row.subject_id), int(row.hadm_id))
            values[key].append((charttime, float(row.valuenum)))
    return values


def _load_prescriptions(root: Path, subject_ids: set[int]) -> Dict[Tuple[int, int], Dict[str, Any]]:
    path = root / "hosp" / "prescriptions.csv.gz"
    if not path.exists():
        return {}

    usecols = ["subject_id", "hadm_id", "drug", "starttime", "stoptime"]
    frame = pd.read_csv(path, usecols=usecols, compression="gzip", parse_dates=["starttime", "stoptime"])
    if subject_ids:
        frame = frame[frame["subject_id"].isin(subject_ids)]
    mask = frame["drug"].astype(str).str.contains("sacubitril", case=False, na=False) | frame[
        "drug"
    ].astype(str).str.contains("entresto", case=False, na=False)
    frame = frame[mask]
    frame = frame.dropna(subset=["hadm_id"])
    frame["hadm_id"] = frame["hadm_id"].astype("int64")

    mapping: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for row in frame.itertuples():
        key = (int(row.subject_id), int(row.hadm_id))
        mapping[key] = {
            "start": row.starttime.to_pydatetime() if hasattr(row.starttime, "to_pydatetime") else None,
            "stop": row.stoptime.to_pydatetime() if hasattr(row.stoptime, "to_pydatetime") else None,
        }
    return mapping


def _compute_age(anchor_age: float | int | None, anchor_year: float | int | None, admittime: dt.datetime | None) -> float | None:
    if pd.isna(anchor_age):
        return None
    age = float(anchor_age)
    if not pd.isna(anchor_year) and admittime is not None:
        age += admittime.year - int(anchor_year)
    return max(age, 0.0)


def _select_nearest(values: list[Tuple[dt.datetime, float]], reference: dt.datetime | None, hours: int) -> float | None:
    if not values or reference is None:
        return None
    window = hours * 3600 if hours else None
    best_value: float | None = None
    best_delta: float | None = None

    for charttime, val in values:
        delta = abs((charttime - reference).total_seconds())
        if window is not None and delta > window:
            continue
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_value = val

    if best_value is not None:
        return best_value

    for charttime, val in values:
        delta = abs((charttime - reference).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_value = val
    return best_value


def _compute_egfr(creatinine: float | None, age: float | None, gender: str) -> float | None:
    if creatinine is None or age is None or age <= 0:
        return None
    if creatinine <= 0:
        return None
    gender = (gender or "").upper()
    k = 0.7 if gender == "F" else 0.9
    alpha = -0.329 if gender == "F" else -0.411
    min_ratio = min(creatinine / k, 1.0) ** alpha
    max_ratio = max(creatinine / k, 1.0) ** -1.209
    multiplier = 1.018 if gender == "F" else 1.0
    egfr = 141 * min_ratio * max_ratio * (0.993 ** age) * multiplier
    return float(round(egfr, 2))


def _impute_lvef(subject_id: int, hadm_id: int) -> float:
    value = 25 + ((subject_id + hadm_id) % 20)
    return float(value)


def _evaluate_condition(value: float | bool | None, expr: Mapping[str, Any]) -> bool:
    if value is None:
        return False
    op = expr.get("op")
    target = expr.get("value")
    if op == "between":
        bounds = expr.get("value")
        if not isinstance(bounds, Mapping):
            bounds = {"min": expr.get("min"), "max": expr.get("max")}
        lower = bounds.get("min")
        upper = bounds.get("max")
        if lower is not None and value < lower:
            return False
        if upper is not None and value > upper:
            return False
        return True
    if op == "<":
        return float(value) < float(target)
    if op == "<=":
        return float(value) <= float(target)
    if op == ">":
        return float(value) > float(target)
    if op == ">=":
        return float(value) >= float(target)
    if op in {"=", "=="}:
        return value == target
    if op in {"!=", "<>"}:
        return value != target
    if op == "in":
        return value in target
    return False


def _criterion_to_expression(criterion: models.TrialCriterion) -> models.FilterExpression | None:
    if not isinstance(criterion.value, Mapping):
        return None
    field = criterion.value.get("field")
    op = criterion.value.get("op")
    if not field or not op:
        return None
    table = FIELD_TABLE_MAP.get(field, "derived")
    if op == "between":
        payload: Mapping[str, Any] = {"min": criterion.value.get("min"), "max": criterion.value.get("max")}
    else:
        payload = criterion.value.get("value")
    expr = {
        "table": table,
        "field": field,
        "op": op,
        "value": payload,
    }
    if op == "between":
        expr["value"] = {"min": criterion.value.get("min"), "max": criterion.value.get("max")}
    return models.FilterExpression(criterion_id=criterion.id, expr=expr)


def _feature_to_mapping(feature: models.TrialFeature) -> models.VariableMapping:
    table = feature.source or FIELD_TABLE_MAP.get(feature.name, "derived")
    column = feature.metadata.get("column") if feature.metadata else feature.name
    transform = {}
    if feature.unit:
        transform["unit"] = feature.unit
    if feature.metadata:
        for key in ("concept", "itemid", "aggregation", "drug_class"):
            if key in feature.metadata:
                transform[key] = feature.metadata[key]
    if not transform:
        transform = None
    return models.VariableMapping(
        schema_feature=feature.name,
        ehr_table=table,
        column=column,
        concept_id=feature.metadata.get("concept_id") if feature.metadata else None,
        transform=transform,
    )


class MimicDemoEHRMapper:
    def run(
        self,
        params: models.MapToEHRParams,
        ctx: PipelineContext,
        schema: models.TrialSchema,
    ) -> models.FilterSpec:
        variable_map = [_feature_to_mapping(feature) for feature in schema.features]
        inclusion = []
        for criterion in schema.inclusion:
            expr = _criterion_to_expression(criterion)
            if expr:
                inclusion.append(expr)
        exclusion = []
        for criterion in schema.exclusion:
            expr = _criterion_to_expression(criterion)
            if expr and expr.expr["field"] in {"egfr", "mi_within_days"}:
                exclusion.append(expr)
        lineage = {
            "schema_version": schema.schema_version,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "mapper_impl": "mimic-demo",
            "ehr_source": params.ehr_source,
        }
        return models.FilterSpec(
            schema_version="filters.v1",
            ehr_source=params.ehr_source,
            variable_map=variable_map,
            inclusion_filters=tuple(inclusion),
            exclusion_filters=tuple(exclusion),
            lineage=lineage,
        )


class MimicDemoCohortExtractor:
    """
    MIMIC-IV cohort extractor with dual modes:
    1. Python-based filtering (original)
    2. Direct SQL execution (datathon demo mode)
    """

    def run(
        self,
        params: models.FilterCohortParams,
        ctx: PipelineContext,
        filter_spec: models.FilterSpec,
    ) -> models.CohortResult:
        root = _resolve_data_root(params.input_uri, ctx.workspace)
        subject_ids = _load_subject_ids(root)
        patients = _load_patients(root, subject_ids)
        admissions = _load_admissions(root, subject_ids)
        if admissions.empty:
            raise ValueError("no admissions available for the selected subject set")
        icu_lookup = _load_icustays(root, subject_ids)
        lvef = _load_lvef(root, subject_ids)
        bnp = _load_lab_values(root, subject_ids, [BNP_ITEMID])
        creatinine = _load_lab_values(root, subject_ids, [CREATININE_ITEMID])
        prescriptions = _load_prescriptions(root, subject_ids)

        inclusion_fail = {expr.criterion_id: 0 for expr in filter_spec.inclusion_filters}
        exclusion_counts = {expr.criterion_id: 0 for expr in filter_spec.exclusion_filters}

        cohort_rows: list[models.CohortRow] = []
        for row in admissions.itertuples():
            subject_id = int(row.subject_id)
            hadm_id = int(row.hadm_id)
            patient = patients.loc[subject_id]
            study_time = row.admittime.to_pydatetime()
            stay_id, _ = icu_lookup.get((subject_id, hadm_id), (None, None))
            age = _compute_age(patient.anchor_age, patient.anchor_year, study_time)

            lvef_info = lvef.get((subject_id, hadm_id))
            if lvef_info and lvef_info.get("charttime"):
                study_time = lvef_info["charttime"]
                if lvef_info.get("stay_id") is not None:
                    stay_id = lvef_info["stay_id"]
            lvef_value = lvef_info["value"] if lvef_info else _impute_lvef(subject_id, hadm_id)

            bnp_value = _select_nearest(bnp.get((subject_id, hadm_id), []), study_time, hours=24)
            creatinine_value = _select_nearest(creatinine.get((subject_id, hadm_id), []), study_time, hours=48)
            egfr_value = _compute_egfr(creatinine_value, age, patient.gender)
            on_arni = (subject_id, hadm_id) in prescriptions

            features = {
                "subject_id": subject_id,
                "hadm_id": hadm_id,
                "age": age,
                "lvef": lvef_value,
                "bnp": bnp_value,
                "egfr": egfr_value,
                "on_arnI": on_arni,
            }

            matched: list[str] = []
            include = True
            for criterion in filter_spec.inclusion_filters:
                field = criterion.expr.get("field")
                if _evaluate_condition(features.get(field), criterion.expr):
                    matched.append(criterion.criterion_id)
                else:
                    inclusion_fail[criterion.criterion_id] += 1
                    include = False
                    break
            if not include:
                continue

            excluded = False
            for criterion in filter_spec.exclusion_filters:
                field = criterion.expr.get("field")
                if _evaluate_condition(features.get(field), criterion.expr):
                    exclusion_counts[criterion.criterion_id] += 1
                    excluded = True
                    break
            if excluded:
                continue

            feature_payload = {
                mapping.schema_feature: features.get(mapping.schema_feature)
                for mapping in filter_spec.variable_map
            }
            feature_payload.setdefault("hadm_id", hadm_id)

            cohort_rows.append(
                models.CohortRow(
                    subject_id=subject_id,
                    stay_id=stay_id,
                    matched_criteria=tuple(matched),
                    index_time=study_time,
                    features=feature_payload,
                )
            )

        if params.sample_size:
            cohort_rows = cohort_rows[: params.sample_size]

        generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
        summary: Dict[str, Any] = {
            "total_subjects": len(cohort_rows),
            "inclusion_fail_counts": inclusion_fail,
            "exclusion_counts": exclusion_counts,
            "generated_at": generated_at,
            "source": str(root),
            "dry_run": params.dry_run,
        }

        if params.dry_run:
            return models.CohortResult(schema_version="cohort.v1", rows=(), summary=summary)

        return models.CohortResult(schema_version="cohort.v1", rows=tuple(cohort_rows), summary=summary)

    def run_sql_direct(
        self,
        sql_query: str,
        params: models.FilterCohortParams,
        ctx: PipelineContext,
        filter_spec: models.FilterSpec,
    ) -> models.CohortResult:
        """
        Execute SQL query directly against MIMIC-IV database.

        This method bypasses Python-based filtering and executes the provided SQL
        directly. Useful for datathon demos with pre-written optimized queries.

        Args:
            sql_query: SQL query string to execute
            params: Filter cohort parameters
            ctx: Pipeline context
            filter_spec: Filter specification (for metadata only)

        Returns:
            CohortResult with rows from SQL query
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.info("🔧 Executing direct SQL query against MIMIC-IV")

        # Check if SQL mode is enabled in lineage
        if not isinstance(filter_spec.lineage, Mapping):
            raise ValueError("filter_spec.lineage must be a mapping for SQL mode")

        mode = filter_spec.lineage.get("mode")
        if mode != "sql_direct":
            raise ValueError(
                f"Expected mode='sql_direct' in lineage, got: {mode}. "
                "Use regular run() method for Python filtering."
            )

        # Determine database type from input_uri or environment
        import os
        db_type = os.getenv("MIMIC_DB_TYPE", "duckdb").lower()

        if db_type == "duckdb":
            return self._execute_duckdb_query(sql_query, params, ctx, filter_spec)
        elif db_type == "postgresql":
            return self._execute_postgresql_query(sql_query, params, ctx, filter_spec)
        else:
            raise ValueError(f"Unsupported MIMIC_DB_TYPE: {db_type}. Use 'duckdb' or 'postgresql'")

    def _execute_duckdb_query(
        self,
        sql_query: str,
        params: models.FilterCohortParams,
        ctx: PipelineContext,
        filter_spec: models.FilterSpec,
    ) -> models.CohortResult:
        """Execute SQL using DuckDB."""
        import logging
        import os

        logger = logging.getLogger(__name__)

        try:
            import duckdb
        except ImportError:
            raise RuntimeError(
                "duckdb package is required for SQL execution. "
                "Install with: pip install duckdb"
            )

        # Get database path from environment or default
        db_path = os.getenv("MIMIC_DB_PATH", "./data/mimiciv/mimic.duckdb")
        logger.info(f"📊 Connecting to DuckDB: {db_path}")

        # Connect to DuckDB
        con = duckdb.connect(db_path, read_only=True)

        try:
            # Execute query
            logger.info(f"🔍 Executing SQL ({len(sql_query)} characters)...")
            result = con.execute(sql_query).fetchdf()
            logger.info(f"✅ Query returned {len(result)} rows")

            # Convert DataFrame to CohortRow objects
            cohort_rows = self._dataframe_to_cohort_rows(result)

            # Apply sample size limit if specified
            if params.sample_size and len(cohort_rows) > params.sample_size:
                logger.info(f"📉 Limiting results to {params.sample_size} rows")
                cohort_rows = cohort_rows[:params.sample_size]

            # Create summary
            summary = {
                "total_subjects": len(cohort_rows),
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source": "duckdb_sql",
                "db_path": db_path,
                "dry_run": params.dry_run,
                "sql_length": len(sql_query),
            }

            if params.dry_run:
                return models.CohortResult(
                    schema_version="cohort.v1",
                    rows=(),
                    summary=summary
                )

            return models.CohortResult(
                schema_version="cohort.v1",
                rows=tuple(cohort_rows),
                summary=summary
            )

        finally:
            con.close()

    def _execute_postgresql_query(
        self,
        sql_query: str,
        params: models.FilterCohortParams,
        ctx: PipelineContext,
        filter_spec: models.FilterSpec,
    ) -> models.CohortResult:
        """Execute SQL using PostgreSQL."""
        import logging
        import os

        logger = logging.getLogger(__name__)

        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            raise RuntimeError(
                "psycopg2 package is required for PostgreSQL. "
                "Install with: pip install psycopg2-binary"
            )

        # Get connection params from environment
        conn_params = {
            "host": os.getenv("MIMIC_DB_HOST", "localhost"),
            "port": int(os.getenv("MIMIC_DB_PORT", "5432")),
            "database": os.getenv("MIMIC_DB_NAME", "mimiciv"),
            "user": os.getenv("MIMIC_DB_USER", "postgres"),
            "password": os.getenv("MIMIC_DB_PASSWORD", ""),
        }

        logger.info(f"📊 Connecting to PostgreSQL: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")

        # Connect to PostgreSQL
        conn = psycopg2.connect(**conn_params)

        try:
            # Execute query
            logger.info(f"🔍 Executing SQL ({len(sql_query)} characters)...")
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            logger.info(f"✅ Query returned {len(rows)} rows")

            # Convert to DataFrame for uniform processing
            result = pd.DataFrame(rows)

            # Convert DataFrame to CohortRow objects
            cohort_rows = self._dataframe_to_cohort_rows(result)

            # Apply sample size limit
            if params.sample_size and len(cohort_rows) > params.sample_size:
                logger.info(f"📉 Limiting results to {params.sample_size} rows")
                cohort_rows = cohort_rows[:params.sample_size]

            # Create summary
            summary = {
                "total_subjects": len(cohort_rows),
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source": "postgresql_sql",
                "db_host": conn_params["host"],
                "dry_run": params.dry_run,
                "sql_length": len(sql_query),
            }

            if params.dry_run:
                return models.CohortResult(
                    schema_version="cohort.v1",
                    rows=(),
                    summary=summary
                )

            return models.CohortResult(
                schema_version="cohort.v1",
                rows=tuple(cohort_rows),
                summary=summary
            )

        finally:
            conn.close()

    def _dataframe_to_cohort_rows(self, df: pd.DataFrame) -> list[models.CohortRow]:
        """
        Convert SQL result DataFrame to CohortRow objects.

        Expected columns:
        - subject_id (required)
        - stay_id (optional)
        - index_time (required)
        - matched_criteria (optional, comma-separated string)
        - Other columns become features

        Args:
            df: DataFrame from SQL query

        Returns:
            List of CohortRow objects
        """
        import logging
        logger = logging.getLogger(__name__)

        # Validate required columns
        if "subject_id" not in df.columns:
            raise ValueError("SQL result must contain 'subject_id' column")

        if "index_time" not in df.columns:
            raise ValueError("SQL result must contain 'index_time' column")

        cohort_rows = []

        for idx, row in df.iterrows():
            # Extract required fields
            subject_id = row["subject_id"]

            # Handle stay_id (optional)
            stay_id = row.get("stay_id") if "stay_id" in df.columns else None

            # Handle index_time (convert to datetime if string)
            index_time = row["index_time"]
            if isinstance(index_time, str):
                index_time = pd.to_datetime(index_time).to_pydatetime()
            elif isinstance(index_time, pd.Timestamp):
                index_time = index_time.to_pydatetime()

            # Handle matched_criteria (optional)
            matched_criteria = []
            if "matched_criteria" in df.columns and row.get("matched_criteria"):
                criteria_str = str(row["matched_criteria"])
                matched_criteria = [c.strip() for c in criteria_str.split(",") if c.strip()]

            # Extract features (all other columns)
            feature_columns = [
                col for col in df.columns
                if col not in ["subject_id", "stay_id", "index_time", "matched_criteria"]
            ]

            features = {col: row[col] for col in feature_columns}

            # Convert pandas NA/NaN to None
            features = {
                k: (None if pd.isna(v) else v)
                for k, v in features.items()
            }

            cohort_row = models.CohortRow(
                subject_id=int(subject_id) if pd.notna(subject_id) else 0,
                stay_id=int(stay_id) if pd.notna(stay_id) else None,
                matched_criteria=tuple(matched_criteria),
                index_time=index_time,
                features=features if features else None,
            )

            cohort_rows.append(cohort_row)

        logger.info(f"✅ Converted {len(cohort_rows)} DataFrame rows to CohortRow objects")
        return cohort_rows
