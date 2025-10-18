'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { StepActions } from '@/features/flow/components/step-actions';
import { RequiredStepGuard } from '@/features/flow/components/required-step-guard';
import { useFlow, useCohortState } from '@/features/flow/context';
import { AnalysisWorkspace } from '@/features/analysis/components/analysis-workspace';
import { StatisticianPanel } from '@/features/analysis/components/statistician-panel';
import { Loader2, AlertCircle, Search } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

function AnalysisPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    state,
    markDone,
  } = useFlow();
  const cohortState = useCohortState();
  const [isDemoSimulating, setIsDemoSimulating] = useState(false);

  // Get NCT ID and medication from URL params (from CT Search selection)
  const nctIdFromParams = searchParams.get('nctId');
  const medicationFromParams = searchParams.get('medication');

  // Demo Mode: Auto-progress simulation (DISABLED - use Next button instead)
  // useEffect(() => {
  //   const mode = searchParams.get('mode');
  //   if (mode === 'demo' && state.mode === 'demo' && !isDemoSimulating) {
  //     simulateDemoAnalysis();
  //   }
  //   // eslint-disable-next-line react-hooks/exhaustive-deps
  // }, [searchParams, state.mode]);

  const simulateDemoAnalysis = async () => {
    setIsDemoSimulating(true);

    // Simulate 2 seconds loading for statistical analysis
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Mark analysis step as complete
    markDone('analysis');

    // Navigate to report page with demo mode
    router.push('/report?mode=demo');
  };

  const { steps } = state;
  const status = steps.analysis;

  const cohortResult = cohortState.result;
  const cohortSummary = useMemo(
    () => (cohortResult ? cohortResult.summary : null),
    [cohortResult],
  );

  // Demo Mode loading UI (after all hooks)
  if (isDemoSimulating) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <div className="text-center">
          <p className="text-lg font-medium text-foreground">Running statistical analysis...</p>
          <p className="text-sm text-muted-foreground">Statistician plugin executing (IPTW, Cox PH, Causal Forest, Shapley)</p>
        </div>
      </div>
    );
  }

  // Check if we have required trial selection (not in demo mode)
  const hasTrialSelection = nctIdFromParams && medicationFromParams;
  const isDemoMode = state.mode === 'demo' && state.demoConfig?.nctId;

  return (
    <RequiredStepGuard step="analysis">
      <section className="space-y-8">
        <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-muted-foreground">Step 4</p>
        <h2 className="text-3xl font-heading font-bold text-foreground">Statistical analysis</h2>
        <p className="text-base text-muted-foreground">
          Execute reusable analysis templates to validate treatment effects and generate report-ready visuals. Track run history and compare outcomes before advancing to narrative reporting.
        </p>
        {(nctIdFromParams || medicationFromParams) && (
          <div className="flex items-center gap-3 rounded-md bg-primary/10 px-4 py-2 border border-primary/20">
            <span className="text-sm font-semibold text-primary">Selected Trial:</span>
            <span className="text-sm font-mono text-foreground">{nctIdFromParams || 'N/A'}</span>
            <span className="text-muted-foreground">•</span>
            <span className="text-sm font-medium text-foreground">{medicationFromParams || 'N/A'}</span>
          </div>
        )}
        <p className="text-sm font-medium text-primary">
          Current status: <span className="capitalize">{status}</span>
        </p>
        {cohortSummary && (
          <p className="text-sm text-muted-foreground">
            Using {cohortSummary.size.toLocaleString()} real patients from {cohortSummary.datasetId === 'mimic-iv' ? 'MIMIC-IV v3.1' : cohortSummary.datasetId}
          </p>
        )}
      </header>

      {/* Show empty state if no trial selected and not in demo mode */}
      {!hasTrialSelection && !isDemoMode ? (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>No Trial Selected</AlertTitle>
          <AlertDescription className="space-y-4">
            <p>
              You need to select a clinical trial and medication before running analysis.
            </p>
            <div className="flex gap-2">
              <Button asChild variant="default" size="sm">
                <Link href="/ct-search">
                  <Search className="h-4 w-4 mr-2" />
                  Search Clinical Trials
                </Link>
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      ) : (
        <>
          {/* Statistician Agent Panel - Only show when trial is selected or in demo mode */}
          <StatisticianPanel
            nctId={
              nctIdFromParams ||
              (state.mode === 'demo' && state.demoConfig?.nctId) ||
              ""
            }
            medication={
              medicationFromParams ||
              (state.mode === 'demo' && state.demoConfig?.study?.medicine) ||
              ""
            }
            onComplete={(result) => {
              if (state.steps.analysis !== 'done') {
                markDone('analysis');
              }
            }}
          />

          {/* Analysis Workspace */}
          <div className="space-y-6">
            {!cohortResult ? (
              <div className="space-y-4 rounded-lg border border-dashed border-border/70 bg-card/40 p-6 text-sm text-muted-foreground">
                <p>Generate a cohort before running analyses. Map schema variables and synthesise a cohort in the previous step.</p>
                <Button asChild variant="outline" size="sm" className="w-fit">
                  <Link href="/cohort">Open cohort workspace</Link>
                </Button>
              </div>
            ) : (
              <AnalysisWorkspace />
            )}
          </div>

          <StepActions step="analysis" />
        </>
      )}
      </section>
    </RequiredStepGuard>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-[60vh] flex-col items-center justify-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    }>
      <AnalysisPageContent />
    </Suspense>
  );
}
