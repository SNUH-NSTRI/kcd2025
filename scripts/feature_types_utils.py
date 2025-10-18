"""
Feature Type Utilities for Baseline Characteristics

This module provides utilities to access and work with feature type metadata
from the baseline characteristics extraction script. Use this for statistical
analysis to ensure appropriate methods are applied to each feature type.

Usage:
    from feature_types_utils import get_feature_type, get_features_by_type

    # Get type of a specific feature
    feature_type = get_feature_type('temperature')  # Returns: 'continuous'

    # Get all features of a specific type
    continuous_features = get_features_by_type('continuous')
    binary_features = get_features_by_type('binary')

    # Get complete metadata
    metadata = get_feature_metadata()
"""

# Feature metadata - Single source of truth for feature types
# This mirrors the FEATURE_METADATA from extract_baseline_characteristics.py
FEATURE_METADATA = {
    # Demographics
    'age_at_admission': {'type': 'continuous', 'description': 'Patient age at admission (alternative naming)', 'unit': 'years'},
    'anchor_age': {'type': 'continuous', 'description': 'Patient age at admission', 'unit': 'years'},
    'gender': {'type': 'categorical', 'description': 'Patient gender', 'unit': None},
    'race': {'type': 'categorical', 'description': 'Patient race/ethnicity', 'unit': None},
    'height_cm': {'type': 'continuous', 'description': 'Patient height', 'unit': 'cm'},
    'weight_kg': {'type': 'continuous', 'description': 'Patient admission weight', 'unit': 'kg'},
    'bmi': {'type': 'continuous', 'description': 'Body Mass Index, calculated from height and weight', 'unit': 'kg/m^2'},

    # Vital Signs (24h average)
    'temperature': {'type': 'continuous', 'description': 'Average temperature in first 24h', 'unit': '°C'},
    'heart_rate': {'type': 'continuous', 'description': 'Average heart rate in first 24h', 'unit': 'bpm'},
    'sbp': {'type': 'continuous', 'description': 'Average systolic blood pressure in first 24h', 'unit': 'mmHg'},
    'dbp': {'type': 'continuous', 'description': 'Average diastolic blood pressure in first 24h', 'unit': 'mmHg'},
    'respiratory_rate': {'type': 'continuous', 'description': 'Average respiratory rate in first 24h', 'unit': 'breaths/min'},
    'spo2': {'type': 'continuous', 'description': 'Average SpO2 in first 24h', 'unit': '%'},

    # Laboratory (first value)
    'ph': {'type': 'continuous', 'description': 'First pH value', 'unit': None},
    'po2': {'type': 'continuous', 'description': 'First partial pressure of oxygen (PO2)', 'unit': 'mmHg'},
    'pco2': {'type': 'continuous', 'description': 'First partial pressure of carbon dioxide (PCO2)', 'unit': 'mmHg'},
    'hematocrit': {'type': 'continuous', 'description': 'First hematocrit value', 'unit': '%'},
    'hemoglobin': {'type': 'continuous', 'description': 'First hemoglobin value', 'unit': 'g/dL'},
    'wbc': {'type': 'continuous', 'description': 'First white blood cell count', 'unit': 'K/uL'},
    'platelets': {'type': 'continuous', 'description': 'First platelet count', 'unit': 'K/uL'},
    'sodium': {'type': 'continuous', 'description': 'First sodium level', 'unit': 'mEq/L'},
    'potassium': {'type': 'continuous', 'description': 'First potassium level', 'unit': 'mEq/L'},
    'chloride': {'type': 'continuous', 'description': 'First chloride level', 'unit': 'mEq/L'},
    'glucose': {'type': 'continuous', 'description': 'First glucose level', 'unit': 'mg/dL'},
    'd_dimer': {'type': 'continuous', 'description': 'First D-dimer value', 'unit': 'ng/mL'},
    'pt': {'type': 'continuous', 'description': 'First prothrombin time (PT)', 'unit': 'seconds'},
    'aptt': {'type': 'continuous', 'description': 'First activated partial thromboplastin time (aPTT)', 'unit': 'seconds'},
    'bun': {'type': 'continuous', 'description': 'First blood urea nitrogen (BUN)', 'unit': 'mg/dL'},
    'creatinine': {'type': 'continuous', 'description': 'First creatinine level', 'unit': 'mg/dL'},
    'lactate': {'type': 'continuous', 'description': 'First lactate level', 'unit': 'mmol/L'},

    # Severity Scores
    'gcs': {'type': 'ordinal', 'description': 'Minimum Glasgow Coma Scale in first 24h', 'unit': 'score'},
    'apache_ii': {'type': 'ordinal', 'description': 'APACHE II score calculated from first 24h data', 'unit': 'score'},

    # Comorbidities
    'chf': {'type': 'binary', 'description': 'Presence of congestive heart failure', 'unit': None},
    'mi': {'type': 'binary', 'description': 'Presence of myocardial infarction history', 'unit': None},
    'pvd': {'type': 'binary', 'description': 'Presence of peripheral vascular disease', 'unit': None},
    'cvd': {'type': 'binary', 'description': 'Presence of cerebrovascular disease', 'unit': None},
    'copd': {'type': 'binary', 'description': 'Presence of chronic obstructive pulmonary disease', 'unit': None},
    'diabetes': {'type': 'binary', 'description': 'Presence of diabetes', 'unit': None},
    'ckd': {'type': 'binary', 'description': 'Presence of chronic kidney disease', 'unit': None},
    'liver_disease': {'type': 'binary', 'description': 'Presence of liver disease', 'unit': None},
    'cancer': {'type': 'binary', 'description': 'Presence of cancer', 'unit': None},
    'charlson_score': {'type': 'ordinal', 'description': 'Charlson comorbidity index score, calculated from ICD codes', 'unit': 'score'},

    # Organ Support
    'vasopressor_norepinephrine': {'type': 'binary', 'description': 'Use of norepinephrine', 'unit': None},
    'vasopressor_phenylephrine': {'type': 'binary', 'description': 'Use of phenylephrine', 'unit': None},
    'vasopressor_vasopressin': {'type': 'binary', 'description': 'Use of vasopressin', 'unit': None},
    'vasopressor_epinephrine': {'type': 'binary', 'description': 'Use of epinephrine', 'unit': None},
    'any_vasopressor': {'type': 'binary', 'description': 'Binary flag indicating use of any vasopressor', 'unit': None},
    'mechanical_ventilation': {'type': 'binary', 'description': 'Received mechanical ventilation', 'unit': None},
    'renal_replacement_therapy': {'type': 'binary', 'description': 'Received renal replacement therapy', 'unit': None},

    # Outcome Variables (should typically NOT be used as covariates for matching)
    'outcome_days': {'type': 'continuous', 'description': 'Days until outcome event (death/discharge)', 'unit': 'days'},
    'los': {'type': 'continuous', 'description': 'Length of stay in ICU', 'unit': 'days'},

    # Additional Severity Scores (if present in cohort)
    'apache_ii_score': {'type': 'ordinal', 'description': 'APACHE II score (alternative naming)', 'unit': 'score'},
}


