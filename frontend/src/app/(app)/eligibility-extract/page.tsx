'use client';

import { useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { NctInput } from '@/features/eligibility/components/nct-input';
import { ExtractionPreview } from '@/features/eligibility/components/extraction-preview';
import { CriteriaEditorList } from '@/features/eligibility/components/criterion-editor';
import { ReviewPanel } from '@/features/eligibility/components/review-panel';
import {
  useExtractEligibility,
  useReviewExtraction,
} from '@/features/eligibility/hooks/use-eligibility-extraction';
import type {
  ExtractResponse,
  EligibilityExtraction,
  EligibilityCriterion,
} from '@/features/eligibility/types';
import { CheckCircle2, AlertCircle } from 'lucide-react';

/**
 * Eligibility Extract Page
 *
 * Main page for eligibility criteria extraction workflow:
 * 1. User enters NCT ID
 * 2. System fetches and extracts criteria
 * 3. User reviews extraction result
 * 4. User can accept or edit
 * 5. Edited version is submitted as correction
 */
export default function EligibilityExtractPage() {
  const [nctId, setNctId] = useState('');
  const [extractResult, setExtractResult] = useState<ExtractResponse | null>(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedExtraction, setEditedExtraction] = useState<EligibilityExtraction | null>(
    null
  );
  const [selectedKeywords, setSelectedKeywords] = useState<string[]>([]);

  // Load available keywords (from backend or static config)
  const availableKeywords = [
    'age_criteria',
    'pregnancy_exclusion',
    'organ_dysfunction',
    'infection',
    'diabetes',
    'cancer',
    'comorbidities',
    'lab_values',
    'medication_history',
    'surgery_history',
    'cardiovascular',
    'respiratory',
    'renal_impairment',
    'hepatic_impairment',
    'prior_treatment',
    'mental_health',
    'genetic_markers',
    'imaging_criteria',
    'consent_capable',
    'study_compliance',
    'vital_signs',
    'ecog_performance',
    'karnofsky_score',
    'contraception_required',
    'substance_abuse',
    'hiv_status',
    'hepatitis_status',
    'neurological_condition',
    'immunosuppression',
    'bleeding_disorder',
  ];

  const { mutate: extract, isPending: isExtracting, error: extractError } = useExtractEligibility();
  const { mutate: review, isPending: isSubmitting } = useReviewExtraction();

  const handleSubmit = () => {
    if (!nctId) return;

    extract(
      { nct_id: nctId },
      {
        onSuccess: (response) => {
          if (response.data) {
            setExtractResult(response.data);
            setEditedExtraction(response.data.extraction);
            setSelectedKeywords([]);
            setIsEditMode(false);
          }
        },
        onError: (err) => {
          console.error('Extraction failed:', err);
          setExtractResult(null);
        },
      }
    );
  };

  const handleReset = () => {
    setNctId('');
    setExtractResult(null);
    setEditedExtraction(null);
    setSelectedKeywords([]);
    setIsEditMode(false);
  };

  const handleToggleEditMode = () => {
    if (!isEditMode && extractResult) {
      // Entering edit mode - copy original extraction
      setEditedExtraction({ ...extractResult.extraction });
    }
    setIsEditMode(!isEditMode);
  };

  const handleAccept = () => {
    if (!extractResult) return;

    review(
      {
        nct_id: extractResult.nct_id,
        action: 'accept',
        original_extraction: extractResult.extraction,
        keywords: [],
      },
      {
        onSuccess: () => {
          alert('Extraction accepted successfully!');
          handleReset();
        },
        onError: (err) => {
          console.error('Accept failed:', err);
          alert('Failed to accept extraction. Please try again.');
        },
      }
    );
  };

  const handleSubmitCorrection = (keywords: string[]) => {
    if (!extractResult || !editedExtraction) return;

    review(
      {
        nct_id: extractResult.nct_id,
        action: 'edit',
        original_extraction: extractResult.extraction,
        corrected_extraction: editedExtraction,
        keywords,
      },
      {
        onSuccess: () => {
          alert('Correction submitted successfully! Your feedback will improve future extractions.');
          handleReset();
        },
        onError: (err) => {
          console.error('Correction submission failed:', err);
          alert('Failed to submit correction. Please try again.');
        },
      }
    );
  };

  const handleUpdateInclusion = (updated: EligibilityCriterion[]) => {
    if (!editedExtraction) return;
    setEditedExtraction({
      ...editedExtraction,
      inclusion: updated,
    });
  };

  const handleUpdateExclusion = (updated: EligibilityCriterion[]) => {
    if (!editedExtraction) return;
    setEditedExtraction({
      ...editedExtraction,
      exclusion: updated,
    });
  };

  const errorMessage = extractError
    ? extractError instanceof Error
      ? extractError.message
      : 'An unexpected error occurred'
    : null;

  const displayExtraction = isEditMode ? editedExtraction : extractResult?.extraction;

  return (
    <div className="container mx-auto py-8 space-y-8 max-w-7xl">
      {/* Header */}
      <header className="space-y-2">
        <h1 className="text-3xl font-heading font-bold text-foreground">
          Eligibility Criteria Extraction
        </h1>
        <p className="text-base text-muted-foreground">
          Extract structured eligibility criteria from ClinicalTrials.gov NCT data using AI.
          The system learns from your corrections to improve future extractions.
        </p>
      </header>

      {/* Step 1: NCT Input */}
      {!extractResult && (
        <NctInput
          nctId={nctId}
          onChange={setNctId}
          onSubmit={handleSubmit}
          isLoading={isExtracting}
          error={errorMessage}
        />
      )}

      {/* Step 2 & 3: Extraction Result + Edit */}
      {extractResult && displayExtraction && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left: Preview or Editor */}
          <div className="lg:col-span-2 space-y-6">
            {/* Success Alert */}
            {!isEditMode && (
              <Alert>
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertDescription>
                  Successfully extracted eligibility criteria from {extractResult.nct_id}.
                  Review the results below.
                </AlertDescription>
              </Alert>
            )}

            {/* Edit Mode Alert */}
            {isEditMode && (
              <Alert>
                <AlertCircle className="h-4 w-4 text-blue-600" />
                <AlertDescription>
                  Edit mode active. Modify criteria below and select keywords in the right
                  panel before submitting.
                </AlertDescription>
              </Alert>
            )}

            {/* Content */}
            {!isEditMode ? (
              <ExtractionPreview
                nctId={extractResult.nct_id}
                extraction={displayExtraction}
                originalText={extractResult.original_eligibility_text}
                examplesUsed={extractResult.examples_used}
              />
            ) : (
              <Tabs defaultValue="inclusion" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="inclusion">
                    Inclusion ({displayExtraction.inclusion.length})
                  </TabsTrigger>
                  <TabsTrigger value="exclusion">
                    Exclusion ({displayExtraction.exclusion.length})
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="inclusion" className="space-y-4 mt-6">
                  <CriteriaEditorList
                    criteria={displayExtraction.inclusion}
                    criterionType="inclusion"
                    onUpdate={handleUpdateInclusion}
                  />
                </TabsContent>
                <TabsContent value="exclusion" className="space-y-4 mt-6">
                  <CriteriaEditorList
                    criteria={displayExtraction.exclusion}
                    criterionType="exclusion"
                    onUpdate={handleUpdateExclusion}
                  />
                </TabsContent>
              </Tabs>
            )}
          </div>

          {/* Right: Review Panel */}
          <div className="lg:col-span-1">
            <div className="sticky top-8 space-y-4">
              <ReviewPanel
                nctId={extractResult.nct_id}
                extraction={displayExtraction}
                onAccept={handleAccept}
                onEdit={handleToggleEditMode}
                onSubmitCorrection={handleSubmitCorrection}
                isEditMode={isEditMode}
                selectedKeywords={selectedKeywords}
                onKeywordsChange={setSelectedKeywords}
                availableKeywords={availableKeywords}
                isSubmitting={isSubmitting}
              />

              <Button variant="outline" onClick={handleReset} className="w-full">
                Extract Another NCT
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Info Footer */}
      {!extractResult && (
        <div className="rounded-lg border border-border/50 bg-muted/30 p-6 space-y-3">
          <h3 className="text-sm font-semibold">How it works:</h3>
          <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
            <li>Enter a valid NCT ID (e.g., NCT03389555)</li>
            <li>System fetches real trial data from ClinicalTrials.gov</li>
            <li>AI extracts structured eligibility criteria using few-shot learning</li>
            <li>Review and optionally correct the extraction</li>
            <li>Your corrections improve future extractions (human-in-the-loop)</li>
          </ol>
        </div>
      )}
    </div>
  );
}
