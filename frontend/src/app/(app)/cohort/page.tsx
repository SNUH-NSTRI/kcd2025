'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { StepActions } from '@/features/flow/components/step-actions';
import { RequiredStepGuard } from '@/features/flow/components/required-step-guard';
import { useFlow, useSearchState } from '@/features/flow/context';
import { CohortWorkspace } from '@/features/cohort/components/cohort-workspace';
import { CohortDemoView } from '@/features/cohort/components/cohort-demo-view';
import { ARTICLES } from '@/features/search/lib/articles';
import type { Article } from '@/features/search/types';
import { Loader2 } from 'lucide-react';

function resolveSelectedArticles(ids: string[]): Article[] {
  const lookup = new Set(ids);
  return ARTICLES.filter((article) => lookup.has(article.id));
}

function CohortPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    state,
    markDone,
    activatePrebuiltDemo,
  } = useFlow();
  const searchState = useSearchState();
  const [isDemoSimulating, setIsDemoSimulating] = useState(false);
  const [isLoadingDemo, setIsLoadingDemo] = useState(false);

  // Auto-load demo data if in demo mode but cohort not loaded
  // DISABLED: This causes infinite loop when backend is not available
  // useEffect(() => {
  //   const cohortState = state.mode === 'demo' && 'cohort' in state ? state.cohort : null;
  //   const hasCohortData = cohortState?.result !== null && cohortState?.result !== undefined;

  //   if (state.mode === 'demo' && !hasCohortData && !isLoadingDemo) {
  //     setIsLoadingDemo(true);
  //     (async () => {
  //       await activatePrebuiltDemo();
  //       setIsLoadingDemo(false);
  //     })();
  //   }
  // }, [state.mode, activatePrebuiltDemo, isLoadingDemo, state]);

  // Demo Mode: Auto-progress simulation (disabled for manual navigation)
  // useEffect(() => {
  //   const mode = searchParams.get('mode');
  //   if (mode === 'demo' && state.mode === 'demo' && !isDemoSimulating) {
  //     simulateDemoCohort();
  //   }
  //   // eslint-disable-next-line react-hooks/exhaustive-deps
  // }, [searchParams, state.mode]);

  const simulateDemoCohort = async () => {
    setIsDemoSimulating(true);

    // Simulate 1 second loading for cohort extraction
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Mark cohort step as complete
    markDone('cohort');

    // Navigate to analysis page with demo mode
    router.push('/analysis?mode=demo');
  };

  const { steps } = state;
  const status = steps.cohort;

  const selectedArticles = useMemo(
    () => resolveSelectedArticles(searchState.selectedArticleIds),
    [searchState.selectedArticleIds],
  );

  const selectionCount = selectedArticles.length;

  // Demo Mode loading UI (after all hooks)
  if (isDemoSimulating || isLoadingDemo) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <div className="text-center">
          <p className="text-lg font-medium text-foreground">Loading demo cohort data...</p>
          <p className="text-sm text-muted-foreground">Fetching real patient data from MIMIC-IV database</p>
        </div>
      </div>
    );
  }

  return (
    <RequiredStepGuard step="cohort">
      <section className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">Step 3</p>
        <h2 className="text-3xl font-heading font-bold text-foreground">Cohort Selection</h2>
        <p className="text-base text-muted-foreground">
          Review cohort demographics and baseline characteristics. Examine attrition funnel to understand patient inclusion/exclusion process before proceeding to analytics.
        </p>
        <p className="text-sm font-medium text-primary">
          Current status: <span className="capitalize">{status}</span>
        </p>
        {state.mode !== 'demo' && (
          <p className="text-sm text-muted-foreground">
            Seeded from {selectionCount} selected article{selectionCount === 1 ? '' : 's'}.
          </p>
        )}
      </header>

      {/* Demo mode: show pre-computed summary */}
      {state.mode === 'demo' ? (
        <CohortDemoView nctId="NCT03389555" />
      ) : selectionCount === 0 ? (
        <div className="space-y-4 rounded-lg border border-dashed border-border/70 bg-card/40 p-6 text-sm text-muted-foreground">
          <p>No literature has been selected. Choose studies and finalise the schema before generating cohorts.</p>
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" size="sm">
              <Link href="/search">Return to literature search</Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href="/schema">Open schema workspace</Link>
            </Button>
          </div>
        </div>
      ) : (
        <CohortWorkspace />
      )}

      <StepActions step="cohort" />
      </section>
    </RequiredStepGuard>
  );
}

export default function CohortPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-[60vh] flex-col items-center justify-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    }>
      <CohortPageContent />
    </Suspense>
  );
}
