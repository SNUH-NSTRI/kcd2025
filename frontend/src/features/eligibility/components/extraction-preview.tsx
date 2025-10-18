'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { CheckCircle2, XCircle, FileText, Sparkles } from 'lucide-react';
import type {
  EligibilityExtraction,
  EligibilityCriterion,
  CorrectionExample,
} from '../types';

interface ExtractionPreviewProps {
  nctId: string;
  extraction: EligibilityExtraction;
  originalText: string;
  examplesUsed: CorrectionExample[];
}

/**
 * Extraction Preview Component
 *
 * Displays extraction results in a 3-column layout:
 * - Left: Original NCT eligibility text
 * - Middle: Extracted structured criteria
 * - Right: Examples used for extraction (optional)
 */
export function ExtractionPreview({
  nctId,
  extraction,
  originalText,
  examplesUsed,
}: ExtractionPreviewProps) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Extraction Result</h2>
          <p className="text-sm text-muted-foreground">
            NCT ID: {nctId} · Confidence: {(extraction.confidence_score * 100).toFixed(1)}%
          </p>
        </div>
        <Badge variant={extraction.confidence_score >= 0.8 ? 'default' : 'secondary'}>
          <Sparkles className="mr-1 h-3 w-3" />
          {extraction.model_version}
        </Badge>
      </div>

      {/* 3-Column Layout */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Column 1: Original NCT Text */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" />
              Original Eligibility Text
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px] pr-4">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <pre className="whitespace-pre-wrap text-xs font-mono leading-relaxed">
                  {originalText}
                </pre>
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Column 2: Extracted Criteria */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Extracted Criteria</CardTitle>
            <p className="text-sm text-muted-foreground">
              {extraction.inclusion.length} inclusion, {extraction.exclusion.length} exclusion
            </p>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px] pr-4">
              <div className="space-y-6">
                {/* Inclusion Criteria */}
                {extraction.inclusion.length > 0 && (
                  <section>
                    <div className="mb-3 flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                      <h3 className="text-lg font-semibold">Inclusion Criteria</h3>
                    </div>
                    <div className="space-y-3">
                      {extraction.inclusion.map((criterion) => (
                        <CriterionCard key={criterion.id} criterion={criterion} />
                      ))}
                    </div>
                  </section>
                )}

                {extraction.inclusion.length > 0 && extraction.exclusion.length > 0 && (
                  <Separator />
                )}

                {/* Exclusion Criteria */}
                {extraction.exclusion.length > 0 && (
                  <section>
                    <div className="mb-3 flex items-center gap-2">
                      <XCircle className="h-5 w-5 text-red-600" />
                      <h3 className="text-lg font-semibold">Exclusion Criteria</h3>
                    </div>
                    <div className="space-y-3">
                      {extraction.exclusion.map((criterion) => (
                        <CriterionCard key={criterion.id} criterion={criterion} />
                      ))}
                    </div>
                  </section>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Examples Used (Optional Footer) */}
      {examplesUsed.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Examples Used ({examplesUsed.length})</CardTitle>
            <p className="text-sm text-muted-foreground">
              Few-shot examples selected for this extraction
            </p>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {examplesUsed.map((example) => (
                <ExampleCard key={example.nct_id} example={example} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/**
 * Individual Criterion Card
 */
function CriterionCard({ criterion }: { criterion: EligibilityCriterion }) {
  const valueDisplay = Array.isArray(criterion.value)
    ? criterion.value.join(', ')
    : String(criterion.value);

  return (
    <div className="rounded-lg border border-border bg-card/50 p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {criterion.key}
            </Badge>
            <span className="text-sm font-medium text-muted-foreground">
              {criterion.operator}
            </span>
            <span className="text-sm font-semibold">{valueDisplay}</span>
            {criterion.unit && (
              <span className="text-xs text-muted-foreground">{criterion.unit}</span>
            )}
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {criterion.original_text}
          </p>
        </div>
        <Badge variant="secondary" className="text-xs shrink-0">
          {criterion.id}
        </Badge>
      </div>
    </div>
  );
}

/**
 * Example Card for Few-Shot Display
 */
function ExampleCard({ example }: { example: CorrectionExample }) {
  const reasonColors = {
    condition_match: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    keyword_overlap: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    recent: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
    seed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  };

  return (
    <div className="rounded-md border border-border bg-card p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{example.nct_id}</span>
        <Badge variant="secondary" className="text-xs">
          {(example.quality_score * 100).toFixed(0)}%
        </Badge>
      </div>
      <div className="flex items-center gap-2">
        <Badge className={`text-xs ${reasonColors[example.selected_reason]}`}>
          {example.selected_reason.replace('_', ' ')}
        </Badge>
        <span className="text-xs text-muted-foreground">{example.metadata.condition}</span>
      </div>
    </div>
  );
}
