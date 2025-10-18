'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { CorpusData } from '@/remote/types/studies';

interface OriginalTextPanelProps {
  corpus: CorpusData;
}

export function OriginalTextPanel({ corpus }: OriginalTextPanelProps) {
  const trial = corpus.documents[0];

  // Try multiple paths for eligibility criteria (backend structure varies)
  const eligibilityText =
    trial.metadata.eligibility?.eligibilityCriteria ||  // Flattened structure (preferred)
    trial.metadata.full_study_data?.protocolSection?.eligibilityModule?.eligibilityCriteria ||  // Full API structure
    'No eligibility criteria found.';

  return (
    <Card className="h-full overflow-auto">
      <CardHeader>
        <div className="flex items-center gap-2 flex-wrap">
          <CardTitle className="text-xl">{trial.title}</CardTitle>
          <Badge variant="secondary">{trial.metadata.nctId}</Badge>
        </div>
        <CardDescription>
          {trial.metadata.design?.phases && `Phase: ${trial.metadata.design.phases.join(', ')} | `}
          {trial.metadata.status && `Status: ${trial.metadata.status}`}
          {trial.metadata.sponsors?.leadSponsor && ` | Sponsor: ${trial.metadata.sponsors.leadSponsor.name}`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground">Original Eligibility Criteria</h3>
          <p className="text-xs text-muted-foreground">
            Raw text from ClinicalTrials.gov protocol
          </p>
          <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg font-mono leading-relaxed">
            {eligibilityText}
          </pre>
        </div>
      </CardContent>
    </Card>
  );
}
