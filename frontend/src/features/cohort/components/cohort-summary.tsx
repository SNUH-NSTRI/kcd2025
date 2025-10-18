'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { CohortResult } from '@/features/flow/types';

interface CohortSummaryProps {
  result: CohortResult | null;
}

function SummaryStat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-border/60 bg-background/60 p-3 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold text-foreground">{value}</p>
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function CohortSummary({ result }: CohortSummaryProps) {
  if (!result) {
    return (
      <Card className="border border-dashed border-border/70 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">Cohort summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Generate a cohort to see high-level demographics and dataset provenance.
          </p>
        </CardContent>
      </Card>
    );
  }

  const { summary } = result;
  const total = Math.max(1, summary.size);
  const histogram = summary.age.histogram;
  const maxBucket = histogram.reduce((acc, bucket) => Math.max(acc, bucket.count), 0) || 1;

  return (
    <Card className="border border-border/70 bg-card/80">
      <CardHeader>
        <CardTitle className="text-base">Cohort summary</CardTitle>
        <p className="text-xs text-muted-foreground">
          Generated {new Date(result.createdAt).toLocaleString()} · Seed {result.seed}
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-3 sm:grid-cols-4">
          <SummaryStat label="Participants" value={`${summary.size}`} hint={`Dataset: ${summary.datasetId}`} />
          <SummaryStat label="Mean age" value={`${summary.age.mean}`} hint={`Median ${summary.age.median}`} />
          <SummaryStat label="Female" value={`${Math.round(summary.sex.proportions.F * 100)}%`} hint={`${summary.sex.counts.F} people`} />
          <SummaryStat label="Male" value={`${Math.round(summary.sex.proportions.M * 100)}%`} hint={`${summary.sex.counts.M} people`} />
        </div>

        <div>
          <p className="text-sm font-medium text-foreground">Age distribution</p>
          {histogram.length === 0 ? (
            <p className="text-xs text-muted-foreground">No age data available.</p>
          ) : (
            <svg className="mt-3 h-32 w-full" role="img" aria-label="Age histogram">
              {histogram.map((bucket, index) => {
                const barWidth = 100 / histogram.length;
                const height = (bucket.count / maxBucket) * 100;
                return (
                  <g key={bucket.label} transform={`translate(${index * barWidth}%, ${100 - height}%)`}>
                    <rect
                      width={`${barWidth - 2}%`}
                      height={`${height}%`}
                      fill="hsl(var(--primary))"
                      rx={4}
                    />
                    <text
                      x={`${(barWidth - 2) / 2}%`}
                      y="-4"
                      textAnchor="middle"
                      className="text-[10px] fill-muted-foreground"
                    >
                      {bucket.count}
                    </text>
                    <text
                      x={`${(barWidth - 2) / 2}%`}
                      y="110%"
                      textAnchor="middle"
                      className="text-[10px] fill-muted-foreground"
                    >
                      {bucket.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}
        </div>

        <div className="rounded-md border border-border/60 bg-background/60 p-3 text-xs text-muted-foreground">
          <p>
            Female ratio {(summary.sex.proportions.F * 100).toFixed(1)}% · Male ratio {(summary.sex.proportions.M * 100).toFixed(1)}%
          </p>
          <p>
            Age range {summary.age.min} – {summary.age.max}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