def get_feature_metadata():
    """
    Get complete feature metadata dictionary.

    Returns:
        dict: Complete FEATURE_METADATA dictionary
    """
    return FEATURE_METADATA.copy()


def get_feature_type(feature_name: str) -> str:
    """
    Get the type of a specific feature.

    Args:
        feature_name: Name of the feature

    Returns:
        str: Feature type ('continuous', 'categorical', 'binary', or 'ordinal')

    Raises:
        KeyError: If feature_name is not found in metadata
    """
    if feature_name not in FEATURE_METADATA:
        raise KeyError(f"Feature '{feature_name}' not found in metadata. "
                      f"Available features: {list(FEATURE_METADATA.keys())}")
    return FEATURE_METADATA[feature_name]['type']


def get_features_by_type(feature_type: str) -> list:
    """
    Get all features of a specific type.

    Args:
        feature_type: Type of features to retrieve
                     ('continuous', 'categorical', 'binary', or 'ordinal')

    Returns:
        list: List of feature names matching the specified type

    Raises:
        ValueError: If feature_type is not valid
    """
    valid_types = {'continuous', 'categorical', 'binary', 'ordinal'}
    if feature_type not in valid_types:
        raise ValueError(f"Invalid feature_type '{feature_type}'. "
                        f"Must be one of: {valid_types}")

    return [name for name, meta in FEATURE_METADATA.items()
            if meta['type'] == feature_type]


def get_feature_info(feature_name: str) -> dict:
    """
    Get complete information for a specific feature.

    Args:
        feature_name: Name of the feature

    Returns:
        dict: Dictionary containing type, description, and unit

    Raises:
        KeyError: If feature_name is not found in metadata
    """
    if feature_name not in FEATURE_METADATA:
        raise KeyError(f"Feature '{feature_name}' not found in metadata")
    return FEATURE_METADATA[feature_name].copy()


