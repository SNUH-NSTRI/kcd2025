import type { SchemaData, Criterion, Entity } from '@/remote/types/studies';

/**
 * ICD code structure from backend enrichment
 */
export interface IcdCode {
  code: string;
  title: string;
}

/**
 * MIMIC-IV mapping structure (dynamic vars/method pairs)
 */
export interface MimicMapping {
  [key: string]: string; // vars1, method1, vars2, method2, etc.
}

/**
 * Enriched metadata including ICD codes
 */
export interface EnrichedEntityMetadata {
  icd9?: IcdCode[];
  icd10?: IcdCode[];
  section?: string;
  criterion_id?: string;
  criterion_original?: string;
  standardization?: any;
  mapping_method?: string;
  mapping_confidence?: number;
  mapping_error?: string;
  [key: string]: unknown;
}

/**
 * Enriched entity with ICD codes
 */
export interface EnrichedEntity extends Omit<Entity, 'metadata'> {
  metadata?: EnrichedEntityMetadata;
}

/**
 * Enriched criterion with MIMIC mapping
 */
export interface EnrichedCriterion extends Omit<Criterion, 'entities'> {
  mimic_mapping?: MimicMapping;
  entities?: EnrichedEntity[];
}

/**
 * Main enrichment data structure
 */
export interface EnrichmentData extends Omit<SchemaData, 'inclusion' | 'exclusion'> {
  inclusion: EnrichedCriterion[];
  exclusion: EnrichedCriterion[];
}

/**
 * Parsed MIMIC mapping for display
 */
export interface ParsedMimicEntry {
  index: number;
  vars: string;
  method: string;
}
