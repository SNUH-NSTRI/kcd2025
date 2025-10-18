'use client';

import { useCallback, useState } from 'react';
import { StepActions } from '@/features/flow/components/step-actions';
import { RequiredStepGuard } from '@/features/flow/components/required-step-guard';
import { useFlow } from '@/features/flow/context';
import { ReportActions } from '@/features/report/components/report-actions';
import { ReportPreview } from '@/features/report/components/report-preview';
import { StreamingReportViewer } from '@/features/report/components/streaming-report-viewer';
import { useReportBuilder } from '@/features/report/hooks/use-report-builder';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, BarChart3 } from 'lucide-react';

export default function ReportPage() {
  const {
    state: { steps, mode, search },
  } = useFlow();
  const { report, hasReport, generateReport, lastGeneratedAt } = useReportBuilder();
  const [activeTab, setActiveTab] = useState<'summary' | 'detailed'>('summary');

  const status = steps.report;

  // Extract NCT ID and medication from workflow
  const nctId = search?.selectedArticleIds?.[0] || 'NCT03389555';
  const medication = 'hydrocortisonenasucc'; // TODO: Get from cohort state
  const useStreaming = true; // Always use streaming for comprehensive report

  const handleDownloadJson = useCallback(() => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `trial-report-${report.createdAt}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [report]);

  const handlePrint = useCallback(() => {
    if (!report) return;
    window.print();
  }, [report]);

  return (
    <RequiredStepGuard step="report">
      <section className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">Step 5</p>
          <h2 className="text-3xl font-heading font-bold text-foreground">Real-World Evidence Report</h2>
          <p className="text-base text-muted-foreground">
            Generate comprehensive reports with real-time streaming. Toggle between executive summary and detailed statistical analysis.
          </p>
          <p className="text-sm font-medium text-primary">
            Current status: <span className="capitalize">{status}</span>
          </p>
        </header>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'summary' | 'detailed')} className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="summary" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              Executive Summary
            </TabsTrigger>
            <TabsTrigger value="detailed" className="gap-2">
              <FileText className="h-4 w-4" />
              Detailed Report
            </TabsTrigger>
          </TabsList>

          <TabsContent value="summary" className="mt-6">
            <StreamingReportViewer nctId={nctId} medication={medication} viewMode="summary" />
          </TabsContent>

          <TabsContent value="detailed" className="mt-6">
            <StreamingReportViewer nctId={nctId} medication={medication} viewMode="detailed" />
          </TabsContent>
        </Tabs>

        <StepActions step="report" />
      </section>
    </RequiredStepGuard>
  );
}
