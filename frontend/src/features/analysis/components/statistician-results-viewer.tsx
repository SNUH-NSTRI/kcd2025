/**
 * Statistician Agent Results Viewer
 *
 * Renders statistical visualizations (plots, tables) in a single linear flow:
 * Baseline Characteristics → Love Plot (PSM Quality) → Survival Analysis
 *
 * Note: Execution order (PSM → Baseline → Survival) differs from display order
 * for better presentation clarity.
 */
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { FileText, Maximize, BarChart2, HeartPulse, AlertTriangle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { StatisticianOutput } from '@/remote';

interface StatisticianResultsViewerProps {
  output: StatisticianOutput;
  outputDir: string;
}

/**
 * Constructs the URL to fetch a static artifact from the backend.
 * Uses the `/api/workspace/outputs` endpoint that serves files based on a path query param.
 * Adds timestamp to prevent browser caching.
 */
function getArtifactUrl(outputDir: string, filename: string): string {
  const fullPath = `${outputDir}/${filename}`;
  const timestamp = Date.now();
  return `/api/workspace/outputs?path=${encodeURIComponent(fullPath)}&t=${timestamp}`;
}

/**
 * A simple placeholder component for failed image loads
 */
function ImagePlaceholder({ title }: { title: string }) {
  return (
    <div className="w-full h-48 flex flex-col items-center justify-center bg-muted/50 rounded-md border border-dashed">
      <AlertTriangle className="h-8 w-8 text-muted-foreground/50" />
      <p className="mt-2 text-sm text-muted-foreground">Could not load: {title}</p>
    </div>
  );
}

/**
 * A card component for displaying an image that can be expanded in a modal.
 */
function ImageCard({ title, description, imageUrl }: { title: string; description: string; imageUrl: string }) {
  const [hasError, setHasError] = useState(false);

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          {title === 'Kaplan-Meier Survival Curve' ? <HeartPulse className="h-5 w-5 text-primary" /> : <BarChart2 className="h-5 w-5 text-primary" />}
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {hasError ? (
          <ImagePlaceholder title={title} />
        ) : (
          <Dialog>
            <DialogTrigger asChild>
              <div className="relative group cursor-pointer">
                <img
                  src={imageUrl}
                  alt={title}
                  className="w-full h-auto rounded-md border border-border transition-all group-hover:opacity-80"
                  onError={() => setHasError(true)}
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-md">
                  <Maximize className="h-8 w-8 text-white" />
                </div>
              </div>
            </DialogTrigger>
            <DialogContent className="max-w-4xl">
              <DialogHeader>
                <DialogTitle>{title}</DialogTitle>
              </DialogHeader>
              <div className="py-4">
                <img src={imageUrl} alt={title} className="w-full h-auto rounded-md" />
              </div>
            </DialogContent>
          </Dialog>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * A card component for fetching and displaying a Markdown file in a collapsible section.
 */
function MarkdownCard({ title, description, markdownUrl }: { title: string; description: string; markdownUrl: string }) {
  const [content, setContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMarkdown = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(markdownUrl);
        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.statusText}`);
        }
        const text = await response.text();
        setContent(text);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setIsLoading(false);
      }
    };
    fetchMarkdown();
  }, [markdownUrl]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Accordion type="single" collapsible>
          <AccordionItem value="item-1">
            <AccordionTrigger>Show Baseline Characteristics</AccordionTrigger>
            <AccordionContent>
              {isLoading && <Skeleton className="h-64 w-full" />}
              {error && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Error loading table</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              {content && (
                <div className="prose prose-sm dark:prose-invert max-w-none max-h-96 overflow-y-auto rounded-md border border-border p-4">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                </div>
              )}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </CardContent>
    </Card>
  );
}

export function StatisticianResultsViewer({ output, outputDir }: StatisticianResultsViewerProps) {
  if (!output.visualizations) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Missing Visualization Data</AlertTitle>
        <AlertDescription>
          The agent result does not contain the necessary visualization file paths.
        </AlertDescription>
      </Alert>
    );
  }

  const { llm_summary } = output;

  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-8 max-h-[800px] overflow-y-auto">
      {/* LLM Summary Section - Question, Conclusion, PICO */}
      {llm_summary && (llm_summary.question || llm_summary.conclusion) && (
        <div className="space-y-4 pb-6 border-b border-border">
          {/* Question & Conclusion */}
          <div className="space-y-3">
            {llm_summary.question && (
              <div className="text-base">
                <span className="font-semibold text-muted-foreground uppercase tracking-wide text-sm">Question: </span>
                <span className="text-foreground">{llm_summary.question}</span>
              </div>
            )}
            {llm_summary.conclusion && (
              <div className="text-base">
                <span className="font-semibold text-primary uppercase tracking-wide text-sm">Conclusion: </span>
                <span className="text-foreground font-medium">{llm_summary.conclusion}</span>
              </div>
            )}
          </div>

          {/* PICO Grid (3 columns) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            {/* Population */}
            {llm_summary.population && (
              <Card className="bg-blue-50/50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2 text-blue-700 dark:text-blue-400">
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
                      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
                      </svg>
                    </div>
                    POPULATION
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="font-semibold text-2xl text-blue-900 dark:text-blue-300">
                    {llm_summary.population.total_patients.toLocaleString()} <span className="text-xs font-normal text-muted-foreground">total patients</span>
                  </div>
                  <div className="text-muted-foreground space-y-1">
                    <div><span className="font-medium text-foreground">{llm_summary.population.treatment_n}</span> Treatment group</div>
                    <div><span className="font-medium text-foreground">{llm_summary.population.control_n}</span> Control group</div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">{llm_summary.population.description}</p>
                </CardContent>
              </Card>
            )}

            {/* Intervention */}
            {llm_summary.intervention && (
              <Card className="bg-purple-50/50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-800">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2 text-purple-700 dark:text-purple-400">
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-purple-100 dark:bg-purple-900">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                      </svg>
                    </div>
                    INTERVENTION
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div>
                    <div className="font-semibold text-purple-900 dark:text-purple-300 mb-1">
                      {llm_summary.intervention.treatment_group.split(':')[0] || 'Treatment group'}
                    </div>
                    <p className="text-xs text-muted-foreground">{llm_summary.intervention.treatment_group}</p>
                  </div>
                  <div>
                    <div className="font-semibold text-purple-900 dark:text-purple-300 mb-1">
                      {llm_summary.intervention.control_group.split(':')[0] || 'Control group'}
                    </div>
                    <p className="text-xs text-muted-foreground">{llm_summary.intervention.control_group}</p>
                  </div>
                  <div className="pt-2 border-t border-purple-200 dark:border-purple-800">
                    <div className="text-xs font-medium text-purple-700 dark:text-purple-400">Primary outcome:</div>
                    <div className="text-xs text-muted-foreground">{llm_summary.intervention.primary_outcome}</div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Findings */}
            {llm_summary.findings && (
              <Card className="bg-orange-50/50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-800">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2 text-orange-700 dark:text-orange-400">
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-orange-100 dark:bg-orange-900">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                    </div>
                    FINDINGS
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div>
                    <div className="text-xs text-muted-foreground">Cox Hazard Ratio</div>
                    <div className="font-bold text-2xl text-orange-900 dark:text-orange-300">{llm_summary.findings.cox_hazard_ratio.toFixed(3)}</div>
                    <div className="text-xs text-muted-foreground">95% CI [{llm_summary.findings.ci_95}]</div>
                  </div>
                  <div className="space-y-1 text-xs">
                    <div><span className="font-medium">P-value:</span> {llm_summary.findings.p_value.toFixed(4)}</div>
                    <div><span className="font-medium">Absolute risk difference:</span> {llm_summary.findings.absolute_risk_difference}</div>
                    <div><span className="font-medium">Hazard {llm_summary.findings.hazard_change.startsWith('+') ? 'increase' : 'decrease'}:</span> {llm_summary.findings.hazard_change}</div>
                  </div>
                  <div className="pt-2 mt-2 border-t border-orange-200 dark:border-orange-800">
                    <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                      llm_summary.findings.significance.toLowerCase().includes('not')
                        ? 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300'
                        : 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                    }`}>
                      {llm_summary.findings.significance.toLowerCase().includes('not') ? '⊗' : '✓'} {llm_summary.findings.significance}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Section 1: Baseline Characteristics Table */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-border">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-sm">
            1
          </div>
          <h3 className="text-lg font-semibold text-foreground">Baseline Characteristics</h3>
        </div>
        <MarkdownCard
          title="Baseline Characteristics (Table 1)"
          description="Patient characteristics before and after matching. Demographics, vitals, labs, severity scores, comorbidities, and organ support."
          markdownUrl={getArtifactUrl(outputDir, output.visualizations.baseline_table_main)}
        />
      </div>

      {/* Section 2: PSM Quality - Love Plot */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-border">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-sm">
            2
          </div>
          <h3 className="text-lg font-semibold text-foreground">Covariate Balance (Love Plot)</h3>
        </div>
        <ImageCard
          title="Covariate Balance (Love Plot)"
          description="Visual confirmation of successful matching. Standardized mean differences (SMD) closer to zero indicate better balance between treatment and control groups."
          imageUrl={getArtifactUrl(outputDir, output.visualizations.love_plot_main)}
        />
      </div>

      {/* Section 3: Survival Analysis */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-border">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-sm">
            3
          </div>
          <h3 className="text-lg font-semibold text-foreground">Survival Analysis</h3>
        </div>
        <ImageCard
          title="Kaplan-Meier Survival Curve"
          description="Treatment effect comparison between matched cohorts. Shows survival probability over time with log-rank test results."
          imageUrl={getArtifactUrl(outputDir, output.visualizations.kaplan_meier_main)}
        />
      </div>
    </div>
  );
}
