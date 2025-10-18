'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { StepActions } from '@/features/flow/components/step-actions';
import { RequiredStepGuard } from '@/features/flow/components/required-step-guard';
import { useFlow, useSearchState } from '@/features/flow/context';
import { SchemaWorkspaceProvider } from '@/features/schema/context';
import { SchemaWorkspace } from '@/features/schema/components/schema-workspace';
import { SchemaDemoView } from '@/features/schema/components/schema-demo-view';
import { ARTICLES } from '@/features/search/lib/articles';
import type { Article } from '@/features/search/types';
import { Loader2 } from 'lucide-react';

function resolveSelectedArticles(ids: string[]): Article[] {
  const lookup = new Set(ids);
  return ARTICLES.filter((article) => lookup.has(article.id));
}

function SchemaPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    state,
    markDone,
  } = useFlow();
  const searchState = useSearchState();
  const [isDemoSimulating, setIsDemoSimulating] = useState(false);

  // Demo Mode: Auto-progress simulation (disabled for manual navigation)
  // useEffect(() => {
  //   const mode = searchParams.get('mode');
  //   if (mode === 'demo' && state.mode === 'demo' && !isDemoSimulating) {
  //     simulateDemoSchema();
  //   }
  //   // eslint-disable-next-line react-hooks/exhaustive-deps
  // }, [searchParams, state.mode]);

  const simulateDemoSchema = async () => {
    setIsDemoSimulating(true);

    // Simulate 0.5 second loading for schema extraction
    await new Promise(resolve => setTimeout(resolve, 500));

    // Mark schema step as complete
    markDone('schema');

    // Navigate to cohort page with demo mode
    router.push('/cohort?mode=demo');
  };

  const { steps } = state;
  const status = steps.schema;

  const selectedArticles = useMemo(
    () => resolveSelectedArticles(searchState.selectedArticleIds),
    [searchState.selectedArticleIds],
  );

  const selectionCount = selectedArticles.length;

  // Demo Mode loading UI (after all hooks)
  if (isDemoSimulating) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <div className="text-center">
          <p className="text-lg font-medium text-foreground">Parsing trial criteria...</p>
          <p className="text-sm text-muted-foreground">Loading pre-parsed schema for NCT03389555</p>
        </div>
      </div>
    );
  }

  return (
    <RequiredStepGuard step="schema">
      <section className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">
            Step 2
          </p>
        <h2 className="text-3xl font-heading font-bold text-foreground">
          Schema extraction workspace
        </h2>
        <p className="text-base text-muted-foreground">
          Transform curated literature into an executable trial schema. Review the auto-generated draft, adjust eligibility logic, and version changes before moving to cohort selection.
        </p>
        <p className="text-sm font-medium text-primary">
          Current status: <span className="capitalize">{status}</span>
        </p>
        <p className="text-sm text-muted-foreground">
          Seeded from {selectionCount} selected article{selectionCount === 1 ? '' : 's'}.
        </p>
      </header>

      {selectionCount === 0 ? (
        state.mode === 'demo' ? (
          <>
            <SchemaDemoView nctId="NCT03389555" />
            <div className="flex justify-end gap-3 pt-6">
              <Button
                size="lg"
                onClick={() => {
                  if (state.steps.schema !== 'done') {
                    markDone('schema');
                  }
                  router.push('/cohort');
                }}
                className="gap-2"
              >
                Next: Review Cohort
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Button>
            </div>
          </>
        ) : (
          <div className="space-y-4 rounded-lg border border-dashed border-border/70 bg-card/40 p-6 text-sm text-muted-foreground">
            <p>No literature has been selected. Choose at least one study in the search step to initialise the schema extractor.</p>
            <Button asChild variant="outline" size="sm" className="w-fit">
              <Link href="/search">Return to literature search</Link>
            </Button>
          </div>
        )
      ) : (
        <SchemaWorkspaceProvider selectedArticles={selectedArticles}>
          <SchemaWorkspace />
        </SchemaWorkspaceProvider>
      )}

      {state.mode !== 'demo' && <StepActions step="schema" />}
      </section>
    </RequiredStepGuard>
  );
}

export default function SchemaPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-[60vh] flex-col items-center justify-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    }>
      <SchemaPageContent />
    </Suspense>
  );
}
