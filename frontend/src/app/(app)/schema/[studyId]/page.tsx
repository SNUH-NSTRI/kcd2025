'use client';

import { Suspense, use } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { RequiredStepGuard } from '@/features/flow/components/required-step-guard';
import { useFlow } from '@/features/flow/context';
import { ParsingProgress } from '@/features/schema/components/parsing-progress';
import { OriginalTextPanel } from '@/features/schema/components/original-text-panel';
import { ParsedSchemaPanel } from '@/features/schema/components/parsed-schema-panel';
import { getStudyStatus, getStudyCorpus, getStudySchema, retryStudyParsing } from '@/remote';

interface SchemaPageProps {
  params: Promise<{ studyId: string }>;
}

function SchemaPageContent({ studyId }: { studyId: string }) {
  const router = useRouter();
  const { state, markDone } = useFlow();

  // Poll study status every 3 seconds
  const { data: status, isLoading: isLoadingStatus } = useQuery({
    queryKey: ['study-status', studyId],
    queryFn: () => getStudyStatus(studyId),
    refetchInterval: (query) => {
      // Stop polling if completed or failed
      const currentStatus = query.state.data?.overallStatus;
      if (currentStatus === 'completed' || currentStatus === 'failed') {
        return false;
      }
      return 3000; // 3 seconds
    },
    retry: 3,
  });

  // Load corpus (original text) - available immediately
  const { data: corpus, isLoading: isLoadingCorpus } = useQuery({
    queryKey: ['corpus', studyId],
    queryFn: () => getStudyCorpus(studyId),
    enabled: !!status && status.steps.some(s => s.step === 'corpus' && s.status === 'done'),
    retry: 3,
  });

  // Load schema - only when parsing is complete
  const { data: schema, isLoading: isLoadingSchema } = useQuery({
    queryKey: ['schema', studyId],
    queryFn: () => getStudySchema(studyId),
    enabled: status?.overallStatus === 'completed',
    retry: 3,
  });

  const handleRetry = async () => {
    try {
      await retryStudyParsing(studyId);
      // Refresh status query
      window.location.reload();
    } catch (error) {
      console.error('Failed to retry parsing:', error);
      alert('Failed to retry parsing. Please try again.');
    }
  };

  const handleNext = () => {
    if (state.steps.schema !== 'done') {
      markDone('schema');
    }
    router.push('/cohort');
  };

  if (isLoadingStatus) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <div className="text-center">
          <p className="text-lg font-medium text-foreground">Loading study...</p>
          <p className="text-sm text-muted-foreground">Study ID: {studyId}</p>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center space-y-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <div className="text-center">
          <p className="text-lg font-medium text-foreground">Study not found</p>
          <p className="text-sm text-muted-foreground">Study ID: {studyId}</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => router.push('/ct-search')}
          >
            Return to CT Search
          </Button>
        </div>
      </div>
    );
  }

  return (
    <RequiredStepGuard step="schema">
      <section className="space-y-6">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">
            Step 2
          </p>
          <h2 className="text-3xl font-heading font-bold text-foreground">
            Trial Schema Extraction
          </h2>
          <p className="text-base text-muted-foreground">
            AI-powered parsing of eligibility criteria into structured, executable format.
            Review original text alongside parsed results to verify accuracy.
          </p>
          <div className="flex items-center gap-3">
            <p className="text-sm font-medium text-primary">
              Status: <span className="capitalize">{status.overallStatus}</span>
            </p>
            <p className="text-xs text-muted-foreground">
              Study ID: {studyId}
            </p>
          </div>
        </header>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-[70vh]">
          {/* Left Panel: Original Text */}
          <div className="space-y-4">
            {isLoadingCorpus ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : corpus ? (
              <OriginalTextPanel corpus={corpus} />
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                Waiting for trial data...
              </div>
            )}
          </div>

          {/* Right Panel: Parsed Schema or Progress */}
          <div className="space-y-4">
            {status.overallStatus === 'completed' ? (
              isLoadingSchema ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : schema ? (
                <ParsedSchemaPanel schema={schema} />
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                  Loading schema data...
                </div>
              )
            ) : status.overallStatus === 'failed' ? (
              <div className="space-y-4">
                <ParsingProgress status={status} />
                <div className="flex gap-3">
                  <Button
                    variant="default"
                    onClick={handleRetry}
                    className="gap-2"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Retry Parsing
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => alert('Manual schema builder coming soon!')}
                  >
                    Build Schema Manually
                  </Button>
                </div>
              </div>
            ) : (
              <ParsingProgress status={status} />
            )}
          </div>
        </div>

        {/* Footer Actions */}
        {status.overallStatus === 'completed' && schema && (
          <div className="flex justify-end gap-3 pt-6 border-t">
            <Button
              variant="outline"
              onClick={() => router.push('/ct-search')}
            >
              Back to Search
            </Button>
            <Button
              size="lg"
              onClick={handleNext}
              className="gap-2"
            >
              Next: Review Cohort
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Button>
          </div>
        )}
      </section>
    </RequiredStepGuard>
  );
}

export default function SchemaPage({ params }: SchemaPageProps) {
  const { studyId } = use(params);

  return (
    <Suspense fallback={
      <div className="flex min-h-[60vh] flex-col items-center justify-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    }>
      <SchemaPageContent studyId={studyId} />
    </Suspense>
  );
}
