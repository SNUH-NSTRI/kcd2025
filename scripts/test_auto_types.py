"""
Test script demonstrating automatic type application when loading CSV.

This shows the difference between regular pd.read_csv() and
load_baseline_characteristics() with automatic type conversion.
"""

import pandas as pd
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from feature_types_utils import load_baseline_characteristics, get_feature_type

def create_sample_csv():
    """Create a sample CSV file for testing."""
    data = {
        'subject_id': [10000001, 10000002, 10000003],
        'temperature': [37.2, 38.5, 36.9],
        'heart_rate': [85, 92, 78],
        'gender': ['M', 'F', 'M'],
        'chf': [0, 1, 0],
        'mi': [1, 0, 1],
        'gcs': [15, 14, 15],
        'apache_ii': [12, 18, 10]
    }
    df = pd.DataFrame(data)
    output_path = Path(__file__).parent.parent / 'cache' / 'test_baseline.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path

def main():
    print("="*80)
    print("AUTOMATIC TYPE APPLICATION TEST")
    print("="*80)

    # Create test CSV
    csv_path = create_sample_csv()
    print(f"\n✓ Created test CSV: {csv_path}")

    print("\n" + "-"*80)
    print("1. LOADING WITH REGULAR pd.read_csv()")
    print("-"*80)
    df_regular = pd.read_csv(csv_path)
    print("\nDataFrame info (regular):")
    print(df_regular.dtypes)
    print(f"\nNote: All numeric columns default to int64/float64")
    print(f"      Categorical columns are 'object' type")
    print(f"      No metadata attached: df.attrs = {df_regular.attrs}")

    print("\n" + "-"*80)
    print("2. LOADING WITH load_baseline_characteristics()")
    print("-"*80)
    df_auto = load_baseline_characteristics(csv_path)
    print("\nDataFrame info (with auto-types):")
    print(df_auto.dtypes)

    print("\n✓ Improvements:")
    print("  - Continuous features: float64 (temperature, heart_rate)")
    print("  - Binary features: Int8 (chf, mi) - saves memory!")
    print("  - Categorical features: category (gender) - saves memory!")
    print("  - Ordinal features: Int16 (gcs, apache_ii)")
    print(f"  - Metadata attached: {len(df_auto.attrs.get('feature_metadata', {}))} features")

    print("\n" + "-"*80)
    print("3. MEMORY USAGE COMPARISON")
    print("-"*80)
    memory_regular = df_regular.memory_usage(deep=True).sum()
    memory_auto = df_auto.memory_usage(deep=True).sum()
    savings = (1 - memory_auto / memory_regular) * 100

    print(f"Regular pd.read_csv():              {memory_regular:,} bytes")
    print(f"load_baseline_characteristics():    {memory_auto:,} bytes")
    print(f"Memory savings:                     {savings:.1f}%")

    print("\n" + "-"*80)
    print("4. TYPE VALIDATION")
    print("-"*80)
    for col in df_auto.columns:
        if col == 'subject_id':
            continue
        try:
            expected_type = get_feature_type(col)
            actual_dtype = df_auto[col].dtype
            print(f"✓ {col:15s} -> {expected_type:12s} (dtype: {actual_dtype})")
        except KeyError:
            print(f"  {col:15s} -> (not in metadata)")

    print("\n" + "="*80)
    print("USAGE IN YOUR CODE:")
    print("="*80)
    print("""
from scripts.feature_types_utils import load_baseline_characteristics

# ✅ Use this instead of pd.read_csv()
df = load_baseline_characteristics('cache/baseline_characteristics.csv')

# Now all types are correctly applied!
# - Continuous: float64
# - Binary: Int8
# - Categorical: category
# - Ordinal: Int16
# - Metadata: df.attrs['feature_metadata']
    """)

    # Clean up
    csv_path.unlink()
    print("\n✓ Test completed and cleaned up")

if __name__ == "__main__":
    main()
