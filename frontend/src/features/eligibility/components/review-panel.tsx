'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { CheckCircle2, Edit3, AlertCircle } from 'lucide-react';
import type { EligibilityExtraction } from '../types';

interface ReviewPanelProps {
  nctId: string;
  extraction: EligibilityExtraction;
  onAccept: () => void;
  onEdit: () => void;
  onSubmitCorrection: (keywords: string[]) => void;
  isEditMode: boolean;
  selectedKeywords: string[];
  onKeywordsChange: (keywords: string[]) => void;
  availableKeywords: string[];
  isSubmitting?: boolean;
}

/**
 * Review Panel Component
 *
 * Controls for accepting or editing the extraction:
 * - Accept button: Submit without changes
 * - Edit button: Toggle edit mode
 * - Keyword selector: Manual tagging
 * - Submit correction: Save edited version
 */
export function ReviewPanel({
  nctId,
  extraction,
  onAccept,
  onEdit,
  onSubmitCorrection,
  isEditMode,
  selectedKeywords,
  onKeywordsChange,
  availableKeywords,
  isSubmitting = false,
}: ReviewPanelProps) {
  // Validation
  const hasInclusion = extraction.inclusion.length > 0;
  const hasExclusion = extraction.exclusion.length > 0;
  const isValid = hasInclusion || hasExclusion;

  const handleKeywordToggle = (keyword: string) => {
    if (selectedKeywords.includes(keyword)) {
      onKeywordsChange(selectedKeywords.filter((k) => k !== keyword));
    } else {
      onKeywordsChange([...selectedKeywords, keyword]);
    }
  };

  return (
    <Card className="border-2">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Review Actions</span>
          {isEditMode && (
            <Badge variant="secondary" className="text-xs">
              Edit Mode
            </Badge>
          )}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {isEditMode
            ? 'Make changes and select applicable keywords before submitting.'
            : 'Accept the extraction as-is or proceed to edit and correct.'}
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Validation Warnings */}
        {!isValid && (
          <div className="flex items-start gap-3 rounded-lg border border-destructive/50 bg-destructive/5 p-3">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-destructive">Validation Error</p>
              <p className="text-xs text-muted-foreground">
                At least one inclusion or exclusion criterion is required.
              </p>
            </div>
          </div>
        )}

        {/* Keyword Selector (Edit Mode Only) */}
        {isEditMode && (
          <>
            <div className="space-y-3">
              <div>
                <Label className="text-base font-semibold">
                  Select Applicable Keywords *
                </Label>
                <p className="text-xs text-muted-foreground mt-1">
                  Tag this extraction with relevant keywords to improve future example
                  selection. Select all that apply ({selectedKeywords.length} selected).
                </p>
              </div>

              <ScrollArea className="h-[280px] rounded-md border border-border bg-muted/30 p-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  {availableKeywords.map((keyword) => (
                    <div
                      key={keyword}
                      className="flex items-center space-x-2 rounded-md border border-border bg-background p-3 hover:bg-accent transition-colors"
                    >
                      <Checkbox
                        id={`keyword-${keyword}`}
                        checked={selectedKeywords.includes(keyword)}
                        onCheckedChange={() => handleKeywordToggle(keyword)}
                      />
                      <label
                        htmlFor={`keyword-${keyword}`}
                        className="text-sm font-medium leading-none cursor-pointer flex-1 peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                      >
                        {keyword.replace(/_/g, ' ')}
                      </label>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
            <Separator />
          </>
        )}

        {/* Statistics */}
        <div className="grid grid-cols-3 gap-4 rounded-lg border border-border bg-muted/30 p-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {extraction.inclusion.length}
            </div>
            <div className="text-xs text-muted-foreground">Inclusion</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">
              {extraction.exclusion.length}
            </div>
            <div className="text-xs text-muted-foreground">Exclusion</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">
              {(extraction.confidence_score * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-muted-foreground">Confidence</div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-3">
          {!isEditMode ? (
            <>
              {/* Accept Button */}
              <Button
                onClick={onAccept}
                disabled={!isValid || isSubmitting}
                className="w-full"
                size="lg"
              >
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Accept Extraction
              </Button>

              {/* Edit Button */}
              <Button
                onClick={onEdit}
                variant="outline"
                className="w-full"
                size="lg"
              >
                <Edit3 className="mr-2 h-4 w-4" />
                Edit & Correct
              </Button>
            </>
          ) : (
            <>
              {/* Submit Correction Button */}
              <Button
                onClick={() => onSubmitCorrection(selectedKeywords)}
                disabled={
                  !isValid || selectedKeywords.length === 0 || isSubmitting
                }
                className="w-full"
                size="lg"
              >
                {isSubmitting ? (
                  <>Submitting...</>
                ) : (
                  <>
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Submit Correction
                  </>
                )}
              </Button>

              {/* Cancel Button */}
              <Button
                onClick={onEdit}
                variant="outline"
                className="w-full"
                disabled={isSubmitting}
              >
                Cancel Edit
              </Button>

              {/* Hint */}
              {selectedKeywords.length === 0 && (
                <p className="text-xs text-center text-muted-foreground">
                  Select at least one keyword to enable submission
                </p>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
