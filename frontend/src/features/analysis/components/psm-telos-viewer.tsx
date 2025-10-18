/**
 * PSM + Survival Analysis Results Viewer (TELOS Template Style)
 *
 * Displays PSM and Survival analysis results in a clean, visual format
 * inspired by TELOS medical trial summaries.
 */

'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle, XCircle, Users, Activity, TrendingUp } from 'lucide-react';

interface PSMTELOSViewerProps {
  cohortSummary: {
    total_patients: number;
    treatment_n: number;
    control_n: number;
    treatment_pct: number;
    matched_pairs?: number;
  };
  psmResults: {
    main_analysis: {
      n_treatment: number;
      n_control?: number;
      mortality_treatment: number;
      mortality_control: number;
      cox_hr: number;
      cox_ci_lower: number;
      cox_ci_upper: number;
      cox_pvalue: number;
    };
    balance?: {
      n_variables: number;
      n_balanced: number;
      max_smd: number;
    };
  };
  nctId?: string;
  medication?: string;
}

export function PSMTELOSViewer({
  cohortSummary,
  psmResults,
  nctId,
  medication
}: PSMTELOSViewerProps) {
  const isSignificant = psmResults.main_analysis.cox_pvalue < 0.05;
  const hr = psmResults.main_analysis.cox_hr;
  const isBeneficial = hr < 1 && isSignificant;
  const isHarmful = hr > 1 && isSignificant;

  // Calculate absolute risk reduction
  const arr = Math.abs(
    psmResults.main_analysis.mortality_treatment * 100 -
    psmResults.main_analysis.mortality_control * 100
  );

  return (
    <div className="space-y-6">
      {/* Header with Question and Conclusion */}
      <div className="rounded-lg border border-border bg-gradient-to-br from-blue-50/50 to-purple-50/50 dark:from-blue-950/20 dark:to-purple-950/20 p-6">
        <div className="space-y-4">
          <div className="border-l-4 border-blue-600 dark:border-blue-400 pl-4">
            <p className="text-lg font-semibold mb-2 leading-relaxed">
              <span className="text-muted-foreground">QUESTION:</span>{' '}
              <span className="font-normal text-foreground">
                {medication
                  ? `What is the effect of ${medication} on 28-day mortality in septic shock patients?`
                  : 'What is the treatment effect on mortality in this patient population?'}
              </span>
            </p>
            <p className="text-lg font-semibold leading-relaxed">
              <span className="text-blue-600 dark:text-blue-400">CONCLUSION:</span>{' '}
              <span className="font-normal text-foreground">
                {isBeneficial && (
                  `Treatment was associated with reduced mortality (HR ${hr.toFixed(2)}, p=${psmResults.main_analysis.cox_pvalue.toFixed(3)}).`
                )}
                {isHarmful && (
                  `Treatment was associated with increased mortality (HR ${hr.toFixed(2)}, p=${psmResults.main_analysis.cox_pvalue.toFixed(3)}).`
                )}
                {!isSignificant && (
                  `No significant difference in mortality was observed between treatment and control groups (p=${psmResults.main_analysis.cox_pvalue.toFixed(3)}).`
                )}
              </span>
            </p>
          </div>
          {nctId && (
            <div className="text-xs text-muted-foreground">
              Study: {nctId}
            </div>
          )}
        </div>
      </div>

      {/* Three Column Layout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Population */}
        <Card className="relative bg-card border-border shadow-sm">
          <div className="absolute -top-3 left-6 bg-blue-100 dark:bg-blue-900 p-2 rounded-full shadow-sm">
            <Users className="text-blue-600 dark:text-blue-400 w-4 h-4" />
          </div>
          <CardHeader>
            <CardTitle className="text-blue-700 dark:text-blue-400 uppercase text-sm tracking-wide border-b border-blue-100 dark:border-blue-900 pb-2">
              Population
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-3 leading-relaxed">
            <div className="bg-muted/50 rounded-lg p-3">
              <p className="font-semibold text-base">{cohortSummary.total_patients.toLocaleString()} total patients</p>
              <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                <p><span className="font-medium text-foreground">{cohortSummary.treatment_n.toLocaleString()}</span> Treatment group</p>
                <p><span className="font-medium text-foreground">{cohortSummary.control_n.toLocaleString()}</span> Control group</p>
              </div>
            </div>

            {cohortSummary.matched_pairs && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
                <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400">PSM Matched Pairs</p>
                <p className="text-xl font-bold text-emerald-700 dark:text-emerald-300 mt-1">
                  {cohortSummary.matched_pairs.toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {((cohortSummary.matched_pairs * 2 / cohortSummary.total_patients) * 100).toFixed(1)}% matching rate
                </p>
              </div>
            )}

            <p className="text-xs text-muted-foreground">
              Adults with septic shock requiring vasopressors
            </p>

            {psmResults.balance && (
              <div className="text-xs text-muted-foreground pt-2 border-t border-border">
                <p>Baseline balance: {psmResults.balance.n_balanced}/{psmResults.balance.n_variables} variables (SMD &lt; 0.1)</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Intervention */}
        <Card className="relative bg-card border-border shadow-sm">
          <div className="absolute -top-3 left-6 bg-purple-100 dark:bg-purple-900 p-2 rounded-full shadow-sm">
            <Activity className="text-purple-600 dark:text-purple-400 w-4 h-4" />
          </div>
          <CardHeader>
            <CardTitle className="text-purple-700 dark:text-purple-400 uppercase text-sm tracking-wide border-b border-purple-100 dark:border-purple-900 pb-2">
              Intervention
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-3 leading-relaxed">
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
              <p className="font-semibold text-blue-700 dark:text-blue-300">
                {psmResults.main_analysis.n_treatment.toLocaleString()} Treatment group
              </p>
              {medication && (
                <p className="text-xs text-muted-foreground mt-1">
                  Received {medication}
                </p>
              )}
              <div className="mt-3 pt-3 border-t border-blue-500/20">
                <p className="text-xs text-muted-foreground">28-day Mortality</p>
                <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                  {(psmResults.main_analysis.mortality_treatment * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            <div className="bg-muted/50 border border-border rounded-lg p-3">
              <p className="font-semibold text-foreground">
                {(psmResults.main_analysis.n_control || psmResults.main_analysis.n_treatment).toLocaleString()} Control group
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Standard care
              </p>
              <div className="mt-3 pt-3 border-t border-border">
                <p className="text-xs text-muted-foreground">28-day Mortality</p>
                <p className="text-2xl font-bold text-foreground">
                  {(psmResults.main_analysis.mortality_control * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              <strong>Primary outcome:</strong> 28-day all-cause mortality
            </p>
          </CardContent>
        </Card>

        {/* Findings */}
        <Card className="relative bg-card border-border shadow-sm">
          <div className="absolute -top-3 left-6 bg-amber-100 dark:bg-amber-900 p-2 rounded-full shadow-sm">
            <TrendingUp className="text-amber-600 dark:text-amber-400 w-4 h-4" />
          </div>
          <CardHeader>
            <CardTitle className="text-amber-700 dark:text-amber-400 uppercase text-sm tracking-wide border-b border-amber-100 dark:border-amber-900 pb-2">
              Findings
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-3 leading-relaxed">
            <div className="bg-muted/50 rounded-lg p-3">
              <p className="text-xs text-muted-foreground mb-2">Cox Hazard Ratio</p>
              <p className="text-3xl font-bold text-foreground">
                {psmResults.main_analysis.cox_hr.toFixed(3)}
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                95% CI [{psmResults.main_analysis.cox_ci_lower.toFixed(3)} - {psmResults.main_analysis.cox_ci_upper.toFixed(3)}]
              </p>
            </div>

            <div className={`rounded-lg p-3 border ${
              isSignificant
                ? 'bg-green-500/10 border-green-500/20'
                : 'bg-gray-500/10 border-gray-500/20'
            }`}>
              <p className="text-xs text-muted-foreground mb-1">P-value</p>
              <p className="text-2xl font-bold">
                {psmResults.main_analysis.cox_pvalue.toFixed(4)}
              </p>
            </div>

            <div className="text-xs text-muted-foreground border-l-4 border-blue-200 dark:border-blue-800 pl-3">
              <p>Absolute risk difference: {arr.toFixed(1)} percentage points</p>
              {hr < 1 && (
                <p className="mt-1">Hazard reduction: {((1 - hr) * 100).toFixed(1)}%</p>
              )}
              {hr > 1 && (
                <p className="mt-1">Hazard increase: {((hr - 1) * 100).toFixed(1)}%</p>
              )}
            </div>

            <div className="flex items-center gap-3 mt-4 pt-3 border-t border-border">
              {isSignificant ? (
                <CheckCircle className="text-green-500 w-5 h-5" />
              ) : (
                <XCircle className="text-gray-400 w-5 h-5" />
              )}
              <span className={`text-sm font-medium ${
                isSignificant
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-muted-foreground'
              }`}>
                {isSignificant ? 'Statistically significant' : 'Not statistically significant'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
