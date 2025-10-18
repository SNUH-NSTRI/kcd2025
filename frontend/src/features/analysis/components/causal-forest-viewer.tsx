'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

import type { AnalysisMetadata } from '@/features/flow/types';

interface CausalForestViewerProps {
  summary: AnalysisMetadata['summary'];
  cateValues?: number[];
}

/**
 * Histogram component for CATE distribution
 */
function CateHistogram({ cateValues }: { cateValues: number[] }) {
  const histogram = useMemo(() => {
    if (!cateValues || cateValues.length === 0) return [];

    const min = Math.min(...cateValues);
    const max = Math.max(...cateValues);
    const numBins = 20;
    const binWidth = (max - min) / numBins;

    const bins = Array.from({ length: numBins }, (_, i) => ({
      start: min + i * binWidth,
      end: min + (i + 1) * binWidth,
      count: 0,
      label: `${(min + i * binWidth).toFixed(2)} - ${(min + (i + 1) * binWidth).toFixed(2)}`,
    }));

    // Count values in each bin
    cateValues.forEach((value) => {
      const binIndex = Math.min(Math.floor((value - min) / binWidth), numBins - 1);
      bins[binIndex].count++;
    });

    return bins;
  }, [cateValues]);

  const maxCount = Math.max(...histogram.map((bin) => bin.count), 1);
  const width = 500;
  const height = 250;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-foreground">CATE Distribution</h4>
      <svg className="w-full" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="CATE Histogram">
        <rect x={0} y={0} width={width} height={height} fill="transparent" />

        {/* Y-axis */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={height - padding.bottom}
          stroke="hsl(var(--muted-foreground))"
          strokeWidth={1}
        />

        {/* X-axis */}
        <line
          x1={padding.left}
          y1={height - padding.bottom}
          x2={width - padding.right}
          y2={height - padding.bottom}
          stroke="hsl(var(--muted-foreground))"
          strokeWidth={1}
        />

        {/* Histogram bars */}
        {histogram.map((bin, i) => {
          const barWidth = chartWidth / histogram.length - 2;
          const barHeight = (bin.count / maxCount) * chartHeight;
          const x = padding.left + (i * chartWidth) / histogram.length + 1;
          const y = height - padding.bottom - barHeight;

          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                fill="hsl(var(--primary))"
                opacity={0.7}
                rx={2}
              />
              <title>{`${bin.label}: ${bin.count} patients`}</title>
            </g>
          );
        })}

        {/* Y-axis label */}
        <text
          x={padding.left - 35}
          y={height / 2}
          textAnchor="middle"
          transform={`rotate(-90 ${padding.left - 35} ${height / 2})`}
          className="text-xs fill-muted-foreground"
        >
          Frequency
        </text>

        {/* X-axis label */}
        <text
          x={width / 2}
          y={height - 10}
          textAnchor="middle"
          className="text-xs fill-muted-foreground"
        >
          CATE Value (Treatment Effect)
        </text>

        {/* Y-axis ticks */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = height - padding.bottom - ratio * chartHeight;
          const value = Math.round(maxCount * ratio);
          return (
            <g key={ratio}>
              <line
                x1={padding.left - 5}
                y1={y}
                x2={padding.left}
                y2={y}
                stroke="hsl(var(--muted-foreground))"
                strokeWidth={1}
              />
              <text
                x={padding.left - 10}
                y={y + 4}
                textAnchor="end"
                className="text-xs fill-muted-foreground"
              >
                {value}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="text-xs text-muted-foreground">
        Distribution of individualized treatment effects across all patients
      </p>
    </div>
  );
}

/**
 * Feature importance bar chart (horizontal)
 */
function FeatureImportanceChart({
  importances,
}: {
  importances: Array<{ feature: string; importance: number }>;
}) {
  const sortedImportances = useMemo(() => {
    return [...importances].sort((a, b) => b.importance - a.importance).slice(0, 10);
  }, [importances]);

  const maxImportance = Math.max(...sortedImportances.map((f) => f.importance), 0.01);
  const width = 500;
  const height = Math.max(200, sortedImportances.length * 30);
  const padding = { top: 20, right: 60, bottom: 30, left: 150 };

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const barHeight = chartHeight / sortedImportances.length - 4;

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-foreground">Feature Importances</h4>
      <svg className="w-full" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Feature Importance">
        <rect x={0} y={0} width={width} height={height} fill="transparent" />

        {/* Feature labels and bars */}
        {sortedImportances.map((item, i) => {
          const barWidth = (item.importance / maxImportance) * chartWidth;
          const y = padding.top + (i * chartHeight) / sortedImportances.length;

          return (
            <g key={item.feature}>
              {/* Feature label */}
              <text
                x={padding.left - 10}
                y={y + barHeight / 2 + 4}
                textAnchor="end"
                className="text-xs fill-foreground"
              >
                {item.feature}
              </text>

              {/* Bar */}
              <rect
                x={padding.left}
                y={y}
                width={barWidth}
                height={barHeight}
                fill="hsl(var(--primary))"
                opacity={0.8}
                rx={3}
              />

              {/* Value label */}
              <text
                x={padding.left + barWidth + 5}
                y={y + barHeight / 2 + 4}
                className="text-xs fill-muted-foreground"
              >
                {item.importance.toFixed(4)}
              </text>
            </g>
          );
        })}

        {/* X-axis */}
        <line
          x1={padding.left}
          y1={height - padding.bottom}
          x2={width - padding.right}
          y2={height - padding.bottom}
          stroke="hsl(var(--muted-foreground))"
          strokeWidth={1}
        />

        {/* X-axis label */}
        <text
          x={width / 2}
          y={height - 5}
          textAnchor="middle"
          className="text-xs fill-muted-foreground"
        >
          Importance (Impact on Treatment Effect Heterogeneity)
        </text>
      </svg>
      <p className="text-xs text-muted-foreground">
        Features that most explain variation in treatment effects across patients
      </p>
    </div>
  );
}

