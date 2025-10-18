'use client';

import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { AnalysisRunResult, AnalysisChart, AnalysisTable } from '@/features/flow/types';
import { CausalForestViewer } from './causal-forest-viewer';

interface ResultViewerProps {
  result: AnalysisRunResult | null;
}

function TableView({ table }: { table: AnalysisTable }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-border/60 text-sm">
        <thead className="bg-muted/40">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-muted-foreground">Metric</th>
            {table.columns.map((column) => (
              <th key={column} className="px-4 py-2 text-left font-medium text-muted-foreground">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60 bg-background/80">
          {table.rows.map((row) => (
            <tr key={row.label}>
              <td className="px-4 py-2 font-medium text-foreground">{row.label}</td>
              {table.columns.map((column) => (
                <td key={column} className="px-4 py-2 text-muted-foreground">
                  {row.values[column] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function computeBounds(chart: AnalysisChart) {
  const points = chart.series.flatMap((series) => series.points);
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const lowers = points
    .map((point) => point.lower)
    .filter((value): value is number => typeof value === 'number');
  const uppers = points
    .map((point) => point.upper)
    .filter((value): value is number => typeof value === 'number');

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys, ...(lowers.length ? lowers : [Number.POSITIVE_INFINITY]));
  const maxY = Math.max(...ys, ...(uppers.length ? uppers : [Number.NEGATIVE_INFINITY]));

  return {
    minX,
    maxX,
    minY: Number.isFinite(minY) ? minY : 0,
    maxY: Number.isFinite(maxY) ? maxY : 1,
  };
}

function LineChart({ chart }: { chart: AnalysisChart }) {
  const { minX, maxX, minY, maxY } = useMemo(() => computeBounds(chart), [chart]);
  const width = 420;
  const height = 220;
  const padding = 32;
  const scaleX = (value: number) => {
    if (maxX === minX) return padding;
    return padding + ((value - minX) / (maxX - minX)) * (width - padding * 2);
  };
  const scaleY = (value: number) => {
    if (maxY === minY) return height / 2;
    return height - padding - ((value - minY) / (maxY - minY)) * (height - padding * 2);
  };

  return (
    <svg className="w-full" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={chart.title}>
      <rect x={0} y={0} width={width} height={height} fill="transparent" />
      <line
        x1={padding}
        y1={height - padding}
        x2={width - padding}
        y2={height - padding}
        stroke="hsl(var(--muted-foreground))"
        strokeWidth={1}
      />
      <line
        x1={padding}
        y1={padding}
        x2={padding}
        y2={height - padding}
        stroke="hsl(var(--muted-foreground))"
        strokeWidth={1}
      />
      {chart.series.map((series, index) => {
        const color = `hsl(var(--primary) / ${0.7 - index * 0.15})`;
        const path = series.points
          .map((point, pointIndex) => {
            const x = scaleX(point.x);
            const y = scaleY(point.y);
            return `${pointIndex === 0 ? 'M' : 'L'} ${x} ${y}`;
          })
          .join(' ');
        return (
          <g key={series.id}>
            <path d={path} fill="none" stroke={color} strokeWidth={2} />
            {series.points.map((point) => {
              const x = scaleX(point.x);
              const y = scaleY(point.y);
              const lower = point.lower !== undefined ? scaleY(point.lower) : null;
              const upper = point.upper !== undefined ? scaleY(point.upper) : null;
              return (
                <g key={`${series.id}-${point.x}`}>
                  <circle cx={x} cy={y} r={3} fill={color} />
                  {lower !== null && upper !== null ? (
                    <line
                      x1={x}
                      x2={x}
                      y1={upper}
                      y2={lower}
                      stroke={color}
                      strokeWidth={2}
                    />
                  ) : null}
                </g>
              );
            })}
          </g>
        );
      })}
      <text x={width / 2} y={height - 4} textAnchor="middle" className="text-[10px] fill-muted-foreground">
        {chart.xLabel}
      </text>
      <text
        x={16}
        y={height / 2}
        textAnchor="middle"
        transform={`rotate(-90 16 ${height / 2})`}
        className="text-[10px] fill-muted-foreground"
      >
        {chart.yLabel}
      </text>
    </svg>
  );
}

function BarChart({ chart }: { chart: AnalysisChart }) {
  const width = 360;
  const height = 220;
  const padding = 32;
  const maxY = chart.series.reduce((acc, series) => {
    const candidate = Math.max(...series.points.map((point) => Math.abs(point.y)));
    return Math.max(acc, candidate);
  }, 0.1);

  const scaleY = (value: number) => {
    return height - padding - ((value + maxY) / (maxY * 2)) * (height - padding * 2);
  };

  const barWidth = (width - padding * 2) / Math.max(1, chart.series.length * 1.5);

  return (
    <svg className="w-full" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={chart.title}>
      <rect x={0} y={0} width={width} height={height} fill="transparent" />
      <line
        x1={padding}
        y1={height - padding}
        x2={width - padding}
        y2={height - padding}
        stroke="hsl(var(--muted-foreground))"
        strokeWidth={1}
      />
      {chart.series.map((series, index) => {
        const color = `hsl(var(--primary) / ${0.7 - index * 0.15})`;
        const point = series.points[0];
        if (!point) return null;
        const x = padding + index * (barWidth + 12);
        const y = scaleY(point.y);
        const zeroY = scaleY(0);
        const heightValue = zeroY - y;
        const lower = point.lower !== undefined ? scaleY(point.lower) : null;
        const upper = point.upper !== undefined ? scaleY(point.upper) : null;
        return (
          <g key={series.id}>
            <rect
              x={x}
              width={barWidth}
              y={heightValue >= 0 ? y : zeroY}
              height={Math.abs(heightValue)}
              fill={color}
              rx={6}
            />
            {lower !== null && upper !== null ? (
              <line
                x1={x + barWidth / 2}
                x2={x + barWidth / 2}
                y1={upper}
                y2={lower}
                stroke={color}
                strokeWidth={2}
              />
            ) : null}
          </g>
        );
      })}
      <text x={width / 2} y={height - 4} textAnchor="middle" className="text-[10px] fill-muted-foreground">
        {chart.xLabel}
      </text>
      <text
        x={16}
        y={height / 2}
        textAnchor="middle"
        transform={`rotate(-90 16 ${height / 2})`}
        className="text-[10px] fill-muted-foreground"
      >
        {chart.yLabel}
      </text>
    </svg>
  );
}

function ChartView({ chart }: { chart: AnalysisChart }) {
  if (chart.type === 'line') {
    return <LineChart chart={chart} />;
  }
  return <BarChart chart={chart} />;
}

export function ResultViewer({ result }: ResultViewerProps) {
  const [activeTab, setActiveTab] = useState<'tables' | 'charts' | 'causal-forest'>('tables');

  if (!result) {
    return (
      <Card className="border border-dashed border-border/70 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">Analysis results</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Run an analysis to see tables and charts here.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Handle both Agent results (with 'output') and Pipeline results (with 'tables'/'charts')
  const tables = result.tables || [];
  const charts = result.charts || [];
  const metadata = result.metadata || {};

  // Check if Causal Forest results are available
  const hasCausalForest =
    metadata?.summary?.causal_forest !== undefined ||
    metadata?.summary?.shapley?.top_features !== undefined;

  // Extract CATE values if available (handle both Agent and Pipeline formats)
  const cateValues = useMemo(() => {
    // Try result.outcomes first (Pipeline format)
    let outcomes = result.outcomes;

    // If not found, try result.output.outcomes (Agent format)
    if (!outcomes && (result as any).output?.outcomes) {
      outcomes = (result as any).output.outcomes;
    }

    if (outcomes && Array.isArray(outcomes)) {
      return outcomes
        .map((outcome: any) => outcome.cate_value)
        .filter((val: any): val is number => typeof val === 'number');
    }
    return [];
  }, [result]);

  return (
    <div className="space-y-4">
      <Card className="border border-border/70 bg-card/80">
        <CardHeader className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Analysis results</CardTitle>
            <div className="flex gap-2 text-xs">
              <ButtonTab
                label={`Tables (${tables.length})`}
                active={activeTab === 'tables'}
                onClick={() => setActiveTab('tables')}
              />
              <ButtonTab
                label={`Charts (${charts.length})`}
                active={activeTab === 'charts'}
                onClick={() => setActiveTab('charts')}
              />
              {hasCausalForest && (
                <ButtonTab
                  label="Causal Forest"
                  active={activeTab === 'causal-forest'}
                  onClick={() => setActiveTab('causal-forest')}
                />
              )}
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Completed {new Date(result.finishedAt).toLocaleString()} · Run ID {result.runId}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {activeTab === 'tables'
            ? tables.map((table) => (
                <section key={table.id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-foreground">{table.title}</h4>
                    <Badge variant="outline" className="text-xs">
                      Table
                    </Badge>
                  </div>
                  <TableView table={table} />
                </section>
              ))
            : activeTab === 'charts'
              ? charts.map((chart) => (
                  <section key={chart.id} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-foreground">{chart.title}</h4>
                      <Badge variant="outline" className="text-xs">
                        {chart.type === 'line' ? 'Line chart' : 'Bar chart'}
                      </Badge>
                    </div>
                    <ChartView chart={chart} />
                  </section>
                ))
              : null}
        </CardContent>
      </Card>

      {/* Causal Forest Viewer - shown as separate card */}
      {activeTab === 'causal-forest' && hasCausalForest && metadata?.summary && (
        <CausalForestViewer summary={metadata.summary} cateValues={cateValues} />
      )}
    </div>
  );
}

function ButtonTab({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium transition ${
        active ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
      }`}
    >
      {label}
    </button>
  );
}
