/**
 * Statistician Agent Panel Component
 *
 * Provides UI for running Statistician Agent (PSM + Survival Analysis)
 * and displaying results.
 */

'use client';

import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, PlayCircle, XCircle, CheckCircle2, Activity } from 'lucide-react';
import { useStatisticianAgent } from '../hooks/use-statistician-agent';
import { AgentStatus } from '@/remote';
import { CausalForestViewer } from './causal-forest-viewer';
import { PSMTELOSViewer } from './psm-telos-viewer';
import { StatisticianResultsViewer } from './statistician-results-viewer';
import { MethodComparisonViewer } from './method-comparison-viewer';

interface StatisticianPanelProps {
  nctId: string;
  medication: string;
  onComplete?: (result: any) => void;
}

export function StatisticianPanel({ nctId, medication, onComplete }: StatisticianPanelProps) {
  const agent = useStatisticianAgent();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCausalForestExpanded, setIsCausalForestExpanded] = useState(false);

  // Extract CATE values at the top level (before any conditional rendering)
  const cateValues = useMemo(() => {
    const outcomes = agent.result?.output?.outcomes;
    if (outcomes && Array.isArray(outcomes)) {
      return outcomes
        .map((outcome: any) => outcome.cate_value)
        .filter((val: any): val is number => typeof val === 'number');
    }
    return [];
  }, [agent.result]);

  const handleRun = async () => {
    try {
      await agent.runAgent(nctId, medication);
    } catch (error) {
      console.error('Failed to run agent:', error);
    }
  };

  const statusColor = {
    [AgentStatus.PENDING]: 'bg-yellow-500',
    [AgentStatus.PROCESSING]: 'bg-blue-500',
    [AgentStatus.COMPLETED]: 'bg-green-500',
    [AgentStatus.FAILED]: 'bg-red-500',
  };

  const statusIcon = {
    [AgentStatus.PENDING]: <Loader2 className="h-4 w-4 animate-spin" />,
    [AgentStatus.PROCESSING]: <Activity className="h-4 w-4 animate-pulse" />,
    [AgentStatus.COMPLETED]: <CheckCircle2 className="h-4 w-4" />,
    [AgentStatus.FAILED]: <XCircle className="h-4 w-4" />,
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Statistician Agent
            </CardTitle>
            <CardDescription>
              Real-world evidence analysis with causal inference and survival modeling
            </CardDescription>
          </div>

          {agent.status && (
            <Badge className={`${statusColor[agent.status]} text-white`}>
              <span className="flex items-center gap-1">
                {statusIcon[agent.status]}
                {agent.status}
              </span>
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Progress Display */}
        {agent.isRunning && (
          <div className="space-y-4">
            {/* Animated Progress Header */}
            <div className="rounded-xl border border-blue-500/30 bg-gradient-to-br from-blue-500/15 via-blue-500/10 to-transparent p-5 shadow-sm">
              <div className="flex items-start gap-4">
                <div className="relative">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                  <div className="absolute inset-0 h-6 w-6 animate-ping rounded-full bg-blue-500/30" />
                </div>
                <div className="flex-1 space-y-2.5">
                  <div className="text-base font-semibold text-foreground tracking-tight">
                    {agent.progress || 'Initializing agent...'}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <div className="flex items-center gap-1.5">
                      <div className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
                      <span>Processing</span>
                    </div>
                    {agent.jobId && (
                      <>
                        <span>•</span>
                        <span className="font-mono opacity-70">Job {agent.jobId.slice(0, 8)}...</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Elegant Pipeline Steps */}
            <div className="rounded-xl border border-border/60 bg-gradient-to-br from-muted/40 to-muted/20 p-5 shadow-sm">
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-foreground tracking-tight">
                  Analysis Pipeline
                </h4>
              </div>

              <div className="grid grid-cols-7 gap-1.5">
                {/* Step 1: 4 Algorithms */}
                <div className={`group relative flex flex-col items-center gap-2 p-2 rounded-lg transition-all duration-300 ${
                  agent.progress?.includes('Step 1/6') || agent.progress?.includes('matching algorithms')
                    ? 'bg-emerald-500/10 border border-emerald-500/30 shadow-sm'
                    : 'bg-transparent border border-transparent'
                }`}>
                  <div className="relative flex-shrink-0">
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                      agent.progress?.includes('Step 1/6') || agent.progress?.includes('matching algorithms')
                        ? 'border-emerald-500 bg-emerald-500/20'
                        : 'border-muted-foreground/30 bg-muted/30'
                    }`}>
                      {agent.progress?.includes('Step 1/6') || agent.progress?.includes('matching algorithms') ? (
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      ) : (
                        <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
                      )}
                    </div>
                  </div>
                  <div className="flex-1 text-center">
                    <div className={`text-[9px] font-medium transition-colors duration-300 ${
                      agent.progress?.includes('Step 1/6') || agent.progress?.includes('matching algorithms')
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-muted-foreground/60'
                    }`}>
                      4 Algorithms
                    </div>
                    <div className="text-[8px] text-muted-foreground/50 mt-0.5">
                      Matching
                    </div>
                  </div>
                </div>

                {/* Step 2: Baseline Extraction */}
                <div className={`group relative flex flex-col items-center gap-2 p-2 rounded-lg transition-all duration-300 ${
                  agent.progress?.includes('Step 2/6') || agent.progress?.includes('Extracting baseline')
                    ? 'bg-blue-500/10 border border-blue-500/30 shadow-sm'
                    : 'bg-transparent border border-transparent'
                }`}>
                  <div className="relative flex-shrink-0">
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                      agent.progress?.includes('Step 2/6') || agent.progress?.includes('Extracting baseline')
                        ? 'border-blue-500 bg-blue-500/20'
                        : 'border-muted-foreground/30 bg-muted/30'
                    }`}>
                      {agent.progress?.includes('Step 2/6') || agent.progress?.includes('Extracting baseline') ? (
                        <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                      ) : (
                        <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
                      )}
                    </div>
                  </div>
                  <div className="flex-1 text-center">
                    <div className={`text-[9px] font-medium transition-colors duration-300 ${
                      agent.progress?.includes('Step 2/6') || agent.progress?.includes('Extracting baseline')
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-muted-foreground/60'
                    }`}>
                      Baseline Extract
                    </div>
                    <div className="text-[8px] text-muted-foreground/50 mt-0.5">
                      4 methods
                    </div>
                  </div>
                </div>

                {/* Step 3: LLM Comparison */}
                <div className={`group relative flex flex-col items-center gap-2 p-2 rounded-lg transition-all duration-300 ${
                  agent.progress?.includes('Step 3/6') || agent.progress?.includes('compare baseline')
                    ? 'bg-purple-500/10 border border-purple-500/30 shadow-sm'
                    : 'bg-transparent border border-transparent'
                }`}>
                  <div className="relative flex-shrink-0">
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                      agent.progress?.includes('Step 3/6') || agent.progress?.includes('compare baseline')
                        ? 'border-purple-500 bg-purple-500/20'
                        : 'border-muted-foreground/30 bg-muted/30'
                    }`}>
                      {agent.progress?.includes('Step 3/6') || agent.progress?.includes('compare baseline') ? (
                        <div className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
                      ) : (
                        <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
                      )}
                    </div>
                  </div>
                  <div className="flex-1 text-center">
                    <div className={`text-[9px] font-medium transition-colors duration-300 ${
                      agent.progress?.includes('Step 3/6') || agent.progress?.includes('compare baseline')
                        ? 'text-purple-600 dark:text-purple-400'
                        : 'text-muted-foreground/60'
                    }`}>
                      LLM Compare
                    </div>
                    <div className="text-[8px] text-muted-foreground/50 mt-0.5">
                      Select best
                    </div>
                  </div>
                </div>

                {/* Step 4: Balance Assessment */}
                <div className={`group relative flex flex-col items-center gap-2 p-2 rounded-lg transition-all duration-300 ${
                  agent.progress?.includes('Step 4/6') || agent.progress?.includes('covariate balance')
                    ? 'bg-orange-500/10 border border-orange-500/30 shadow-sm'
                    : 'bg-transparent border border-transparent'
                }`}>
                  <div className="relative flex-shrink-0">
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                      agent.progress?.includes('Step 4/6') || agent.progress?.includes('covariate balance')
                        ? 'border-orange-500 bg-orange-500/20'
                        : 'border-muted-foreground/30 bg-muted/30'
                    }`}>
                      {agent.progress?.includes('Step 4/6') || agent.progress?.includes('covariate balance') ? (
                        <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
                      ) : (
                        <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
                      )}
                    </div>
                  </div>
                  <div className="flex-1 text-center">
                    <div className={`text-[9px] font-medium transition-colors duration-300 ${
                      agent.progress?.includes('Step 4/6') || agent.progress?.includes('covariate balance')
                        ? 'text-orange-600 dark:text-orange-400'
                        : 'text-muted-foreground/60'
                    }`}>
                      Balance Check
                    </div>
                    <div className="text-[8px] text-muted-foreground/50 mt-0.5">
                      SMD assessment
                    </div>
                  </div>
                </div>

                {/* Step 5: Demographics */}
                <div className={`group relative flex flex-col items-center gap-2 p-2 rounded-lg transition-all duration-300 ${
                  agent.progress?.includes('Step 5/6') || agent.progress?.includes('baseline characteristics table') || agent.progress?.includes('Table 1')
                    ? 'bg-pink-500/10 border border-pink-500/30 shadow-sm'
                    : 'bg-transparent border border-transparent'
                }`}>
                  <div className="relative flex-shrink-0">
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                      agent.progress?.includes('Step 5/6') || agent.progress?.includes('baseline characteristics table') || agent.progress?.includes('Table 1')
                        ? 'border-pink-500 bg-pink-500/20'
                        : 'border-muted-foreground/30 bg-muted/30'
                    }`}>
                      {agent.progress?.includes('Step 5/6') || agent.progress?.includes('baseline characteristics table') || agent.progress?.includes('Table 1') ? (
                        <div className="w-2 h-2 rounded-full bg-pink-500 animate-pulse" />
                      ) : (
                        <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
                      )}
                    </div>
                  </div>
                  <div className="flex-1 text-center">
                    <div className={`text-[9px] font-medium transition-colors duration-300 ${
                      agent.progress?.includes('Step 5/6') || agent.progress?.includes('baseline characteristics table') || agent.progress?.includes('Table 1')
                        ? 'text-pink-600 dark:text-pink-400'
                        : 'text-muted-foreground/60'
                    }`}>
                      Demographics
                    </div>
                    <div className="text-[8px] text-muted-foreground/50 mt-0.5">
                      Baseline summary
                    </div>
                  </div>
                </div>

                {/* Step 6: Survival Analysis */}
                <div className={`group relative flex flex-col items-center gap-2 p-2 rounded-lg transition-all duration-300 ${
                  agent.progress?.includes('Step 6/6') || agent.progress?.includes('Kaplan-Meier') || agent.progress?.includes('survival')
                    ? 'bg-amber-500/10 border border-amber-500/30 shadow-sm'
                    : 'bg-transparent border border-transparent'
                }`}>
                  <div className="relative flex-shrink-0">
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                      agent.progress?.includes('Step 6/6') || agent.progress?.includes('Kaplan-Meier') || agent.progress?.includes('survival')
                        ? 'border-amber-500 bg-amber-500/20'
                        : 'border-muted-foreground/30 bg-muted/30'
                    }`}>
                      {agent.progress?.includes('Step 6/6') || agent.progress?.includes('Kaplan-Meier') || agent.progress?.includes('survival') ? (
                        <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                      ) : (
                        <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
                      )}
                    </div>
                  </div>
                  <div className="flex-1 text-center">
                    <div className={`text-[9px] font-medium transition-colors duration-300 ${
                      agent.progress?.includes('Step 6/6') || agent.progress?.includes('Kaplan-Meier') || agent.progress?.includes('survival')
                        ? 'text-amber-600 dark:text-amber-400'
                        : 'text-muted-foreground/60'
                    }`}>
                      Survival Analysis
                    </div>
                    <div className="text-[8px] text-muted-foreground/50 mt-0.5">
                      KM + Cox
                    </div>
                  </div>
                </div>

                {/* Causal Forest (Bonus Step) */}
                <div className={`group relative flex flex-col items-center gap-2 p-2 rounded-lg transition-all duration-300 ${
                  agent.progress?.includes('Causal Forest') || agent.progress?.includes('treatment effect heterogeneity')
                    ? 'bg-teal-500/10 border border-teal-500/30 shadow-sm'
                    : 'bg-transparent border border-transparent'
                }`}>
                  <div className="relative flex-shrink-0">
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                      agent.progress?.includes('Causal Forest') || agent.progress?.includes('treatment effect heterogeneity')
                        ? 'border-teal-500 bg-teal-500/20'
                        : 'border-muted-foreground/30 bg-muted/30'
                    }`}>
                      {agent.progress?.includes('Causal Forest') || agent.progress?.includes('treatment effect heterogeneity') ? (
                        <div className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
                      ) : (
                        <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
                      )}
                    </div>
                  </div>
                  <div className="flex-1 text-center">
                    <div className={`text-[9px] font-medium transition-colors duration-300 ${
                      agent.progress?.includes('Causal Forest') || agent.progress?.includes('treatment effect heterogeneity')
                        ? 'text-teal-600 dark:text-teal-400'
                        : 'text-muted-foreground/60'
                    }`}>
                      Causal Forest
                    </div>
                    <div className="text-[8px] text-muted-foreground/50 mt-0.5">
                      HTE analysis
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {agent.error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 space-y-3">
            <div className="flex items-start gap-3">
              <XCircle className="h-5 w-5 text-destructive mt-0.5" />
              <div className="flex-1 space-y-2">
                <div className="font-semibold text-destructive">Agent Execution Failed</div>
                <p className="text-sm text-destructive/90">{agent.error}</p>
                {agent.jobId && (
                  <div className="text-xs text-destructive/70 font-mono">
                    Failed Job ID: {agent.jobId}
                  </div>
                )}
              </div>
            </div>

            {/* Troubleshooting Tips */}
            <div className="rounded-lg bg-destructive/5 border border-destructive/20 p-3">
              <div className="text-xs font-semibold text-destructive/80 mb-2">
                💡 Troubleshooting Tips:
              </div>
              <ul className="space-y-1 text-xs text-destructive/70">
                <li>• Check if cohort data exists for this NCT ID and medication</li>
                <li>• Verify backend server is running (localhost:8000)</li>
                <li>• Review backend logs for detailed error messages</li>
                <li>• Try running the analysis again (temporary API issue)</li>
              </ul>
            </div>

            {/* Reset Button */}
            <Button
              onClick={agent.reset}
              variant="outline"
              size="sm"
              className="w-full"
            >
              Clear Error and Retry
            </Button>
          </div>
        )}

        {/* Results Preview */}
        {agent.result && agent.status === AgentStatus.COMPLETED && (
          <div className="space-y-4">
            {/* Success Banner */}
            <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
                <div className="flex-1">
                  <div className="font-semibold text-green-700 dark:text-green-400">
                    Analysis Completed Successfully
                  </div>
                  <div className="text-sm text-green-600/80 dark:text-green-400/70 mt-1">
                    PSM + Survival Analysis finished. Results are ready for review.
                  </div>
                  {agent.jobId && (
                    <div className="text-xs text-green-600/60 dark:text-green-400/50 mt-1 font-mono">
                      Completed Job ID: {agent.jobId}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-foreground">Analysis Results</h4>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
              >
                {isExpanded ? 'Hide' : 'Show'} Details
              </Button>
            </div>

            {isExpanded && agent.result && (
              <div className="space-y-6">
                {/* DEBUG: Log agent.result structure */}
                {console.log('[StatisticianPanel] agent.result:', agent.result)}
                {console.log('[StatisticianPanel] agent.result.output:', agent.result.output)}
                
                {/* NEW: Method Comparison Viewer */}
                {agent.result.output?.method_comparisons && agent.result.output.method_comparisons.length > 0 && (
                  <MethodComparisonViewer
                    methodComparisons={agent.result.output.method_comparisons}
                    selectedMethod={agent.result.output.selected_method || 'psm'}
                    methodReasoning={agent.result.output.method_reasoning || 'No reasoning available'}
                  />
                )}

                {/* TELOS Style Results Viewer */}
                {agent.result.output.cohort_summary && agent.result.output.psm_results?.main_analysis && (
                  <PSMTELOSViewer
                    cohortSummary={agent.result.output.cohort_summary}
                    psmResults={{
                      ...agent.result.output.psm_results,
                      balance: agent.result.output.baseline_imbalance ? {
                        n_variables: agent.result.output.baseline_imbalance.total_variables,
                        n_balanced: agent.result.output.baseline_imbalance.total_variables - agent.result.output.baseline_imbalance.imbalanced_vars,
                        max_smd: agent.result.output.baseline_imbalance.max_smd
                      } : undefined
                    }}
                    nctId={nctId}
                    medication={medication}
                  />
                )}

                {/* New Visualizations Viewer */}
                {agent.result.output.visualizations && agent.result.output_dir && (
                  <StatisticianResultsViewer
                    output={agent.result.output}
                    outputDir={agent.result.output_dir}
                  />
                )}
              </div>
            )}

            {/* Causal Forest Results (if available) */}
            {agent.result?.metadata?.summary?.causal_forest && (
              <div className="mt-6">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    🌲 Causal Forest Analysis
                    <Badge variant="outline" className="text-xs">
                      Heterogeneous Treatment Effects
                    </Badge>
                  </h4>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsCausalForestExpanded(!isCausalForestExpanded)}
                  >
                    {isCausalForestExpanded ? 'Hide' : 'Show'} Details
                  </Button>
                </div>
                {isCausalForestExpanded && (
                  <CausalForestViewer
                    summary={agent.result.metadata.summary}
                    cateValues={cateValues}
                  />
                )}
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          {!agent.isRunning ? (
            <Button
              onClick={handleRun}
              disabled={!nctId || !medication}
              className="w-full"
            >
              <PlayCircle className="h-4 w-4 mr-2" />
              Run Statistician Agent
            </Button>
          ) : (
            <Button
              onClick={agent.cancelAgent}
              variant="destructive"
              className="w-full"
            >
              <XCircle className="h-4 w-4 mr-2" />
              Cancel
            </Button>
          )}
        </div>

      </CardContent>
    </Card>
  );
}
