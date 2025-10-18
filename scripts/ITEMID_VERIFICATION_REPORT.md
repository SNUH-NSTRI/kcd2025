# MIMIC-IV ItemID Verification Report

## Summary
All itemids in `extract_baseline_characteristics.py` have been verified against MIMIC-IV v3.1 official documentation and corrected where necessary.

**Verification Date**: 2025-01-17
**MIMIC-IV Version**: v3.1
**Verification Method**:
- Direct inspection of `d_items.csv`
- Gemini MCP consultation
- Zen MCP validation

---

## ✅ Corrected Issues

### 1. Height (Demographics)
**Issue**: Unit conversion error
- `226707`: Was treated as cm → **Actually Inch** (needs ×2.54)
- `226730`: Was treated as Inch → **Actually cm** (no conversion)

**Fix**: Reversed unit handling, proper range filters per unit

### 2. Temperature (Vital Signs)
**Issue**: Mixed units without conversion
- `223761`: **Fahrenheit** (needs conversion: `(F-32)×5/9`)
- `223762`: **Celsius** (no conversion)

**Fix**: Added Fahrenheit to Celsius conversion

### 3. Weight (Demographics)
**Issue**: Incorrect unit assumption
- `224639`: Was treated as **lbs** → **Actually kg**

**Fix**: Removed incorrect conversion (×0.453592)

### 4. GCS (Severity Scores)
**Issue**: Wrong itemid
- `220739`: Used as GCS Total → **Actually only Eye Opening (1-4)**

**Fix**: Proper 3-component calculation:
- `220739`: GCS Eye Opening (1-4)
- `223900`: GCS Verbal Response (1-5)
- `223901`: GCS Motor Response (1-6)
- **Total**: Sum of 3 components (3-15 range)

### 5. Mechanical Ventilation (Organ Support)
**Issue**: Non-existent itemid
- `720`: **Does not exist in MIMIC-IV** (legacy from MIMIC-III)

**Fix**: Use correct MetaVision itemids:
- `223848`: Ventilator Type
- `223849`: Ventilator Mode

### 6. Vasopressors (Organ Support)
**Issue**: Mislabeled itemid
- `221749`: Was labeled as Norepinephrine → **Actually Phenylephrine**

**Fix**: Separated into 4 distinct categories:
- `221906`: Norepinephrine
- `221749`: Phenylephrine
- `222315`: Vasopressin
- `221289`: Epinephrine

### 7. Laboratory Values Extraction Logic
**Issue**: Using AVG instead of FIRST value
- Docstring stated "first measurement"
- Code calculated average (`AVG(...)`)

**Fix**:
- Used `ROW_NUMBER()` window function
- Extracts chronologically first value per itemid
- More clinically accurate for baseline assessment

---

## ✅ Verified Correct

### Demographics
- `226512`: Admission Weight (kg) ✓
- Gender, Age, Race fields ✓

### Vital Signs (24h averages)
- `220045`: Heart Rate (bpm) ✓
- `220050`, `220179`: SBP (mmHg) ✓
- `220051`, `220180`: DBP (mmHg) ✓
- `220210`, `224690`: Respiratory Rate ✓
- `220277`: SpO2 (%) ✓

### Laboratory Values (26 itemids)
All verified correct:

**Blood Gas:**
- `50820`: pH ✓
- `50821`: PO2 ✓
- `50818`: PCO2 ✓

**Hematology:**
- `51221`: Hematocrit ✓
- `51222`: Hemoglobin ✓
- `51301`: WBC ✓
- `51265`: Platelets ✓

**Electrolytes:**
- `50983`: Sodium ✓
- `50971`: Potassium ✓
- `50902`: Chloride ✓
- `50931`: Glucose ✓

**Liver Function:**
- `50878`: AST ✓
- `50861`: ALT ✓
- `50863`: ALP ✓
- `50927`: GGT ✓

**Coagulation:**
- `51237`: D-dimer ✓
- `51214`: Fibrinogen ✓
- `51274`: PT ✓
- `51275`: aPTT ✓ (renamed from ptt)

**Renal:**
- `51006`: BUN ✓
- `50912`: Creatinine ✓
- `50813`: Lactate ✓