def load_baseline_characteristics(csv_path: str, apply_types: bool = True):
    """
    Load baseline characteristics CSV with automatic feature type application.

    This function loads the CSV and automatically applies correct data types
    based on the feature metadata, ensuring proper handling in analysis.

    Args:
        csv_path: Path to the baseline characteristics CSV file
        apply_types: Whether to automatically apply feature types (default: True)

    Returns:
        pd.DataFrame: DataFrame with types correctly applied and metadata attached

    Example:
        >>> df = load_baseline_characteristics('cache/baseline_characteristics.csv')
        >>> # Continuous features are float64
        >>> # Binary features are int8 (0, 1, or NaN)
        >>> # Categorical features are category type
        >>> # Ordinal features are int16
    """
    import pandas as pd
    import numpy as np

    # Load CSV
    df = pd.read_csv(csv_path)

    if apply_types:
        # Apply correct dtypes based on feature metadata
        for col in df.columns:
            if col not in FEATURE_METADATA:
                continue  # Skip ID columns and other non-feature columns

            ftype = FEATURE_METADATA[col]['type']

            try:
                if ftype == 'continuous':
                    # Convert to float64 for continuous variables
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')

                elif ftype == 'binary':
                    # Convert to int8 for binary (0/1) to save memory
                    # NaN values are preserved
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    # Validate binary values
                    unique_vals = df[col].dropna().unique()
                    if not all(val in [0, 1] for val in unique_vals):
                        print(f"Warning: '{col}' has non-binary values: {unique_vals}")
                    df[col] = df[col].astype('Int8')  # Nullable integer type

                elif ftype == 'ordinal':
                    # Convert to int16 for ordinal scores
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int16')

                elif ftype == 'categorical':
                    # Convert to category type for memory efficiency
                    df[col] = df[col].astype('category')

            except Exception as e:
                print(f"Warning: Could not convert '{col}' to {ftype}: {e}")

    # Attach metadata to DataFrame
    df.attrs['feature_metadata'] = FEATURE_METADATA

    return df


def print_feature_summary():
    """
    Print a formatted summary of all features grouped by type.

    Useful for quick reference during analysis.
    """
    type_counts = {}
    for meta in FEATURE_METADATA.values():
        ftype = meta['type']
        type_counts[ftype] = type_counts.get(ftype, 0) + 1

    print("="*80)
    print("BASELINE CHARACTERISTICS FEATURE TYPE SUMMARY")
    print("="*80)
    print(f"\nTotal Features: {len(FEATURE_METADATA)}")
    print(f"\nType Distribution:")
    for ftype in ['continuous', 'categorical', 'binary', 'ordinal']:
        count = type_counts.get(ftype, 0)
        features = get_features_by_type(ftype)
        print(f"\n{ftype.upper()}: {count} features")
        for i, feat in enumerate(features, 1):
            unit = FEATURE_METADATA[feat]['unit']
            unit_str = f" ({unit})" if unit else ""
            print(f"  {i:2d}. {feat}{unit_str}")
    print("="*80)


if __name__ == "__main__":
    # Demo usage
    print_feature_summary()

    print("\n\nExample API Usage:")
    print("-"*80)

    # Example 1: Get type of specific feature
    print("\n1. Get feature type:")
    print(f"   get_feature_type('temperature') = '{get_feature_type('temperature')}'")
    print(f"   get_feature_type('gender') = '{get_feature_type('gender')}'")
    print(f"   get_feature_type('chf') = '{get_feature_type('chf')}'")

    # Example 2: Get all features by type
    print("\n2. Get features by type:")
    continuous = get_features_by_type('continuous')
    print(f"   Continuous features ({len(continuous)}): {continuous[:5]}... (showing first 5)")

    binary = get_features_by_type('binary')
    print(f"   Binary features ({len(binary)}): {binary}")

    # Example 3: Get complete info
    print("\n3. Get feature info:")
    info = get_feature_info('temperature')
    print(f"   temperature: {info}")

    # Example 4: Load CSV with automatic type application
    print("\n4. Load CSV with automatic types:")
    print("   # Instead of:")
    print("   #   df = pd.read_csv('baseline_characteristics.csv')")
    print("   # Use:")
    print("   #   df = load_baseline_characteristics('baseline_characteristics.csv')")
    print("   # This automatically applies correct dtypes based on metadata!")
