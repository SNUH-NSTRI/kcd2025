/**
 * Trialist Hybrid Pipeline Types
 */

export interface CriterionEntity {
  id: string;
  text: string;
  entity_type: 'demographic' | 'measurement' | 'condition' | 'procedure' | 'medication';
  attribute: string;
  operator?: string;
  value?: string;
  unit?: string;
  negation: boolean;
  temporal_constraint?: TemporalConstraint;
  sub_criteria?: CriterionEntity[];
  assumptions_made: string[];
}

export interface TemporalConstraint {
  operator: 'within_last' | 'before' | 'after' | 'between';
  value: number;
  unit: 'hours' | 'days' | 'weeks' | 'months' | 'years';
  reference_point: string;
}

export interface MimicMapping {
  table: string;
  columns: string[];
  join_table?: string;
  join_columns?: string[];
  join_condition?: string;
  sql_condition: string;
  icd_codes?: string[];
  itemids?: number[];
}

export interface MappingOutput {
  criterion: CriterionEntity;
  mimic_mapping: MimicMapping;
  confidence: number;
  reasoning: string;
}

export interface ValidationResult {
  criterion_id: string;
  validation_status: 'passed' | 'warning' | 'needs_review' | 'failed';
  confidence_score: number;
  flags: string[];
  warnings: string[];
  sql_query: string | null;
}

export interface PipelineSummary {
  total_criteria: number;
  stage1_extracted: number;
  stage1_extraction_rate: number;
  stage2_mapped: number;
  stage2_mapping_rate: number;
  stage3_passed: number;
  stage3_warning: number;
  stage3_needs_review: number;
  stage3_failed: number;
  stage3_validation_rate: number;
  avg_confidence: number;
  execution_time_seconds: number;
}

export interface TrialistHybridRequest {
  raw_criteria: string;
  nct_id?: string;
}

export interface TrialistHybridResponse {
  extraction: {
    inclusion: CriterionEntity[];
    exclusion: CriterionEntity[];
  };
  mappings: MappingOutput[];
  validations: ValidationResult[];
  summary: PipelineSummary;
  workspace_path: string | null;
}

export interface TrialistHybridNctResponse extends TrialistHybridResponse {
  nct_id: string;
  eligibility_criteria: string;
  corpus_path: string | null;
  metadata_path: string | null;
}
