/**
 * Cohort Quality Assessment Types
 */

/**
 * Request for cohort quality assessment
 */
export interface CohortQualityRequest {
  nct_id: string;
  medication: string;
}

/**
 * Continuous variable balance result
 */
export interface ContinuousBalanceResult {
  variable: string;
  type: "continuous";
  smd: number;
  p_value: number | null;
  treatment_mean: number;
  treatment_std: number;
  control_mean: number;
  control_std: number;
  overall_mean: number;
  overall_std: number;
  imbalanced: boolean;
  missing_pct: number;
}

/**
 * Categorical variable balance result
 */
export interface CategoricalBalanceResult {
  variable: string;
  type: "categorical";
  chi2: number | null;
  p_value: number | null;
  treatment_dist: Record<string, number>;
  control_dist: Record<string, number>;
  overall_dist: Record<string, number>;
  imbalanced: boolean;
  missing_pct: number;
}

/**
 * Union type for balance results
 */
export type BalanceResult = ContinuousBalanceResult | CategoricalBalanceResult;

/**
 * Continuous variable characterization
 */
export interface ContinuousCharacteristic {
  mean: number;
  std: number;
  median: number;
  q25: number;
  q75: number;
  min: number;
  max: number;
  missing_pct: number;
}

/**
 * Categorical variable characterization
 */
export interface CategoricalCharacteristic {
  counts: Record<string, number>;
  percentages: Record<string, number>;
  missing_pct: number;
}

/**
 * Cohort characteristics (Table 1 format)
 */
export interface CohortCharacteristics {
  sample_size: {
    total: number;
    treatment: number;
    control: number;
  };
  continuous: Record<string, ContinuousCharacteristic>;
  categorical: Record<string, CategoricalCharacteristic>;
}

/**
 * Summary of quality assessment
 */
export interface QualitySummary {
  total_patients: number;
  treatment_count: number;
  control_count: number;
  variables_analyzed: number;
  imbalanced_variables: number;
}

/**
 * Complete quality assessment result
 */
export interface CohortQualityResult {
  summary: QualitySummary;
  baseline_balance: BalanceResult[];
  cohort_characteristics: CohortCharacteristics;
}
