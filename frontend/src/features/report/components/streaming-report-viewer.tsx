'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, FileText, StopCircle, AlertCircle } from 'lucide-react';
import { useReportStream } from '../hooks/use-report-stream';
import { AnalysSummaryCard } from './analysis-summary-card';
import { pollJobStatus } from '@/remote/api/agents';
import { StatisticianOutput } from '@/remote';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface StreamingReportViewerProps {
  nctId: string;
  medication: string;
  viewMode?: 'summary' | 'detailed';
}

export function StreamingReportViewer({ nctId, medication, viewMode = 'detailed' }: StreamingReportViewerProps) {
  const { content, isStreaming, isLoading, error, startStream, stopStream, reset } = useReportStream();
  const [statisticianData, setStatisticianData] = useState<StatisticianOutput | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [statsError, setStatsError] = useState<string | null>(null);

  // Fetch statistician results for summary view
  useEffect(() => {
    if (viewMode === 'summary') {
      loadStatisticianData();
    }
  }, [viewMode, nctId, medication]);

  const loadStatisticianData = async () => {
    setLoadingStats(true);
    setStatsError(null);

    try {
      console.log(`[Report] Fetching LLM summary for ${nctId} / ${medication}`);

      // Call backend API to generate summary from existing analysis
      const response = await fetch('/api/summary/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nct_id: nctId,
          medication: medication,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('[Report] Received summary from API:', data);

      // Set summary data
      if (data.summary) {
        setStatisticianData({
          llm_summary: data.summary,
        } as StatisticianOutput);
        setStatsError(null);
      } else {
        setStatsError('No summary data returned from API');
      }
    } catch (err) {
      console.error('[Report] Failed to load statistician data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load analysis data';

      if (errorMessage.includes('404') || errorMessage.includes('not found')) {
        setStatsError('Analysis results not found. Please run the Statistician analysis first in the Analysis page.');
      } else {
        setStatsError(errorMessage);
      }
    } finally {
      setLoadingStats(false);
    }
  };

  const handleGenerate = () => {
    startStream(nctId, medication);
  };

  const hasContent = content.length > 0;

  // Summary View
  if (viewMode === 'summary') {
    return (
      <div className="space-y-6">
        {loadingStats && (
          <Card>
            <CardContent className="py-12 text-center">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
              <p className="mt-4 text-sm text-muted-foreground">Loading statistical analysis...</p>
            </CardContent>
          </Card>
        )}

        {statsError && (
          <Card className="border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/20">
            <CardHeader>
              <CardTitle className="text-base font-semibold flex items-center gap-2 text-amber-700 dark:text-amber-400">
                <AlertCircle className="h-5 w-5" />
                Analysis Data Required
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-foreground/80">
              <p className="mb-3">{statsError}</p>
              <p className="text-xs text-muted-foreground">
                Navigate to the <strong>Analysis</strong> page and run the Statistician agent to generate the executive summary.
              </p>
            </CardContent>
          </Card>
        )}

        {statisticianData?.llm_summary && (
          <AnalysSummaryCard summary={statisticianData.llm_summary} />
        )}

        {!loadingStats && !statsError && !statisticianData && (
          <div className="rounded-lg border border-dashed border-border/70 bg-card/40 p-12 text-center">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 text-lg font-semibold">No Analysis Data Available</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Run the Statistician agent in the Analysis page to generate an executive summary.
            </p>
          </div>
        )}
      </div>
    );
  }

  // Detailed View (Original Report)
  return (
    <div className="space-y-6">
      {/* Action Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Comprehensive Report Generator
          </CardTitle>
          <CardDescription>
            {isStreaming
              ? 'Generating report with real-time streaming...'
              : hasContent
                ? 'Report generation complete'
                : 'Click Generate to create a comprehensive report with statistical analysis'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            {!isStreaming && !isLoading ? (
              <Button onClick={handleGenerate} className="gap-2">
                <FileText className="h-4 w-4" />
                {hasContent ? 'Regenerate Report' : 'Generate Report'}
              </Button>
            ) : (
              <Button onClick={stopStream} variant="destructive" className="gap-2">
                <StopCircle className="h-4 w-4" />
                Stop Generation
              </Button>
            )}

            {hasContent && !isStreaming && (
              <Button onClick={reset} variant="outline">
                Clear
              </Button>
            )}
          </div>

          {error && (
            <div className="mt-4 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600">
              <strong>Error:</strong> {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Report Content */}
      {(isLoading || isStreaming || hasContent) && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Clinical Trial Emulation Report</CardTitle>
              {(isLoading || isStreaming) && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {isLoading ? 'Initializing...' : 'Streaming...'}
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="prose prose-lg max-w-none dark:prose-invert">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Enhanced headings with better spacing and styling
                  h1: ({ node, ...props }) => (
                    <h1 className="text-4xl font-bold mb-6 mt-8 pb-4 border-b-2 border-primary/20 text-foreground" {...props} />
                  ),
                  h2: ({ node, ...props }) => (
                    <h2 className="text-3xl font-semibold mb-4 mt-8 text-foreground flex items-center gap-2" {...props} />
                  ),
                  h3: ({ node, ...props }) => (
                    <h3 className="text-2xl font-semibold mb-3 mt-6 text-foreground" {...props} />
                  ),
                  h4: ({ node, ...props }) => (
                    <h4 className="text-xl font-medium mb-2 mt-4 text-muted-foreground" {...props} />
                  ),

                  // Better paragraph spacing
                  p: ({ node, ...props }) => (
                    <p className="mb-4 leading-relaxed text-base text-foreground/90" {...props} />
                  ),

                  // Enhanced lists
                  ul: ({ node, ...props }) => (
                    <ul className="mb-4 ml-6 space-y-2 list-disc marker:text-primary" {...props} />
                  ),
                  ol: ({ node, ...props }) => (
                    <ol className="mb-4 ml-6 space-y-2 list-decimal marker:text-primary marker:font-semibold" {...props} />
                  ),
                  li: ({ node, ...props }) => (
                    <li className="leading-relaxed" {...props} />
                  ),

                  // Styled tables
                  table: ({ node, ...props }) => (
                    <div className="overflow-x-auto my-6 rounded-lg border border-border">
                      <table className="min-w-full divide-y divide-border" {...props} />
                    </div>
                  ),
                  thead: ({ node, ...props }) => (
                    <thead className="bg-muted/50" {...props} />
                  ),
                  th: ({ node, ...props }) => (
                    <th className="px-4 py-3 text-left text-sm font-semibold text-foreground" {...props} />
                  ),
                  td: ({ node, ...props }) => (
                    <td className="px-4 py-3 text-sm text-foreground/80 border-t border-border" {...props} />
                  ),

                  // Styled blockquotes
                  blockquote: ({ node, ...props }) => (
                    <blockquote className="border-l-4 border-primary/40 pl-4 my-4 italic text-muted-foreground bg-muted/30 py-2 rounded-r" {...props} />
                  ),

                  // Code blocks
                  pre: ({ node, ...props }) => (
                    <pre className="overflow-x-auto my-4 p-4 rounded-lg bg-muted/50 border border-border" {...props} />
                  ),
                  code: ({ node, inline, ...props }) => (
                    inline
                      ? <code className="px-1.5 py-0.5 rounded bg-muted/50 text-primary font-mono text-sm" {...props} />
                      : <code className="block overflow-x-auto font-mono text-sm" {...props} />
                  ),

                  // Horizontal rule
                  hr: ({ node, ...props }) => (
                    <hr className="my-8 border-t-2 border-border/50" {...props} />
                  ),

                  // Strong/Bold text
                  strong: ({ node, ...props }) => (
                    <strong className="font-semibold text-foreground" {...props} />
                  ),

                  // Links
                  a: ({ node, ...props }) => (
                    <a className="text-primary hover:underline font-medium" {...props} />
                  ),
                }}
              >
                {content}
              </ReactMarkdown>
              {isStreaming && (
                <span className="inline-block w-2 h-5 bg-primary animate-pulse ml-1 rounded-sm">|</span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!isLoading && !isStreaming && !hasContent && (
        <div className="rounded-lg border border-dashed border-border/70 bg-card/40 p-12 text-center">
          <FileText className="mx-auto h-12 w-12 text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-semibold">No Report Generated</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Click the &quot;Generate Report&quot; button above to create a comprehensive analysis report.
          </p>
        </div>
      )}
    </div>
  );
}
