/**
 * Type definitions for workspace API
 */

export interface ProjectInfo {
  project_id: string;
  stages: string[];
  created_at?: string;
}

export interface ProjectListResponse {
  projects: ProjectInfo[];
  total: number;
}

export interface WorkspaceFileInfo {
  size: number;
  extension: string;
}

export interface WorkspaceDataResponse {
  project_id: string;
  stage: string;
  files: Record<string, WorkspaceFileInfo>;
  data?: unknown;
}

export interface FileContentResponse {
  filename: string;
  content: unknown;
}

export interface CohortSummary {
  total_subjects: number;
  [key: string]: unknown;
}

export interface AnalysisData {
  outcomes: unknown;
  metrics: unknown;
}

