/**
 * ClinicalTrials.gov API client
 */

import { apiClient } from '../client';

export interface CTSearchRequest {
  query?: string;
  condition?: string;
  intervention?: string;
  sponsor?: string;
  status?: string[];
  phase?: string[];
  page_size?: number;
  page_token?: string;
}

export interface CTSearchResponse {
  status: string;
  message: string;
  studies: TrialSummary[];
  total_count: number;
  next_page_token?: string;
  error?: string;
}

export interface CTDetailResponse {
  status: string;
  message: string;
  study: TrialDetail | null;
  error?: string;
}

export interface TrialSummary {
  nctId: string;
  briefTitle: string;
  officialTitle: string;
  overallStatus: string;
  phase: string;
  studyType: string;
  enrollment?: number;
  startDate?: string;
  completionDate?: string;
  conditions: string[];
  interventions: Intervention[];
  sponsor: {
    lead: string;
    collaborators: string[];
  };
  summary?: string;
  eligibilityCriteria?: string;
  sex?: string;
  minimumAge?: string;
  maximumAge?: string;
}

export interface TrialDetail extends TrialSummary {
  description?: string;
  arms: Arm[];
  primaryOutcomes: Outcome[];
  secondaryOutcomes: Outcome[];
  studyDesign: {
    allocation?: string;
    interventionModel?: string;
    masking?: string;
    primaryPurpose?: string;
  };
  locations: Location[];
}

export interface Intervention {
  type: string;
  name: string;
  description?: string;
}

export interface Arm {
  label: string;
  type: string;
  description?: string;
  interventionNames: string[];
}

export interface Outcome {
  measure: string;
  description?: string;
  timeFrame?: string;
}

export interface Location {
  facility?: string;
  city?: string;
  state?: string;
  country?: string;
  status?: string;
}

/**
 * Search clinical trials on ClinicalTrials.gov
 */
export async function searchClinicalTrials(
  request: CTSearchRequest
): Promise<CTSearchResponse> {
  try {
    // apiClient already returns parsed JSON directly (not response.data)
    return await apiClient.post<CTSearchResponse>(
      '/api/pipeline/clinicaltrials/search',
      request
    );
  } catch (error) {
    console.error('Search clinical trials error:', error);
    return {
      status: 'error',
      message: 'Failed to search clinical trials',
      studies: [],
      total_count: 0,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Get detailed information for a specific trial
 */
export async function getTrialDetails(nctId: string): Promise<CTDetailResponse> {
  try {
    // apiClient already returns parsed JSON directly (not response.data)
    return await apiClient.get<CTDetailResponse>(
      `/api/pipeline/clinicaltrials/${nctId}`
    );
  } catch (error) {
    console.error('Get trial details error:', error);
    return {
      status: 'error',
      message: `Failed to fetch details for ${nctId}`,
      study: null,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Helper function to format trial status for display
 */
export function formatTrialStatus(status: string): string {
  return status
    .toLowerCase()
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Helper function to format phase for display
 */
export function formatPhase(phase: string): string {
  if (phase === 'N/A') return 'Not Applicable';
  return phase.replace('PHASE', 'Phase ');
}

/**
 * Helper function to get status badge color
 */
export function getStatusColor(
  status: string
): 'default' | 'secondary' | 'destructive' | 'outline' {
  const normalizedStatus = status.toUpperCase();
  switch (normalizedStatus) {
    case 'RECRUITING':
    case 'ACTIVE_NOT_RECRUITING':
      return 'default';
    case 'COMPLETED':
      return 'secondary';
    case 'TERMINATED':
    case 'SUSPENDED':
    case 'WITHDRAWN':
      return 'destructive';
    default:
      return 'outline';
  }
}

/**
 * Helper function to get phase badge color
 */
export function getPhaseColor(
  phase: string
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (phase) {
    case 'PHASE4':
      return 'default';
    case 'PHASE3':
      return 'secondary';
    case 'PHASE2':
    case 'PHASE1':
      return 'outline';
    default:
      return 'outline';
  }
}
