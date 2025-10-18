/**
 * Hook for Statistician Agent execution
 *
 * Provides methods to run the Statistician Agent and poll for results.
 * Integrates with the analysis workflow.
 */

import { useState, useCallback, useRef } from 'react';
import { agentsApi, AgentStatus, type JobStatusResponse } from '@/remote';
import { useToast } from '@/hooks/use-toast';

export interface StatisticianAgentState {
  isRunning: boolean;
  jobId: string | null;
  status: AgentStatus | null;
  progress: string | null;
  result: any | null;
  error: string | null;
}

export function useStatisticianAgent() {
  const { toast } = useToast();
  const [state, setState] = useState<StatisticianAgentState>({
    isRunning: false,
    jobId: null,
    status: null,
    progress: null,
    result: null,
    error: null,
  });

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Start polling job status
   */
  const startPolling = useCallback((jobId: string) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await agentsApi.pollJobStatus(jobId);
        // Backend returns response directly (not wrapped in .data)
        const data = response as JobStatusResponse;

        setState(prev => ({
          ...prev,
          status: data.status,
          progress: data.progress ?? null,
          result: data.result ?? null,
          error: data.error ?? null,
        }));
        
        // DEBUG: Log progress to console
        console.log('[Statistician Agent] Progress:', data.progress);

        // Stop polling if completed or failed
        if (data.status === AgentStatus.COMPLETED || data.status === AgentStatus.FAILED) {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }

          setState(prev => ({ ...prev, isRunning: false }));

          if (data.status === AgentStatus.COMPLETED) {
            // Save result to localStorage for Report page access
            if (data.result) {
              try {
                localStorage.setItem('statistician_latest_result', JSON.stringify({
                  jobId: jobId,
                  timestamp: Date.now(),
                  result: data.result,
                }));
                console.log('[Statistician] Saved result to localStorage');
              } catch (e) {
                console.error('[Statistician] Failed to save to localStorage:', e);
              }
            }

            toast({
              title: 'Statistician Agent completed',
              description: 'PSM + Survival Analysis finished successfully',
            });
          } else {
            toast({
              title: 'Statistician Agent failed',
              description: data.error || 'Unknown error occurred',
              variant: 'destructive',
            });
          }
        }
      } catch (error) {
        console.error('Failed to poll job status:', error);

        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }

        setState(prev => ({
          ...prev,
          isRunning: false,
          error: 'Failed to poll job status',
        }));

        toast({
          title: 'Polling error',
          description: 'Failed to check agent status',
          variant: 'destructive',
        });
      }
    }, 2000); // Poll every 2 seconds
  }, [toast]);

  /**
   * Run Statistician Agent
   */
  const runAgent = useCallback(async (nctId: string, medication: string) => {
    try {
      setState({
        isRunning: true,
        jobId: null,
        status: AgentStatus.PENDING,
        progress: 'Starting agent...',
        result: null,
        error: null,
      });

      toast({
        title: 'Starting Statistician Agent',
        description: `Running multi-method matching analysis for ${nctId}...`,
      });

      // Don't show fake progress - let backend control it
      const response = await agentsApi.runStatistician(nctId, medication, {
        workspace_root: '/Users/kyh/datathon'
      });
      // Backend returns response directly (not wrapped in .data)
      const jobId = response.job_id;

      setState(prev => ({
        ...prev,
        jobId,
        status: response.status,
      }));

      // Start polling
      startPolling(jobId);

      return jobId;
    } catch (error: any) {
      console.error('Failed to start agent:', error);

      setState({
        isRunning: false,
        jobId: null,
        status: AgentStatus.FAILED,
        progress: null,
        result: null,
        error: error.message || 'Failed to start agent',
      });

      toast({
        title: 'Failed to start agent',
        description: error.message || 'Unknown error occurred',
        variant: 'destructive',
      });

      throw error;
    }
  }, [toast, startPolling]);

  /**
   * Cancel agent execution
   */
  const cancelAgent = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    setState({
      isRunning: false,
      jobId: null,
      status: null,
      progress: null,
      result: null,
      error: null,
    });

    toast({
      title: 'Agent cancelled',
      description: 'Statistician Agent execution cancelled',
    });
  }, [toast]);

  /**
   * Reset agent state
   */
  const reset = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    setState({
      isRunning: false,
      jobId: null,
      status: null,
      progress: null,
      result: null,
      error: null,
    });
  }, []);

  return {
    ...state,
    runAgent,
    cancelAgent,
    reset,
  };
}