**Proteins:**
- `50976`: Total Protein ✓
- `50862`: Albumin ✓

**Inflammation:**
- `50889`: CRP ✓
- `51003`: Procalcitonin ✓

### Organ Support
**Vasopressors (inputevents):**
- All 4 itemids verified ✓

**RRT (procedureevents):**
- `225802`: Dialysis - CRRT ✓
- `225803`: Dialysis - CVVHD ✓
- `225805`: Peritoneal Dialysis ✓
- `224144`: Blood Flow (ml/min) ✓
- `225806`: Volume In (PD) ✓

### Comorbidities
- ICD-10 code mapping verified ✓

---

## 📊 Methodological Decisions

### Time Window: `-6h to +24h`
**Rationale** (confirmed with Zen MCP):
- ICU admission (`icu.intime`) is an **administrative event**
- Critical labs are drawn in ED/ward **before** official ICU transfer
- Pre-admission window captures the acute state that necessitated ICU care
- **Standard practice** in MIMIC research (MIT LCP guidelines)
- Reduces missing data without sacrificing clinical relevance

**Alternative** (`0h to +24h`):
- ❌ Higher missing data rate
- ❌ "First" value may be hours after admission, post-intervention
- ❌ Less clinically representative of admission state

---

## 🎯 Impact Summary

### Data Quality Improvements
1. **Height**: Will now correctly convert all values to cm
2. **Temperature**: Unified to Celsius across both itemids
3. **Weight**: No longer incorrectly converting kg to kg
4. **GCS**: Now properly calculates total score (3-15 range)
5. **Ventilation**: Uses valid itemids only
6. **Vasopressors**: 4 distinct types instead of 3
7. **Lab Values**: True baseline (first measurement) instead of average

### Expected Changes
- More complete height/weight data (includes Inch measurements)
- Unified temperature scale
- Accurate GCS scores (lower than before, as Eye Opening alone is 1-4)
- Reduced ventilation false negatives
- More granular vasopressor analysis
- More representative lab baseline values

---

## 📝 Code Changes

### Files Modified
- `통합필요/scripts/extract_baseline_characteristics.py`

### Methods Updated
1. `extract_demographics()`: Height/Weight units
2. `extract_vital_signs()`: Temperature conversion
3. `extract_lab_values()`: AVG→FIRST logic, aPTT rename
4. `extract_severity_scores()`: GCS 3-component calculation
5. `extract_organ_support()`: Ventilation itemids, Phenylephrine separation

### Lines of Code Changed
- ~150 lines modified/added
- No breaking changes to output schema (except new `vasopressor_phenylephrine` column)

---

## ✅ Validation Checklist

- [x] All itemids verified against `d_items.csv`
- [x] Unit conversions mathematically correct
- [x] Time windows clinically justified
- [x] Extraction logic matches documentation
- [x] SQL queries optimized (ROW_NUMBER for first values)
- [x] Column names descriptive and consistent
- [x] Gemini MCP validation completed
- [x] Zen MCP expert review completed

---

## 📚 References

1. **MIMIC-IV v3.1 Official Documentation**
   https://physionet.org/content/mimiciv/3.1/

2. **MIMIC-IV d_items Dictionary**
   `data/3.1/icu/d_items.csv`
   `data/3.1/hosp/d_labitems.csv`

3. **MIT Laboratory for Computational Physiology**
   Standard baseline extraction methodology

4. **Glasgow Coma Scale**
   Teasdale & Jennett (1974), official scoring system

5. **APACHE II Scoring**
   Knaus et al. (1985), Critical Care Medicine

---

## 🔍 Recommendations for Future Work

1. **Dopamine**: Consider adding itemid `221662` (another common vasopressor)
2. **Intubation Status**: For GCS Verbal, handle intubated patients specially
3. **Lab Units**: Add explicit unit validation/conversion if needed
4. **Data Quality Checks**: Add reasonable range filters for all continuous variables
5. **Documentation**: Consider adding unit columns to output CSV for transparency

---

**Report Generated**: 2025-01-17
**Verified By**: Gemini-2.5-Pro + Zen MCP
**Status**: ✅ All corrections applied and validated
