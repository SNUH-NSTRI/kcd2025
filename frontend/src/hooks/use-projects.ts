'use client';

/**
 * React Query hooks for project operations
 */

import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '@/remote';

/**
 * Hook to fetch all projects
 */
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.listProjects(),
  });
}

/**
 * Hook to fetch a specific project
 */
export function useProject(projectId: string, enabled = true) {
  return useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.getProject(projectId),
    enabled,
  });
}

