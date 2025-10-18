'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, Loader2, Circle, AlertCircle } from 'lucide-react';
import type { StudyStatus } from '@/remote/types/studies';

interface ParsingProgressProps {
  status: StudyStatus;
}

export function ParsingProgress({ status }: ParsingProgressProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Trial Data</CardTitle>
        <CardDescription>
          Fetching and parsing eligibility criteria from ClinicalTrials.gov
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {status.steps.map((step) => (
          <ProgressStep
            key={step.step}
            label={step.label}
            status={step.status}
            error={step.error}
          />
        ))}

        {status.error && (
          <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium">Processing Failed</p>
                <p className="mt-1 text-xs">{status.error}</p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface ProgressStepProps {
  label: string;
  status: 'pending' | 'in_progress' | 'done' | 'failed';
  error?: string | null;
}

function ProgressStep({ label, status, error }: ProgressStepProps) {
  const getIcon = () => {
    switch (status) {
      case 'done':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'in_progress':
        return <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-destructive" />;
      case 'pending':
      default:
        return <Circle className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getTextColor = () => {
    switch (status) {
      case 'done':
        return 'text-green-700';
      case 'in_progress':
        return 'text-blue-700 font-medium';
      case 'failed':
        return 'text-destructive';
      case 'pending':
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <div className="flex items-start gap-3">
      <div className="flex-shrink-0 mt-0.5">{getIcon()}</div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm ${getTextColor()}`}>{label}</p>
        {error && (
          <p className="text-xs text-destructive mt-1">{error}</p>
        )}
      </div>
    </div>
  );
}
