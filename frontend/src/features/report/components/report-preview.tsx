'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { AnalysisChart, AnalysisTable, ReportData } from '@/features/flow/types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ReportPreviewProps {
  report: ReportData | null;
}

const SECTION_DEFS = [
  { id: 'abstract', label: 'Abstract' },
  { id: 'methods', label: 'Methods' },
  { id: 'cohort', label: 'Cohort overview' },
  { id: 'results', label: 'Results' },
  { id: 'discussion', label: 'Discussion' },
  { id: 'references', label: 'References' },
];

function AnalyticsTable({ table }: { table: AnalysisTable }) {
  return (
    <figure className="my-6 rounded-lg border border-border/70 bg-card/70">
      <figcaption className="border-b border-border/70 bg-muted/50 px-4 py-2 text-sm font-medium text-muted-foreground">
        Table: {table.title}
      </figcaption>
      <div className="overflow-x-auto">
        <table className="w-full whitespace-nowrap text-left text-xs">
          <thead className="bg-muted/40 text-muted-foreground">
            <tr>
              <th className="px-4 py-2">Label</th>
              {table.columns.map((column) => (
                <th key={column} className="px-4 py-2 capitalize">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row) => (
              <tr key={row.label} className="odd:bg-background">
                <th scope="row" className="px-4 py-2 font-medium text-foreground">
                  {row.label}
                </th>
                {table.columns.map((column) => (
                  <td key={`${row.label}-${column}`} className="px-4 py-2 text-foreground/90">
                    {String(row.values[column] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

function AnalyticsChartPlaceholder({ chart }: { chart: AnalysisChart }) {
  return (
    <figure className="my-6 rounded-lg border border-dashed border-border/70 bg-card/40 p-4">
      <div className="text-sm font-medium text-muted-foreground">{chart.title}</div>
      <p className="mt-2 text-xs text-muted-foreground">
        Placeholder preview. Review interactive visualisations within the analysis workspace for the full chart.
      </p>
      <figcaption className="mt-3 text-xs text-muted-foreground">
        Figure: {chart.title} — {chart.xLabel} vs {chart.yLabel}
      </figcaption>
    </figure>
  );
}

export function ReportPreview({ report }: ReportPreviewProps) {
  if (!report) {
    return (
      <div className="rounded-lg border border-dashed border-border/70 bg-card/40 p-6 text-sm text-muted-foreground">
        Generate the report draft to preview the assembled narrative, tables, and citations.
      </div>
    );
  }

  const { cohort, results } = report;
  const cohortSummary = cohort.summary;
  const analysis = results.analysis;

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="no-print">
        <Card className="sticky top-20 border border-border/70 bg-card/80">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Chapters</CardTitle>
            <p className="text-xs text-muted-foreground">Jump to a section to continue editing upstream artefacts.</p>
          </CardHeader>
          <CardContent>
            <nav aria-label="Report sections">
              <ol className="space-y-2 text-sm">
                {SECTION_DEFS.map((section) => (
                  <li key={section.id}>
                    <a
                      href={`#${section.id}`}
                      className="flex items-center gap-2 rounded-md px-2 py-1 text-muted-foreground transition hover:bg-muted/40 hover:text-foreground"
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60" aria-hidden />
                      {section.label}
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
          </CardContent>
        </Card>
      </aside>

      <article className="space-y-12 print:space-y-10" aria-label="Report preview" id="report-preview">
        <section
          id="cover"
          className="rounded-xl border border-border/70 bg-gradient-to-br from-primary/10 via-background to-background px-8 py-12 text-center shadow-sm print:border-none print:bg-white print:shadow-none"
        >
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">TrialSynth RWE Draft</p>
          <h1 className="mt-3 text-4xl font-heading font-bold text-foreground">{report.title}</h1>
          <p className="mt-4 text-base text-muted-foreground">
            {report.authors.join(' · ')}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Generated {new Date(report.createdAt).toLocaleString()}
          </p>
          {cohortSummary ? (
            <p className="mt-6 text-sm text-muted-foreground">
              Cohort n={cohortSummary.size} · Dataset {cohortSummary.datasetId.toUpperCase()} · Median age {cohortSummary.age.median}
            </p>
          ) : (
            <p className="mt-6 text-sm text-muted-foreground">Cohort synthesis pending</p>
          )}
        </section>

        <section
          id="table-of-contents"
          className="report-page-break rounded-lg border border-border/60 bg-card/70 p-6 print:border-none print:bg-white"
          aria-label="Table of contents"
        >
          <h2 className="text-lg font-semibold text-foreground">Table of contents</h2>
          <ol className="mt-4 space-y-2 text-sm text-muted-foreground">
            {SECTION_DEFS.map((section, index) => (
              <li key={section.id}>
                <a href={`#${section.id}`} className="hover:text-foreground">
                  {index + 1}. {section.label}
                </a>
              </li>
            ))}
          </ol>
        </section>

        <section id="abstract" className="report-section">
          <header className="mb-3 border-b border-border/60 pb-2">
            <h2 className="text-xl font-semibold text-foreground">Abstract</h2>
          </header>
          <div className="text-sm leading-relaxed prose prose-sm dark:prose-invert max-w-none prose-p:text-muted-foreground">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.abstract}
            </ReactMarkdown>
          </div>
        </section>

        <section id="methods" className="report-section">
          <header className="mb-3 border-b border-border/60 pb-2">
            <h2 className="text-xl font-semibold text-foreground">Methods</h2>
          </header>
          <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:text-muted-foreground">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.methods.narrative}
            </ReactMarkdown>
          </div>
          {report.methods.schema ? (
            <div className="mt-4 space-y-3 rounded-lg border border-border/70 bg-card/70 p-4 text-xs text-muted-foreground">
              <p><span className="font-semibold text-foreground">Objective:</span> {report.methods.schema.objective}</p>
              <p>
                <span className="font-semibold text-foreground">Eligibility:</span> {report.methods.schema.inclusionCriteria.length} inclusion · {report.methods.schema.exclusionCriteria.length} exclusion criteria
              </p>
              <p>
                <span className="font-semibold text-foreground">Covariates:</span> {report.methods.schema.variables.length} mapped variables
              </p>
              <p>
                <span className="font-semibold text-foreground">Outcomes:</span> {report.methods.schema.outcomes.map((outcome) => outcome.name).join(', ')}
              </p>
            </div>
          ) : null}
        </section>

        <section id="cohort" className="report-section">
          <header className="mb-3 border-b border-border/60 pb-2">
            <h2 className="text-xl font-semibold text-foreground">Cohort overview</h2>
          </header>
          <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:text-muted-foreground">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {cohort.narrative}
            </ReactMarkdown>
          </div>
          {cohort.keyMetrics.length > 0 ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {cohort.keyMetrics.map((metric) => (
                <div key={metric.label} className="rounded-md border border-border/60 bg-background/80 p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">{metric.label}</p>
                  <p className="text-lg font-semibold text-foreground">{metric.value}</p>
                </div>
              ))}
            </div>
          ) : null}
        </section>

        <section id="results" className="report-section">
          <header className="mb-3 border-b border-border/60 pb-2">
            <h2 className="text-xl font-semibold text-foreground">Results</h2>
          </header>
          <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:text-muted-foreground">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {results.narrative}
            </ReactMarkdown>
          </div>
          {results.keyFindings.length > 0 ? (
            <ul className="mt-4 list-disc space-y-2 pl-6 text-sm text-muted-foreground">
              {results.keyFindings.map((finding) => (
                <li key={finding}>{finding}</li>
              ))}
            </ul>
          ) : null}
          {analysis?.notes ? (
            <blockquote className="mt-5 border-l-2 border-primary/60 bg-primary/5 px-4 py-2 text-sm prose prose-sm dark:prose-invert max-w-none prose-p:text-muted-foreground">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {analysis.notes}
              </ReactMarkdown>
            </blockquote>
          ) : null}
          {analysis?.tables?.map((table) => (
            <AnalyticsTable key={table.id} table={table} />
          ))}
          {analysis?.charts?.map((chart) => (
            <AnalyticsChartPlaceholder key={chart.id} chart={chart} />
          ))}
        </section>

        <section id="discussion" className="report-section">
          <header className="mb-3 border-b border-border/60 pb-2">
            <h2 className="text-xl font-semibold text-foreground">Discussion</h2>
          </header>
          <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:text-muted-foreground">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.discussion}
            </ReactMarkdown>
          </div>
        </section>

        <section id="references" className="report-section report-page-break">
          <header className="mb-3 border-b border-border/60 pb-2">
            <h2 className="text-xl font-semibold text-foreground">References</h2>
          </header>
          <ol className="space-y-2 text-sm text-muted-foreground">
            {report.references.map((reference) => (
              <li key={reference}>{reference}</li>
            ))}
          </ol>
        </section>
      </article>
    </div>
  );
}
