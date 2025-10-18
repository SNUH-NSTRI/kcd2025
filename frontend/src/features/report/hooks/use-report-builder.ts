'use client';

import { useCallback, useEffect, useMemo } from 'react';
import { buildReportData } from '@/features/report/lib/build-report';
import { useFlow } from '@/features/flow/context';
import { useAudit } from '@/features/audit';
import type { ReportData } from '@/features/flow/types';

function getLatestSourceTimestamp(
  cohortCreatedAt: string | null,
  analysisFinishedAt: string | null,
  schemaTimestamp: string | null,
): number {
  const cohortTime = cohortCreatedAt ? Date.parse(cohortCreatedAt) : 0;
  const analysisTime = analysisFinishedAt ? Date.parse(analysisFinishedAt) : 0;
  const schemaTime = schemaTimestamp ? Date.parse(schemaTimestamp) : 0;
  return Math.max(cohortTime, analysisTime, schemaTime);
}

export function useReportBuilder() {
  const {
    state,
    markDone,
    setReportDraft,
  } = useFlow();
  const { createEvent } = useAudit();

  const { selectedArticleIds } = state.search;
  const cohortResult = state.cohort.result ?? null;
  const analysisRuns = state.analysis.history;
  const latestAnalysis = analysisRuns.at(-1) ?? null;
  const latestSourceTimestamp = getLatestSourceTimestamp(
    cohortResult?.createdAt ?? null,
    latestAnalysis?.finishedAt ?? null,
    state.schema?.version.timestamp ?? null,
  );
  const lastGeneratedAt = state.report.lastGeneratedAt ? Date.parse(state.report.lastGeneratedAt) : 0;
  const articleCount = selectedArticleIds.length;
  const cohortSize = cohortResult?.summary.size ?? null;
  const analysisRunCount = analysisRuns.length;

  const computeReport = useCallback((): ReportData => {
    return buildReportData({
      selectedArticleIds,
      cohort: cohortResult,
      analysisRuns,
      schema: state.schema,
    });
  }, [analysisRuns, cohortResult, selectedArticleIds, state.schema]);

  const generateReport = useCallback((): ReportData => {
    const draft = computeReport();
    setReportDraft(draft);
    if (state.steps.report !== 'done') {
      markDone('report');
    }
    createEvent('report.generated', 'report', {
      summary: 'Generated report draft from current cohort and analysis results.',
      articleCount,
      cohortSize,
      analysisRuns: analysisRunCount,
    });
    return draft;
  }, [
    analysisRunCount,
    cohortSize,
    computeReport,
    createEvent,
    markDone,
    articleCount,
    setReportDraft,
    state.steps.report,
  ]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const shouldGenerate = !state.report.draft || latestSourceTimestamp > lastGeneratedAt;
    if (!shouldGenerate) {
      return;
    }
    const draft = computeReport();
    setReportDraft(draft);
    // Don't auto-mark as done - user should explicitly generate report
    // if (state.steps.report !== 'done') {
    //   markDone('report');
    // }
    createEvent('report.generated.auto', 'report', {
      summary: 'Refreshed report after upstream changes.',
      articleCount,
      cohortSize,
      analysisRuns: analysisRunCount,
    });
  }, [
    computeReport,
    createEvent,
    lastGeneratedAt,
    latestSourceTimestamp,
    // markDone, // Removed from dependencies
    setReportDraft,
    state.report.draft,
    state.steps.report,
    analysisRunCount,
    cohortSize,
    articleCount,
  ]);

  const report = useMemo(() => state.report.draft, [state.report.draft]);

  return {
    report,
    hasReport: Boolean(report),
    generateReport,
    lastGeneratedAt: state.report.lastGeneratedAt,
    latestAnalysis,
    latestCohort: cohortResult,
  } as const;
}
