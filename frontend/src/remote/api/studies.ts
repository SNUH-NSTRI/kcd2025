/**
 * Study management API client
 */

import { apiClient } from '../client';
import type {
  CreateStudyRequest,
  StudyResponse,
  StudyStatus,
  CorpusData,
  SchemaData,
} from '../types/studies';

/**
 * Create a new study and start background processing
 */
export async function createStudy(data: CreateStudyRequest): Promise<StudyResponse> {
  return await apiClient.post<StudyResponse>('/api/studies', data);
}

/**
 * Get current processing status of a study
 * Should be polled (e.g., every 3 seconds) to track progress
 */
export async function getStudyStatus(studyId: string): Promise<StudyStatus> {
  return await apiClient.get<StudyStatus>(`/api/studies/${studyId}/status`);
}

/**
 * Get corpus data for a study
 * Returns trial data from ClinicalTrials.gov including original eligibility criteria
 */
export async function getStudyCorpus(studyId: string): Promise<CorpusData> {
  return await apiClient.get<CorpusData>(`/api/studies/${studyId}/corpus`);
}

/**
 * Get schema data for a study
 * Returns parsed trial schema with inclusion/exclusion criteria and MIMIC-IV mappings
 */
export async function getStudySchema(studyId: string): Promise<SchemaData> {
  return await apiClient.get<SchemaData>(`/api/studies/${studyId}/schema`);
}

/**
 * Retry schema parsing for a failed study
 */
export async function retryStudyParsing(studyId: string): Promise<{ status: string; message: string }> {
  return await apiClient.post<{ status: string; message: string }>(`/api/studies/${studyId}/retry`);
}
