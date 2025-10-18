/**
 * Analysis Summary Card Component
 *
 * Displays LLM-generated summary of statistical analysis in PICO format
 * (Population, Intervention, Comparison, Outcome)
 */
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Users, FlaskConical, TrendingUp, AlertCircle } from 'lucide-react';

interface AnalysisSummaryProps {
  summary: {
    question?: string;
    conclusion?: string;
    population?: {
      total_patients: number;
      treatment_n: number;
      control_n: number;
      description: string;
    };
    intervention?: {
      treatment_group: string;
      control_group: string;
      primary_outcome: string;
    };
    findings?: {
      cox_hazard_ratio: number;
      ci_95: string;
      p_value: number;
      absolute_risk_difference: string;
      hazard_change: string;
      significance: string;
    };
  };
}

export function AnalysSummaryCard({ summary }: AnalysisSummaryProps) {
  if (!summary || (!summary.question && !summary.conclusion)) {
    return null;
  }

  const isSignificant = summary.findings?.significance && !summary.findings.significance.toLowerCase().includes('not');

  return (
    <div className="space-y-6">
      {/* Research Question & Conclusion */}
      <Card className="border-2 border-primary/20 bg-gradient-to-br from-background to-primary/5">
        <CardHeader>
          <div className="space-y-4">
            {summary.question && (
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Research Question
                </div>
                <p className="text-lg font-medium text-foreground leading-relaxed">
                  {summary.question}
                </p>
              </div>
            )}

            {summary.conclusion && (
              <>
                <Separator />
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-primary mb-2 flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    Key Finding
                  </div>
                  <p className="text-xl font-semibold text-foreground leading-relaxed">
                    {summary.conclusion}
                  </p>
                  {summary.findings && (
                    <Badge
                      variant={isSignificant ? 'default' : 'secondary'}
                      className="mt-3"
                    >
                      {isSignificant ? '✓ Statistically Significant' : '⊗ Not Statistically Significant'}
                    </Badge>
                  )}
                </div>
              </>
            )}
          </div>
        </CardHeader>
      </Card>

      {/* PICO Summary Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Population Card */}
        {summary.population && (
          <Card className="border-blue-200 dark:border-blue-800 bg-gradient-to-br from-blue-50/50 to-blue-100/30 dark:from-blue-950/20 dark:to-blue-900/10">
            <CardHeader>
              <CardTitle className="text-lg font-semibold flex items-center gap-2 text-blue-700 dark:text-blue-400">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
                  <Users className="h-5 w-5" />
                </div>
                Population
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Key Metrics */}
              <div className="flex items-baseline gap-2">
                <div className="text-4xl font-bold text-blue-900 dark:text-blue-300">
                  {summary.population.total_patients.toLocaleString()}
                </div>
                <div className="text-sm text-muted-foreground">patients</div>
              </div>

              {/* Group Breakdown */}
              <div className="space-y-2 text-sm">
                <div className="flex justify-between items-center p-2 rounded bg-blue-100/50 dark:bg-blue-900/30">
                  <span className="text-muted-foreground">Treatment</span>
                  <span className="font-semibold text-foreground">{summary.population.treatment_n.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center p-2 rounded bg-blue-100/50 dark:bg-blue-900/30">
                  <span className="text-muted-foreground">Control</span>
                  <span className="font-semibold text-foreground">{summary.population.control_n.toLocaleString()}</span>
                </div>
              </div>

              <Separator className="bg-blue-200 dark:bg-blue-800" />

              {/* Description */}
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400 mb-2">
                  Characteristics
                </div>
                <p className="text-sm text-foreground/80 leading-relaxed">
                  {summary.population.description}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Intervention Card */}
        {summary.intervention && (
          <Card className="border-purple-200 dark:border-purple-800 bg-gradient-to-br from-purple-50/50 to-purple-100/30 dark:from-purple-950/20 dark:to-purple-900/10">
            <CardHeader>
              <CardTitle className="text-lg font-semibold flex items-center gap-2 text-purple-700 dark:text-purple-400">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-purple-100 dark:bg-purple-900">
                  <FlaskConical className="h-5 w-5" />
                </div>
                Intervention
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Treatment Group */}
              <div className="p-3 rounded-lg bg-purple-100/50 dark:bg-purple-900/30 border border-purple-200 dark:border-purple-800">
                <div className="text-xs font-semibold uppercase tracking-wide text-purple-700 dark:text-purple-400 mb-1">
                  Treatment Group
                </div>
                <p className="text-sm font-medium text-foreground leading-relaxed">
                  {summary.intervention.treatment_group}
                </p>
              </div>

              {/* Control Group */}
              <div className="p-3 rounded-lg bg-purple-100/50 dark:bg-purple-900/30 border border-purple-200 dark:border-purple-800">
                <div className="text-xs font-semibold uppercase tracking-wide text-purple-700 dark:text-purple-400 mb-1">
                  Control Group
                </div>
                <p className="text-sm font-medium text-foreground leading-relaxed">
                  {summary.intervention.control_group}
                </p>
              </div>

              <Separator className="bg-purple-200 dark:bg-purple-800" />

              {/* Primary Outcome */}
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-purple-700 dark:text-purple-400 mb-2">
                  Primary Outcome
                </div>
                <p className="text-sm text-foreground/80 leading-relaxed">
                  {summary.intervention.primary_outcome}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Findings Card */}
        {summary.findings && (
          <Card className="border-orange-200 dark:border-orange-800 bg-gradient-to-br from-orange-50/50 to-orange-100/30 dark:from-orange-950/20 dark:to-orange-900/10">
            <CardHeader>
              <CardTitle className="text-lg font-semibold flex items-center gap-2 text-orange-700 dark:text-orange-400">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-orange-100 dark:bg-orange-900">
                  <TrendingUp className="h-5 w-5" />
                </div>
                Statistical Findings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Hazard Ratio */}
              <div className="text-center p-4 rounded-lg bg-orange-100/50 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-800">
                <div className="text-xs font-semibold uppercase tracking-wide text-orange-700 dark:text-orange-400 mb-1">
                  Cox Hazard Ratio
                </div>
                <div className="text-4xl font-bold text-orange-900 dark:text-orange-300">
                  {summary.findings.cox_hazard_ratio.toFixed(3)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  95% CI [{summary.findings.ci_95}]
                </div>
              </div>

              {/* Key Metrics */}
              <div className="space-y-2 text-sm">
                <div className="flex justify-between items-center p-2 rounded bg-orange-100/50 dark:bg-orange-900/30">
                  <span className="text-muted-foreground">P-value</span>
                  <span className="font-semibold text-foreground font-mono">{summary.findings.p_value.toFixed(4)}</span>
                </div>
                <div className="flex justify-between items-center p-2 rounded bg-orange-100/50 dark:bg-orange-900/30">
                  <span className="text-muted-foreground">Risk Difference</span>
                  <span className="font-semibold text-foreground">{summary.findings.absolute_risk_difference}</span>
                </div>
                <div className="flex justify-between items-center p-2 rounded bg-orange-100/50 dark:bg-orange-900/30">
                  <span className="text-muted-foreground">Hazard Change</span>
                  <span className="font-semibold text-foreground">{summary.findings.hazard_change}</span>
                </div>
              </div>

              <Separator className="bg-orange-200 dark:bg-orange-800" />

              {/* Significance Badge */}
              <div className="flex items-center justify-center">
                <Badge
                  variant={isSignificant ? 'default' : 'secondary'}
                  className="text-sm px-4 py-2"
                >
                  {isSignificant ? '✓' : '⊗'} {summary.findings.significance}
                </Badge>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Clinical Interpretation Alert */}
      {summary.findings && (
        <Card className="border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/20">
          <CardHeader>
            <CardTitle className="text-base font-semibold flex items-center gap-2 text-amber-700 dark:text-amber-400">
              <AlertCircle className="h-5 w-5" />
              Clinical Interpretation
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-foreground/80 leading-relaxed">
            {isSignificant ? (
              <p>
                The treatment showed a <strong>statistically significant effect</strong> on the primary outcome
                (p = {summary.findings.p_value.toFixed(4)}). The Cox hazard ratio of {summary.findings.cox_hazard_ratio.toFixed(3)} indicates
                a {summary.findings.hazard_change.startsWith('+') ? 'increased' : 'decreased'} hazard of {Math.abs(parseFloat(summary.findings.hazard_change))}%
                in the treatment group compared to control. The absolute risk difference was {summary.findings.absolute_risk_difference}.
              </p>
            ) : (
              <p>
                <strong>No statistically significant difference</strong> was observed between the treatment and control groups
                (p = {summary.findings.p_value.toFixed(4)}). The Cox hazard ratio of {summary.findings.cox_hazard_ratio.toFixed(3)}
                (95% CI [{summary.findings.ci_95}]) suggests a modest {summary.findings.hazard_change.startsWith('+') ? 'increase' : 'decrease'}
                of {Math.abs(parseFloat(summary.findings.hazard_change))}%, but this finding could be due to chance.
                Further studies with larger sample sizes may be warranted.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
