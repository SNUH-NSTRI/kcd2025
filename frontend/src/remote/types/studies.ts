/**
 * Study management types
 */

export interface CreateStudyRequest {
  name: string;
  nctId: string;
  researchQuestion: string;
  medicineFamily: string;
  medicineGeneric?: string;
  medicineBrand?: string;
}

export interface StudyResponse {
  status: string;
  message: string;
  studyId: string;
}

export interface StudyProgressStep {
  step: string;
  label: string;
  status: 'pending' | 'in_progress' | 'done' | 'failed';
  startedAt?: string | null;
  completedAt?: string | null;
  error?: string | null;
}

export interface StudyStatus {
  studyId: string;
  overallStatus: 'created' | 'processing' | 'completed' | 'failed';
  currentStep?: string | null;
  steps: StudyProgressStep[];
  createdAt: string;
  updatedAt: string;
  error?: string | null;
}

export interface CorpusDocument {
  title: string;
  metadata: {
    nctId: string;
    eligibility?: {
      eligibilityCriteria: string;
    };
    design?: {
      phases: string[];
    };
    status?: string;
    sponsors?: {
      leadSponsor: {
        name: string;
      };
    };
  };
}

export interface CorpusData {
  documents: CorpusDocument[];
}

export interface CriterionValue {
  field: string;
  op: string;
  value: number | string;
}

export interface Entity {
  text: string;
  type: string;
  domain: string;
  confidence: number;
  standard_name: string;
  umls_cui?: string | null;
  code_system?: string | null;
  code_set?: string[] | null;
  primary_code?: string | null;
  metadata?: any;
}

export interface Criterion {
  id: string;
  description: string;
  category: string;
  kind: string;
  value: CriterionValue;
  entities?: Entity[];
}

export interface Feature {
  name: string;
  source: string;
  unit: string | null;
  timeWindow: [number, number] | null;
  metadata: {
    description: string;
    table?: string;
    column?: string;
    itemid?: number;
    [key: string]: any;
  };
}

export interface SchemaData {
  schemaVersion: string;
  diseaseCode?: string;
  inclusion: Criterion[];
  exclusion: Criterion[];
  features: Feature[];
  provenance?: {
    source: string;
    nctId: string;
    generatedAt: string;
    version: string;
    method: string;
    notes?: string;
  };
}