/**
 * Main Causal Forest Results Viewer
 */
export function CausalForestViewer({ summary, cateValues }: CausalForestViewerProps) {
  if (!summary) return null;

  const metrics = summary.causal_forest;
  const importances = summary.shapley?.top_features;

  if (!metrics) {
    return null;
  }

  const ate = metrics.ate ?? metrics.mean_cate;

  return (
    <Card className="border border-border/70 bg-card/80">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Causal Forest Analysis</CardTitle>
          <Badge variant="secondary" className="text-xs">
            Heterogeneous Treatment Effects
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          Personalized treatment effect estimates using econml CausalForestDML
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Summary Metrics */}
        <div className="grid grid-cols-2 gap-4 rounded-lg border border-border/50 bg-muted/20 p-4">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Average Treatment Effect (ATE)</p>
            <p className="text-lg font-semibold text-foreground">{ate.toFixed(4)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Mean CATE</p>
            <p className="text-lg font-semibold text-foreground">{metrics.mean_cate.toFixed(4)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">CATE Std Dev</p>
            <p className="text-lg font-semibold text-foreground">{metrics.cate_std.toFixed(4)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Positive Response Rate</p>
            <p className="text-lg font-semibold text-foreground">
              {(metrics.positive_response_rate * 100).toFixed(1)}%
            </p>
          </div>
          <div className="col-span-2 space-y-1">
            <p className="text-xs text-muted-foreground">CATE Range</p>
            <p className="text-base font-semibold text-foreground">
              [{metrics.cate_range[0].toFixed(4)}, {metrics.cate_range[1].toFixed(4)}]
            </p>
          </div>
        </div>

        {/* CATE Histogram */}
        {cateValues && cateValues.length > 0 && (
          <div className="rounded-lg border border-border/50 bg-background/50 p-4">
            <CateHistogram cateValues={cateValues} />
          </div>
        )}

        {/* Feature Importances */}
        {importances && importances.length > 0 && (
          <div className="rounded-lg border border-border/50 bg-background/50 p-4">
            <FeatureImportanceChart importances={importances} />
          </div>
        )}

        {/* Interpretation Guide */}
        <div className="space-y-2 rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-900 dark:bg-blue-950/20">
          <h5 className="text-sm font-semibold text-blue-900 dark:text-blue-100">
            📊 Interpretation Guide
          </h5>
          <ul className="space-y-1 text-xs text-blue-800 dark:text-blue-200">
            <li>
              <strong>ATE</strong>: Average treatment effect across all patients
            </li>
            <li>
              <strong>CATE</strong>: Individual treatment effects - shows who benefits more/less
            </li>
            <li>
              <strong>CATE Std Dev</strong>: Higher values indicate greater heterogeneity
            </li>
            <li>
              <strong>Positive Response Rate</strong>: % of patients predicted to benefit from
              treatment
            </li>
            <li>
              <strong>Feature Importances</strong>: Variables that explain treatment effect
              differences
            </li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
