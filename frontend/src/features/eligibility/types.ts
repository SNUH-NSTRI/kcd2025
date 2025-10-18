/**
 * TypeScript type definitions for Eligibility Extraction system.
 *
 * These types mirror the Pydantic schemas in backend/src/rwe_api/schemas/eligibility_schemas.py
 * Ensures type safety across the full stack.
 */

export type CriterionType = "inclusion" | "exclusion";

export type CriterionOperator =
  | ">="
  | "<="
  | "=="
  | "!="
  | "in"
  | "not_in"
  | "between"
  | "contains";

/**
 * Individual eligibility criterion with structured fields.
 */
export interface EligibilityCriterion {
  id: string; // e.g., "inc_1", "exc_1"
  type: CriterionType;
  key: string; // e.g., "Age", "ECOG Performance Status"
  operator: CriterionOperator;
  value: any; // For 'between': [min, max], For 'in': [value1, value2, ...]
  unit: string | null; // e.g., "years", "g/dL", "mg/mL"
  original_text: string; // Original NCT text snippet
}

/**
 * Complete eligibility extraction result.
 */
export interface EligibilityExtraction {
  inclusion: EligibilityCriterion[];
  exclusion: EligibilityCriterion[];
  confidence_score: number; // 0.0-1.0
  model_version: string;
  extracted_at: string; // ISO datetime
}

/**
 * Study metadata for example selection.
 */
export interface StudyMetadata {
  condition: string; // Normalized condition (e.g., "sepsis", "diabetes")
  phase: string; // e.g., "phase_3", "phase_2"
  keywords: string[]; // Selected keywords for this study
}

/**
 * Quality metrics for a correction.
 */
export interface QualityMetrics {
  quality_score: number; // 0.0-1.0
  num_changes: number; // Number of changes made
  has_empty_inclusion: boolean;
  has_short_text: boolean;
}

/**
 * Change between original and corrected extraction.
 */
export interface CorrectionChange {
  field: string;
  criterion_id: string | null;
  original_value: any;
  corrected_value: any;
  change_type: "added" | "removed" | "modified";
}

/**
 * Complete correction record.
 */
export interface Correction {
  nct_id: string;
  corrected_at: string; // ISO datetime
  corrected_by: string; // User email/ID
  study_metadata: StudyMetadata;
  extraction: {
    original_ai_output: EligibilityExtraction;
    human_corrected: EligibilityExtraction;
    changes: CorrectionChange[];
  };
  quality_metrics: QualityMetrics;
}

/**
 * Example used for few-shot prompting.
 */
export interface CorrectionExample {
  nct_id: string;
  extraction: EligibilityExtraction;
  metadata: StudyMetadata;
  quality_score: number;
  selected_reason: "condition_match" | "keyword_overlap" | "recent" | "seed";
}

// ============================================================================
// API Request/Response Types
// ============================================================================

/**
 * Request to extract eligibility criteria from NCT data.
 */
export interface ExtractRequest {
  nct_id: string; // NCT ID (e.g., "NCT03389555")
}

/**
 * Response from extraction endpoint.
 */
export interface ExtractResponse {
  nct_id: string;
  extraction: EligibilityExtraction;
  examples_used: CorrectionExample[];
  original_eligibility_text: string; // Raw eligibility text from NCT
}

/**
 * Review action type.
 */
export type ReviewAction = "accept" | "edit";

/**
 * Request to review/correct an extraction.
 */
export interface ReviewRequest {
  nct_id: string;
  action: ReviewAction;
  original_extraction: EligibilityExtraction;
  corrected_extraction?: EligibilityExtraction; // Required if action === "edit"
  keywords?: string[]; // Selected keywords for indexing
}

/**
 * Response from review endpoint.
 */
export interface ReviewResponse {
  success: boolean;
  correction_id: string; // Version ID (e.g., "v1", "v2")
  quality_score: number;
  message: string;
}

/**
 * Correction statistics response.
 */
export interface CorrectionStats {
  total_corrections: number;
  total_trials: number;
  avg_quality_score: number;
  corrections_by_condition: Record<string, number>;
  corrections_by_keyword: Record<string, number>;
  recent_corrections: Array<{
    nct_id: string;
    corrected_at: string;
    quality_score: number;
  }>;
}

/**
 * Correction history response.
 */
export interface CorrectionHistory {
  nct_id: string;
  versions: Correction[];
  latest_version: string; // Version ID
}

// ============================================================================
// UI State Types
// ============================================================================

/**
 * Extraction workflow state.
 */
export type ExtractionStatus =
  | "idle"
  | "fetching_nct"
  | "selecting_examples"
  | "extracting"
  | "reviewing"
  | "submitting"
  | "completed"
  | "error";

/**
 * UI state for extraction workflow.
 */
export interface ExtractionState {
  status: ExtractionStatus;
  nct_id: string | null;
  extraction: EligibilityExtraction | null;
  original_text: string | null;
  examples_used: CorrectionExample[];
  error: string | null;
}

/**
 * Form state for criterion editor.
 */
export interface CriterionFormData {
  type: CriterionType;
  key: string;
  operator: CriterionOperator;
  value: any;
  unit: string | null;
  original_text: string;
}
