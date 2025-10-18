/**
 * Method Comparison Viewer Component
 *
 * Displays comparison of multiple matching methods (PSM, PSM+caliper, Mahalanobis, IPTW)
 * with SMD metrics and LLM-based method selection reasoning.
 */

'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MarkdownContent } from '@/components/ui/markdown-content';
import { CheckCircle2, TrendingDown, Users } from 'lucide-react';

interface MethodComparisonData {
  method_name: string;
  n_matched: number;
  mean_smd: number;
  balanced_pct: number;
  smd_details?: Record<string, number>;
}

interface MethodComparisonViewerProps {
  methodComparisons: MethodComparisonData[];
  selectedMethod: string;
  methodReasoning: string;
}

export function MethodComparisonViewer({
  methodComparisons,
  selectedMethod,
  methodReasoning,
}: MethodComparisonViewerProps) {
  // Debug logging
  console.log('[MethodComparisonViewer] methodComparisons:', methodComparisons);
  console.log('[MethodComparisonViewer] selectedMethod:', selectedMethod);
  console.log('[MethodComparisonViewer] methodReasoning:', methodReasoning);
  
  if (!methodComparisons || methodComparisons.length === 0) {
    console.warn('[MethodComparisonViewer] No method comparisons data available');
    return null;
  }

  const methodLabels: Record<string, string> = {
    psm: 'PSM (No Caliper)',
    psm_caliper: 'PSM + Caliper (0.01)',
    mahalanobis: 'Mahalanobis Distance',
    iptw: 'IPTW',
  };

  const formatPercent = (value: number | null | undefined) => {
    if (value == null || isNaN(value)) return 'N/A';
    return `${(value * 100).toFixed(1)}%`;
  };
  
  const formatSMD = (value: number | null | undefined) => {
    if (value == null || isNaN(value)) return 'N/A';
    return value.toFixed(4);
  };

  // Sort methods by mean SMD (best first), handling null values
  const sortedMethods = [...methodComparisons].sort((a, b) => {
    const smdA = a.mean_smd ?? Infinity;
    const smdB = b.mean_smd ?? Infinity;
    return smdA - smdB;
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <TrendingDown className="h-5 w-5 text-blue-500" />
          Matching Method Comparison
        </CardTitle>
        <CardDescription>
          Comparison of 4 matching methods based on covariate balance (SMD)
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Comparison Table */}
        <div className="rounded-lg border">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Method</th>
                <th className="px-4 py-3 text-center font-medium">N Matched</th>
                <th className="px-4 py-3 text-center font-medium">Mean SMD</th>
                <th className="px-4 py-3 text-center font-medium">Balanced (%)</th>
                <th className="px-4 py-3 text-center font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {sortedMethods.map((method) => {
                const isSelected = method.method_name === selectedMethod;
                const isBestSMD = method.mean_smd != null && 
                                   sortedMethods[0].mean_smd != null &&
                                   method.mean_smd === sortedMethods[0].mean_smd;
                
                return (
                  <tr
                    key={method.method_name}
                    className={`${
                      isSelected ? 'bg-green-50 dark:bg-green-950/20' : 'hover:bg-muted/30'
                    } transition-colors`}
                  >
                    <td className="px-4 py-3 font-medium">
                      {methodLabels[method.method_name] || method.method_name}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Users className="h-4 w-4 text-muted-foreground" />
                        {method.n_matched.toLocaleString()}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-flex items-center gap-1 font-mono ${
                          method.mean_smd == null || isNaN(method.mean_smd)
                            ? 'text-muted-foreground'
                            : method.mean_smd < 0.1
                            ? 'text-green-600 dark:text-green-400'
                            : method.mean_smd < 0.2
                            ? 'text-yellow-600 dark:text-yellow-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {formatSMD(method.mean_smd)}
                        {isBestSMD && (
                          <TrendingDown className="h-3 w-3 text-green-500" />
                        )}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="font-medium">{formatPercent(method.balanced_pct)}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {isSelected && (
                        <Badge className="bg-green-500 text-white">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Selected
                        </Badge>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* LLM Reasoning */}
        {methodReasoning && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-800 p-4">
            <h4 className="text-sm font-semibold mb-3 text-blue-900 dark:text-blue-100">
              LLM Recommendation
            </h4>
            <MarkdownContent
              content={methodReasoning}
              className="text-sm text-blue-800 dark:text-blue-200 leading-relaxed"
            />
          </div>
        )}

        {/* Legend */}
        <div className="rounded-lg border bg-muted/30 p-4 text-xs space-y-2">
          <h4 className="font-semibold text-foreground">Metrics Explanation</h4>
          <ul className="space-y-1 text-muted-foreground">
            <li>
              <strong>Mean SMD:</strong> Average standardized mean difference across all covariates (lower is better, &lt;0.1 is excellent)
            </li>
            <li>
              <strong>Balanced (%):</strong> Percentage of covariates with SMD &lt; 0.1 (higher is better)
            </li>
            <li>
              <strong>N Matched:</strong> Number of matched pairs (or total subjects for IPTW)
            </li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
