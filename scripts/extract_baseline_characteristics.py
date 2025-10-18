"""
Extract baseline characteristics from MIMIC-IV v3.1 (약물 제외)

Extracts the following feature categories:
- Demographics: age, gender, BMI, race, height, weight
  * Height: 226707 (Inch→cm), 226730 (cm)
  * Weight: 226512 (Admission kg), 224639 (Daily kg)
- Vital Signs: temperature, HR, SBP, DBP, RR, SpO2 (average in first 24h)
  * Temperature: 223761 (°F→°C), 223762 (°C)
- Laboratory: 17 lab values (FIRST value in -6h to +24h window)
  * Time window includes pre-admission labs (standard practice)
  * Excluded: AST, ALT, ALP, GGT, Fibrinogen, Total Protein, Albumin, CRP, Procalcitonin
- Severity Scores: GCS (minimum, 3 components), APACHE II (calculated)
  * GCS: 220739 (Eye) + 223900 (Verbal) + 223901 (Motor)
- Comorbidities: Charlson Index components from ICD-10 codes
- Organ Support: vasopressors (4 types), mechanical ventilation, RRT
  * Vasopressors: 221906 (Norepi), 221749 (Phenyl), 222315 (Vaso), 221289 (Epi)
  * Ventilation: 223848 (Type), 223849 (Mode)

All itemids verified against MIMIC-IV v3.1 d_items.csv

합치기: subject_id, hadm_id 키로 medications와 조인 가능

Usage:
    python scripts/extract_baseline_characteristics.py \
        --mimic-dir mimiciv/3.1 \
        --output outputs/baseline_characteristics.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
import duckdb
import warnings
import sys

warnings.filterwarnings('ignore')

# ✅ Import FEATURE_METADATA from Single Source of Truth
# Add scripts directory to path if needed
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    from feature_types_utils import FEATURE_METADATA
except ImportError:
    print("⚠️ WARNING: feature_types_utils.py not found. Using fallback metadata.")
    # Fallback: minimal metadata if import fails
    FEATURE_METADATA = {}


class BaselineCharacteristicsExtractor:
    """Extract baseline characteristics from MIMIC-IV (excluding medications)

    ICU 환자만 추출: ICU stay가 있는 환자만 포함

    Note: FEATURE_METADATA is imported from feature_types_utils.py (Single Source of Truth)
    """

    # ✅ Use imported FEATURE_METADATA instead of duplicating
    FEATURE_METADATA = FEATURE_METADATA

    def __init__(self, mimic_dir: str = "data/3.1"):
        self.mimic_dir = Path(mimic_dir)
        self.icu_dir = self.mimic_dir / "icu"
        self.hosp_dir = self.mimic_dir / "hosp"
        self.con = duckdb.connect()

        # Load ICU cohort (stay_id, subject_id, hadm_id, intime, outtime)
        print("\n📊 Loading ICU cohort...")
        self.icu_cohort = pd.read_csv(f"{self.icu_dir}/icustays.csv.gz")
        self.icu_subject_ids = set(self.icu_cohort['subject_id'].unique())
        self.icu_hadm_ids = set(self.icu_cohort['hadm_id'].unique())
        print(f"   ✓ ICU patients: {len(self.icu_subject_ids):,}")
        print(f"   ✓ ICU admissions: {len(self.icu_hadm_ids):,}")

    def extract_demographics(self) -> pd.DataFrame:
        """
        Extract demographic variables:
        - Age, Gender, BMI, Race
        """
        print("\n👤 [1/6] Extracting demographics...")

        sql = f"""
        WITH heights AS (
            SELECT
                subject_id,
                MEDIAN(
                    CASE
                        WHEN itemid = 226707 THEN valuenum * 2.54  -- inches to cm
                        WHEN itemid = 226730 THEN valuenum         -- already in cm
                        ELSE NULL
                    END
                ) as height_cm
            FROM read_csv_auto('{self.icu_dir}/chartevents.csv.gz') 
            WHERE (
                (itemid = 226707 AND valuenum BETWEEN 39 AND 98)      -- inches: 39-98 inch
                OR (itemid = 226730 AND valuenum BETWEEN 100 AND 250) -- cm: 100-250cm
            )
            GROUP BY subject_id
        ),
        weights AS (
            SELECT
                icu.subject_id,
                icu.stay_id,
                FIRST(c.valuenum ORDER BY c.charttime) as weight_kg  -- Both are in kg
            FROM read_csv_auto('{self.icu_dir}/icustays.csv.gz') icu
            LEFT JOIN read_csv_auto('{self.icu_dir}/chartevents.csv.gz') c
                ON icu.stay_id = c.stay_id
            WHERE c.itemid IN (226512, 224639)  -- Admission Weight (kg), Daily Weight (kg)
                AND c.valuenum BETWEEN 30 AND 300  -- reasonable range in kg
            GROUP BY icu.subject_id, icu.stay_id
        )
        SELECT
            p.subject_id,
            p.gender,
            p.anchor_age,
            p.anchor_year,
            COALESCE(h.height_cm, NULL) as height_cm,
            COALESCE(w.weight_kg, NULL) as weight_kg,
            CASE
                WHEN h.height_cm IS NOT NULL AND w.weight_kg IS NOT NULL
                THEN w.weight_kg / ((h.height_cm / 100.0) * (h.height_cm / 100.0))
                ELSE NULL
            END as bmi,
            a.race
        FROM read_csv_auto('{self.hosp_dir}/patients.csv.gz') p
        INNER JOIN read_csv_auto('{self.icu_dir}/icustays.csv.gz') icu
            ON p.subject_id = icu.subject_id
        LEFT JOIN heights h ON p.subject_id = h.subject_id
        LEFT JOIN weights w ON p.subject_id = w.subject_id
        LEFT JOIN read_csv_auto('{self.hosp_dir}/admissions.csv.gz') a
            ON p.subject_id = a.subject_id
        """

        df = self.con.execute(sql).df()
        df = df.drop_duplicates(subset=['subject_id'])  # Remove duplicates from multiple ICU stays
        print(f"   ✓ Extracted demographics for {len(df):,} ICU patients")
        return df

    def extract_vital_signs(self) -> pd.DataFrame:
        """
        Extract vital signs (first 24h of ICU stay) - AVERAGE VALUES ONLY:
        - Temperature, Heart rate, SBP, DBP, Respiratory rate, SpO2
        """
        print("\n🩺 [2/6] Extracting vital signs (24h averages)...")

        sql = f"""
        SELECT
            icu.subject_id,
            icu.hadm_id,
            icu.stay_id,
            -- Temperature (°C) - Average only
            AVG(
                CASE
                    WHEN c.itemid = 223762 THEN c.valuenum  -- Celsius
                    WHEN c.itemid = 223761 THEN (c.valuenum - 32) * 5.0 / 9.0  -- Fahrenheit to Celsius
                    ELSE NULL
                END
            ) as temperature,
            -- Heart Rate - Average only
            AVG(CASE WHEN c.itemid IN (220045) THEN c.valuenum ELSE NULL END) as heart_rate,
            -- Systolic BP - Average only
            AVG(CASE WHEN c.itemid IN (220050, 220179) THEN c.valuenum ELSE NULL END) as sbp,
            -- Diastolic BP - Average only
            AVG(CASE WHEN c.itemid IN (220051, 220180) THEN c.valuenum ELSE NULL END) as dbp,
            -- Respiratory Rate - Average only
            AVG(CASE WHEN c.itemid IN (220210, 224690) THEN c.valuenum ELSE NULL END) as respiratory_rate,
            -- SpO2 - Average only
            AVG(CASE WHEN c.itemid IN (220277) THEN c.valuenum ELSE NULL END) as spo2
        FROM read_csv_auto('{self.icu_dir}/icustays.csv.gz') icu
        LEFT JOIN read_csv_auto('{self.icu_dir}/chartevents.csv.gz') c
            ON icu.stay_id = c.stay_id
            AND c.charttime BETWEEN icu.intime AND icu.intime + INTERVAL '24 hours'
        WHERE c.itemid IN (
            223761, 223762,  -- Temperature
            220045,          -- Heart Rate
            220050, 220179,  -- Systolic BP
            220051, 220180,  -- Diastolic BP
            220210, 224690,  -- Respiratory Rate
            220277           -- SpO2
        )
        GROUP BY icu.subject_id, icu.hadm_id, icu.stay_id
        """

        df = self.con.execute(sql).df()
        print(f"   ✓ Extracted vital signs for {len(df):,} ICU stays")
        return df

    def extract_lab_values(self) -> pd.DataFrame:
        """
        Extract laboratory values (first measurement in -6h to +24h window):
        - Blood gas: pH, PO2, PCO2
        - Hematology: Hematocrit, Hemoglobin, WBC, Platelets
        - Electrolytes: Sodium, Potassium, Chloride, Glucose
        - Coagulation: D-dimer, PT, aPTT
        - Renal: BUN, Creatinine, Lactate
        """
        print("\n🧪 [3/6] Extracting laboratory values (first measurements)...")

        # Map itemids to lab names
        lab_items = {
            # Blood Gas
            50820: 'ph',
            50821: 'po2',
            50818: 'pco2',
            # Hematology
            51221: 'hematocrit',
            51222: 'hemoglobin',
            51301: 'wbc',
            51265: 'platelets',
            # Electrolytes
            50983: 'sodium',
            50971: 'potassium',
            50902: 'chloride',
            50931: 'glucose',
            # Coagulation
            51237: 'd_dimer',
            51274: 'pt',
            51275: 'aptt',  # aPTT (Activated Partial Thromboplastin Time)
            # Renal
            51006: 'bun',
            50912: 'creatinine',
            50813: 'lactate',
        }

        # Build CASE statements for pivoting first values
        pivot_statements = []
        for itemid, name in lab_items.items():
            pivot_statements.append(
                f"MAX(CASE WHEN itemid = {itemid} THEN valuenum ELSE NULL END) as {name}"
            )

        sql = f"""
        WITH ranked_labs AS (
            SELECT
                icu.subject_id,
                icu.hadm_id,
                icu.stay_id,
                le.itemid,
                le.valuenum,
                ROW_NUMBER() OVER(
                    PARTITION BY icu.stay_id, le.itemid ORDER BY le.charttime ASC
                ) as rn
            FROM read_csv_auto('{self.icu_dir}/icustays.csv.gz') icu
            LEFT JOIN read_csv_auto('{self.hosp_dir}/labevents.csv.gz') le
                ON icu.hadm_id = le.hadm_id
                AND le.charttime BETWEEN icu.intime - INTERVAL '6 hours'
                                     AND icu.intime + INTERVAL '24 hours'
            WHERE le.itemid IN ({','.join(map(str, lab_items.keys()))})
        )
        SELECT
            subject_id,
            hadm_id,
            stay_id,
            {', '.join(pivot_statements)}
        FROM ranked_labs
        WHERE rn = 1
        GROUP BY subject_id, hadm_id, stay_id
        """

        df = self.con.execute(sql).df()
        print(f"   ✓ Extracted lab values for {len(df):,} ICU stays")
        return df

    def extract_severity_scores(self) -> pd.DataFrame:
        """
        Extract severity scores:
        - Glasgow Coma Scale (GCS) - minimum value in first 24h
        - GCS Total = Eye Opening (1-4) + Verbal Response (1-5) + Motor Response (1-6)
        """
        print("\n📊 [4/6] Extracting severity scores (GCS)...")

        sql = f"""
        WITH gcs_components AS (
            SELECT
                icu.subject_id,
                icu.hadm_id,
                icu.stay_id,
                c.charttime,
                MAX(CASE WHEN c.itemid = 220739 THEN c.valuenum ELSE NULL END) as gcs_eye,
                MAX(CASE WHEN c.itemid = 223900 THEN c.valuenum ELSE NULL END) as gcs_verbal,
                MAX(CASE WHEN c.itemid = 223901 THEN c.valuenum ELSE NULL END) as gcs_motor
            FROM read_csv_auto('{self.icu_dir}/icustays.csv.gz') icu
            LEFT JOIN read_csv_auto('{self.icu_dir}/chartevents.csv.gz') c
                ON icu.stay_id = c.stay_id
                AND c.charttime BETWEEN icu.intime AND icu.intime + INTERVAL '24 hours'
            WHERE c.itemid IN (220739, 223900, 223901)  -- GCS Eye, Verbal, Motor
            GROUP BY icu.subject_id, icu.hadm_id, icu.stay_id, c.charttime
        )
        SELECT
            subject_id,
            hadm_id,
            stay_id,
            -- GCS Total (worst/minimum value in first 24h, sum of 3 components)
            MIN(
                COALESCE(gcs_eye, 0) +
                COALESCE(gcs_verbal, 0) +
                COALESCE(gcs_motor, 0)
            ) as gcs
        FROM gcs_components
        WHERE (gcs_eye IS NOT NULL OR gcs_verbal IS NOT NULL OR gcs_motor IS NOT NULL)
        GROUP BY subject_id, hadm_id, stay_id
        """

        df = self.con.execute(sql).df()
        print(f"   ✓ Extracted GCS for {len(df):,} ICU stays")
        return df

    def extract_comorbidities(self) -> pd.DataFrame:
        """
        Extract comorbidity indices:
        - Charlson Comorbidity Index
        - Elixhauser Comorbidity Index (component flags)
        """
        print("\n🏥 [5/6] Extracting comorbidities (Charlson Index)...")

        # Charlson comorbidity ICD-10 codes (simplified)
        charlson_codes = {
            'chf': ['I50', 'I11', 'I13'],  # Congestive Heart Failure
            'mi': ['I21', 'I22', 'I25'],   # Myocardial Infarction
            'pvd': ['I70', 'I71', 'I73'],  # Peripheral Vascular Disease
            'cvd': ['I60', 'I61', 'I63'],  # Cerebrovascular Disease
            'copd': ['J41', 'J42', 'J43', 'J44'],  # COPD
            'diabetes': ['E10', 'E11'],    # Diabetes
            'ckd': ['N18'],                # Chronic Kidney Disease
            'liver': ['K70', 'K72', 'K74'],  # Liver Disease
            'cancer': ['C'],               # Cancer (any C code)
        }

        sql = f"""
        WITH diagnoses AS (
            SELECT DISTINCT
                d.subject_id,
                d.hadm_id,
                d.icd_code,
                SUBSTR(d.icd_code, 1, 3) as icd_prefix
            FROM read_csv_auto('{self.hosp_dir}/diagnoses_icd.csv.gz') d
            WHERE d.icd_version = 10  -- ICD-10 codes
        ),
        comorbidities AS (
            SELECT
                subject_id,
                hadm_id,
                MAX(CASE WHEN icd_prefix IN ('I50', 'I11', 'I13') THEN 1 ELSE 0 END) as chf,
                MAX(CASE WHEN icd_prefix IN ('I21', 'I22', 'I25') THEN 1 ELSE 0 END) as mi,
                MAX(CASE WHEN icd_prefix IN ('I70', 'I71', 'I73') THEN 1 ELSE 0 END) as pvd,
                MAX(CASE WHEN icd_prefix IN ('I60', 'I61', 'I63') THEN 1 ELSE 0 END) as cvd,
                MAX(CASE WHEN icd_prefix IN ('J41', 'J42', 'J43', 'J44') THEN 1 ELSE 0 END) as copd,
                MAX(CASE WHEN icd_prefix IN ('E10', 'E11') THEN 1 ELSE 0 END) as diabetes,
                MAX(CASE WHEN icd_prefix IN ('N18') THEN 1 ELSE 0 END) as ckd,
                MAX(CASE WHEN icd_prefix IN ('K70', 'K72', 'K74') THEN 1 ELSE 0 END) as liver_disease,
                MAX(CASE WHEN SUBSTR(icd_prefix, 1, 1) = 'C' THEN 1 ELSE 0 END) as cancer
            FROM diagnoses
            GROUP BY subject_id, hadm_id
        )
        SELECT
            subject_id,
            hadm_id,
            chf,
            mi,
            pvd,
            cvd,
            copd,
            diabetes,
            ckd,
            liver_disease,
            cancer,
            (chf + mi + pvd + cvd + copd + diabetes + ckd + liver_disease + cancer) as charlson_score
        FROM comorbidities
        """

        df = self.con.execute(sql).df()
        print(f"   ✓ Extracted comorbidities for {len(df):,} admissions")
        return df

    def extract_organ_support(self) -> pd.DataFrame:
        """
        Extract organ support indicators:
        - Vasopressor use (Norepinephrine, Phenylephrine, Vasopressin, Epinephrine)
        - Mechanical ventilation
        - Renal replacement therapy (CRRT, CVVHD, Peritoneal Dialysis)
        """
        print("\n💉 [6/6] Extracting organ support indicators...")

        sql = f"""
        WITH vasopressors AS (
            SELECT
                stay_id,
                MAX(CASE WHEN itemid = 221906 THEN 1 ELSE 0 END) as norepinephrine,
                MAX(CASE WHEN itemid = 221749 THEN 1 ELSE 0 END) as phenylephrine,
                MAX(CASE WHEN itemid = 222315 THEN 1 ELSE 0 END) as vasopressin,
                MAX(CASE WHEN itemid = 221289 THEN 1 ELSE 0 END) as epinephrine
            FROM read_csv_auto('{self.icu_dir}/inputevents.csv.gz')
            WHERE itemid IN (221906, 221749, 222315, 221289)
                AND amount > 0
            GROUP BY stay_id
        ),
        ventilation AS (
            SELECT DISTINCT
                stay_id,
                1 as mechanical_ventilation
            FROM read_csv_auto('{self.icu_dir}/chartevents.csv.gz')
            WHERE itemid IN (223848, 223849)  -- Ventilator Type, Ventilator Mode
                AND value IS NOT NULL
        ),
        rrt AS (
            SELECT DISTINCT
                stay_id,
                1 as renal_replacement_therapy
            FROM read_csv_auto('{self.icu_dir}/procedureevents.csv.gz')
            WHERE itemid IN (225802, 225803, 225805, 224144, 225806)  -- Dialysis/CRRT
        )
        SELECT
            icu.subject_id,
            icu.hadm_id,
            icu.stay_id,
            COALESCE(v.norepinephrine, 0) as vasopressor_norepinephrine,
            COALESCE(v.phenylephrine, 0) as vasopressor_phenylephrine,
            COALESCE(v.vasopressin, 0) as vasopressor_vasopressin,
            COALESCE(v.epinephrine, 0) as vasopressor_epinephrine,
            CASE WHEN (v.norepinephrine = 1 OR v.phenylephrine = 1 OR v.vasopressin = 1 OR v.epinephrine = 1)
                 THEN 1 ELSE 0 END as any_vasopressor,
            COALESCE(vent.mechanical_ventilation, 0) as mechanical_ventilation,
            COALESCE(r.renal_replacement_therapy, 0) as renal_replacement_therapy
        FROM read_csv_auto('{self.icu_dir}/icustays.csv.gz') icu
        LEFT JOIN vasopressors v ON icu.stay_id = v.stay_id
        LEFT JOIN ventilation vent ON icu.stay_id = vent.stay_id
        LEFT JOIN rrt r ON icu.stay_id = r.stay_id
        """

        df = self.con.execute(sql).df()
        print(f"   ✓ Extracted organ support for {len(df):,} ICU stays")
        return df

    def calculate_apache_ii(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate APACHE II score from extracted features

        APACHE II = Acute Physiology Score + Age Points + Chronic Health Points

        Components:
        1. Acute Physiology Score (0-60 points): 12 physiological variables
        2. Age Points (0-6 points): Based on age
        3. Chronic Health Points (0-5 points): Chronic diseases + emergency surgery

        Reference: Knaus et al. (1985) Crit Care Med
        """
        print("\n🎯 Calculating APACHE II scores...")

        df = df.copy()

        # Initialize APACHE II score
        df['apache_ii_score'] = 0

        # 1. ACUTE PHYSIOLOGY SCORE (APS)

        # Temperature (rectal, °C)
        df['aps_temp'] = 0
        df.loc[df['temperature'] >= 41, 'aps_temp'] = 4
        df.loc[(df['temperature'] >= 39) & (df['temperature'] < 41), 'aps_temp'] = 3
        df.loc[(df['temperature'] >= 38.5) & (df['temperature'] < 39), 'aps_temp'] = 1
        df.loc[(df['temperature'] >= 36) & (df['temperature'] < 38.5), 'aps_temp'] = 0
        df.loc[(df['temperature'] >= 34) & (df['temperature'] < 36), 'aps_temp'] = 1
        df.loc[(df['temperature'] >= 32) & (df['temperature'] < 34), 'aps_temp'] = 2
        df.loc[(df['temperature'] >= 30) & (df['temperature'] < 32), 'aps_temp'] = 3
        df.loc[df['temperature'] < 30, 'aps_temp'] = 4

        # Mean Arterial Pressure (MAP, mmHg) - we need to calculate from SBP/DBP
        df['map'] = df['dbp'] + (df['sbp'] - df['dbp']) / 3
        df['aps_map'] = 0
        df.loc[df['map'] >= 160, 'aps_map'] = 4
        df.loc[(df['map'] >= 130) & (df['map'] < 160), 'aps_map'] = 3
        df.loc[(df['map'] >= 110) & (df['map'] < 130), 'aps_map'] = 2
        df.loc[(df['map'] >= 70) & (df['map'] < 110), 'aps_map'] = 0
        df.loc[(df['map'] >= 50) & (df['map'] < 70), 'aps_map'] = 2
        df.loc[df['map'] < 50, 'aps_map'] = 4

        # Heart Rate (bpm)
        df['aps_hr'] = 0
        df.loc[df['heart_rate'] >= 180, 'aps_hr'] = 4
        df.loc[(df['heart_rate'] >= 140) & (df['heart_rate'] < 180), 'aps_hr'] = 3
        df.loc[(df['heart_rate'] >= 110) & (df['heart_rate'] < 140), 'aps_hr'] = 2
        df.loc[(df['heart_rate'] >= 70) & (df['heart_rate'] < 110), 'aps_hr'] = 0
        df.loc[(df['heart_rate'] >= 55) & (df['heart_rate'] < 70), 'aps_hr'] = 2
        df.loc[(df['heart_rate'] >= 40) & (df['heart_rate'] < 55), 'aps_hr'] = 3
        df.loc[df['heart_rate'] < 40, 'aps_hr'] = 4

        # Respiratory Rate (breaths/min)
        df['aps_rr'] = 0
        df.loc[df['respiratory_rate'] >= 50, 'aps_rr'] = 4
        df.loc[(df['respiratory_rate'] >= 35) & (df['respiratory_rate'] < 50), 'aps_rr'] = 3
        df.loc[(df['respiratory_rate'] >= 25) & (df['respiratory_rate'] < 35), 'aps_rr'] = 1
        df.loc[(df['respiratory_rate'] >= 12) & (df['respiratory_rate'] < 25), 'aps_rr'] = 0
        df.loc[(df['respiratory_rate'] >= 10) & (df['respiratory_rate'] < 12), 'aps_rr'] = 1
        df.loc[(df['respiratory_rate'] >= 6) & (df['respiratory_rate'] < 10), 'aps_rr'] = 2
        df.loc[df['respiratory_rate'] < 6, 'aps_rr'] = 4

        # Oxygenation: A-aDO2 or PaO2
        # If FiO2 >= 0.5: use A-aDO2, else use PaO2
        # Simplified: use PaO2 (PO2 from blood gas)
        df['aps_oxy'] = 0
        df.loc[df['po2'] >= 70, 'aps_oxy'] = 0
        df.loc[(df['po2'] >= 61) & (df['po2'] < 70), 'aps_oxy'] = 1
        df.loc[(df['po2'] >= 55) & (df['po2'] < 61), 'aps_oxy'] = 3
        df.loc[df['po2'] < 55, 'aps_oxy'] = 4

        # Arterial pH
        df['aps_ph'] = 0
        df.loc[df['ph'] >= 7.7, 'aps_ph'] = 4
        df.loc[(df['ph'] >= 7.6) & (df['ph'] < 7.7), 'aps_ph'] = 3
        df.loc[(df['ph'] >= 7.5) & (df['ph'] < 7.6), 'aps_ph'] = 1
        df.loc[(df['ph'] >= 7.33) & (df['ph'] < 7.5), 'aps_ph'] = 0
        df.loc[(df['ph'] >= 7.25) & (df['ph'] < 7.33), 'aps_ph'] = 2
        df.loc[(df['ph'] >= 7.15) & (df['ph'] < 7.25), 'aps_ph'] = 3
        df.loc[df['ph'] < 7.15, 'aps_ph'] = 4

        # Serum Sodium (mEq/L)
        df['aps_na'] = 0
        df.loc[df['sodium'] >= 180, 'aps_na'] = 4
        df.loc[(df['sodium'] >= 160) & (df['sodium'] < 180), 'aps_na'] = 3
        df.loc[(df['sodium'] >= 155) & (df['sodium'] < 160), 'aps_na'] = 2
        df.loc[(df['sodium'] >= 150) & (df['sodium'] < 155), 'aps_na'] = 1
        df.loc[(df['sodium'] >= 130) & (df['sodium'] < 150), 'aps_na'] = 0
        df.loc[(df['sodium'] >= 120) & (df['sodium'] < 130), 'aps_na'] = 2
        df.loc[(df['sodium'] >= 111) & (df['sodium'] < 120), 'aps_na'] = 3
        df.loc[df['sodium'] < 111, 'aps_na'] = 4

        # Serum Potassium (mEq/L)
        df['aps_k'] = 0
        df.loc[df['potassium'] >= 7, 'aps_k'] = 4
        df.loc[(df['potassium'] >= 6) & (df['potassium'] < 7), 'aps_k'] = 3
        df.loc[(df['potassium'] >= 5.5) & (df['potassium'] < 6), 'aps_k'] = 1
        df.loc[(df['potassium'] >= 3.5) & (df['potassium'] < 5.5), 'aps_k'] = 0
        df.loc[(df['potassium'] >= 3) & (df['potassium'] < 3.5), 'aps_k'] = 1
        df.loc[(df['potassium'] >= 2.5) & (df['potassium'] < 3), 'aps_k'] = 2
        df.loc[df['potassium'] < 2.5, 'aps_k'] = 4

        # Serum Creatinine (mg/dL) - double points if acute renal failure
        df['aps_cr'] = 0
        df.loc[df['creatinine'] >= 3.5, 'aps_cr'] = 4
        df.loc[(df['creatinine'] >= 2) & (df['creatinine'] < 3.5), 'aps_cr'] = 3
        df.loc[(df['creatinine'] >= 1.5) & (df['creatinine'] < 2), 'aps_cr'] = 2
        df.loc[(df['creatinine'] >= 0.6) & (df['creatinine'] < 1.5), 'aps_cr'] = 0
        df.loc[df['creatinine'] < 0.6, 'aps_cr'] = 2

        # Hematocrit (%)
        df['aps_hct'] = 0
        df.loc[df['hematocrit'] >= 60, 'aps_hct'] = 4
        df.loc[(df['hematocrit'] >= 50) & (df['hematocrit'] < 60), 'aps_hct'] = 2
        df.loc[(df['hematocrit'] >= 46) & (df['hematocrit'] < 50), 'aps_hct'] = 1
        df.loc[(df['hematocrit'] >= 30) & (df['hematocrit'] < 46), 'aps_hct'] = 0
        df.loc[(df['hematocrit'] >= 20) & (df['hematocrit'] < 30), 'aps_hct'] = 2
        df.loc[df['hematocrit'] < 20, 'aps_hct'] = 4

        # White Blood Count (1000/mm³)
        df['aps_wbc'] = 0
        df.loc[df['wbc'] >= 40, 'aps_wbc'] = 4
        df.loc[(df['wbc'] >= 20) & (df['wbc'] < 40), 'aps_wbc'] = 2
        df.loc[(df['wbc'] >= 15) & (df['wbc'] < 20), 'aps_wbc'] = 1
        df.loc[(df['wbc'] >= 3) & (df['wbc'] < 15), 'aps_wbc'] = 0
        df.loc[(df['wbc'] >= 1) & (df['wbc'] < 3), 'aps_wbc'] = 2
        df.loc[df['wbc'] < 1, 'aps_wbc'] = 4

        # Glasgow Coma Score (use 15 minus actual GCS)
        df['aps_gcs'] = 15 - df['gcs'].fillna(15)

        # Sum all APS components
        aps_cols = ['aps_temp', 'aps_map', 'aps_hr', 'aps_rr', 'aps_oxy',
                    'aps_ph', 'aps_na', 'aps_k', 'aps_cr', 'aps_hct', 'aps_wbc', 'aps_gcs']
        df['acute_physiology_score'] = df[aps_cols].sum(axis=1)

        # 2. AGE POINTS
        # Need to calculate age from anchor_age and admission time
        # (This will be done in the merge step with admissions data)
        # For now, use anchor_age as approximation
        df['age_points'] = 0
        df.loc[df['anchor_age'] >= 75, 'age_points'] = 6
        df.loc[(df['anchor_age'] >= 65) & (df['anchor_age'] < 75), 'age_points'] = 5
        df.loc[(df['anchor_age'] >= 55) & (df['anchor_age'] < 65), 'age_points'] = 3
        df.loc[(df['anchor_age'] >= 45) & (df['anchor_age'] < 55), 'age_points'] = 2
        df.loc[df['anchor_age'] < 45, 'age_points'] = 0

        # 3. CHRONIC HEALTH POINTS
        # 5 points if:
        # - Nonoperative OR emergency postoperative patient with:
        #   Severe organ insufficiency or immunocompromised
        # 2 points if:
        # - Elective postoperative patient with severe organ insufficiency

        # Simplified: use comorbidities as proxy
        df['chronic_health_points'] = 0
        # If has severe comorbidities (liver disease, cancer), assign points
        # This would need procedure/admission type info for full accuracy
        df.loc[(df['liver_disease'] == 1) | (df['cancer'] == 1), 'chronic_health_points'] = 5

        # FINAL APACHE II SCORE
        df['apache_ii'] = (df['acute_physiology_score'] +
                           df['age_points'] +
                           df['chronic_health_points'])

        print(f"   ✓ Calculated APACHE II for {len(df):,} patients")
        print(f"   ✓ Mean APACHE II: {df['apache_ii'].mean():.1f} (SD: {df['apache_ii'].std():.1f})")

        # Clean up intermediate columns (keep only final score)
        keep_cols = [c for c in df.columns if not c.startswith('aps_')]
        df = df[keep_cols]

        # Drop intermediate calculation columns
        df = df.drop(columns=['map', 'acute_physiology_score', 'age_points', 'chronic_health_points'], errors='ignore')

        return df

    def _validate_dataframe(self, df: pd.DataFrame):
        """
        Validate the final dataframe against the feature metadata.
        - Checks for presence of all features.
        - Checks for correct data types.
        - Checks for valid ranges for binary features.
        """
        print("\n" + "-"*80)
        print("🔍 VALIDATING DATAFRAME SCHEMA AND TYPES")
        print("-" * 80)

        errors = []
        for feature, meta in self.FEATURE_METADATA.items():
            if feature not in df.columns:
                errors.append(f"  - Missing feature: '{feature}'")
                continue

            col = df[feature]
            dtype = col.dtype

            if meta['type'] in ['continuous', 'ordinal']:
                if not np.issubdtype(dtype, np.number):
                    errors.append(f"  - Type mismatch for '{feature}': Expected numeric, got {dtype}")

            elif meta['type'] == 'binary':
                if not np.issubdtype(dtype, np.number):
                    errors.append(f"  - Type mismatch for '{feature}': Expected numeric for binary, got {dtype}")

                # Check if values are in {0, 1, NaN}
                unique_vals = col.dropna().unique()
                if not all(val in [0, 1] for val in unique_vals):
                    errors.append(f"  - Invalid values for binary feature '{feature}': Found {unique_vals}")

            elif meta['type'] == 'categorical':
                if not (dtype == 'object' or pd.api.types.is_categorical_dtype(dtype)):
                    errors.append(f"  - Type mismatch for '{feature}': Expected object/categorical, got {dtype}")

        if errors:
            print("   ✗ Validation failed with the following errors:")
            for error in errors:
                print(error)
            # For stricter pipelines, you might want to raise an exception here:
            # raise ValueError("DataFrame validation failed.")
        else:
            print("   ✓ Dataframe schema and types are valid.")

        print("-" * 80)

    def extract_all_characteristics(self) -> pd.DataFrame:
        """Extract all baseline characteristics and merge into single dataframe"""
        print("\n" + "="*80)
        print("🔬 EXTRACTING BASELINE CHARACTERISTICS")
        print("="*80)

        # Extract each category
        demographics = self.extract_demographics()
        vital_signs = self.extract_vital_signs()
        lab_values = self.extract_lab_values()
        severity_scores = self.extract_severity_scores()
        comorbidities = self.extract_comorbidities()
        organ_support = self.extract_organ_support()

        # Merge all features
        print("\n🔗 Merging all features...")

        # Start with ICU stays as base
        icu_stays = pd.read_csv(f"{self.icu_dir}/icustays.csv.gz")
        df = icu_stays[['subject_id', 'hadm_id', 'stay_id', 'intime', 'outtime', 'los', 'first_careunit']]

        # Merge each feature set
        df = df.merge(demographics[['subject_id', 'gender', 'anchor_age', 'height_cm',
                                    'weight_kg', 'bmi', 'race']],
                     on='subject_id', how='left')

        df = df.merge(vital_signs, on=['subject_id', 'hadm_id', 'stay_id'], how='left')
        df = df.merge(lab_values, on=['subject_id', 'hadm_id', 'stay_id'], how='left')
        df = df.merge(severity_scores, on=['subject_id', 'hadm_id', 'stay_id'], how='left')
        df = df.merge(comorbidities, on=['subject_id', 'hadm_id'], how='left')
        df = df.merge(organ_support, on=['subject_id', 'hadm_id', 'stay_id'], how='left')

        # Calculate APACHE II score
        df = self.calculate_apache_ii(df)

        # Validate final dataframe and attach metadata
        self._validate_dataframe(df)
        df.attrs['feature_metadata'] = self.FEATURE_METADATA

        print("\n" + "="*80)
        print("✅ BASELINE CHARACTERISTICS EXTRACTION COMPLETE!")
        print("="*80)
        print(f"📊 Final dataset: {df.shape[0]:,} patients × {df.shape[1]} features")
        print(f"\n📋 Feature breakdown:")
        print(f"   └─ Demographics: 6 features")
        print(f"   └─ Vital signs: 6 features")
        print(f"   └─ Laboratory: 17 features (excluded: AST, ALT, ALP, GGT, Fibrinogen, Total Protein, Albumin, CRP, Procalcitonin)")
        print(f"   └─ Severity scores: 2 features (GCS, APACHE II)")
        print(f"   └─ Comorbidities: 10 features")
        print(f"   └─ Organ support: 7 features (incl. 'any_vasopressor')")
        print("="*80 + "\n")

        return df


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract baseline characteristics from MIMIC-IV (약물 제외)")
    parser.add_argument("--mimic-dir", default="data/3.1", help="Path to MIMIC-IV directory (default: mimiciv/3.1)")
    parser.add_argument("--output", default="cache/baseline_characteristics_v3.1_final.csv", help="Output CSV file (default: cache/baseline_characteristics_v3.1_final.csv)")

    args = parser.parse_args()

    # Extract features
    extractor = BaselineCharacteristicsExtractor(mimic_dir=args.mimic_dir)
    df = extractor.extract_all_characteristics()

    # Save to CSV
    print(f"💾 Saving to {args.output}...")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    # Print missing value report
    print(f"\n📊 Missing value report (top 10):")
    missing_pct = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
    top_missing = missing_pct[missing_pct > 0].head(10)
    if len(top_missing) > 0:
        for col, pct in top_missing.items():
            print(f"   - {col}: {pct:.1f}%")
    else:
        print("   ✓ No missing values!")

    print(f"\n✅ File saved: {args.output}")
    print(f"✅ Ready for NCT cohort merging!\n")


if __name__ == "__main__":
    main()
