'use client';

import { useCallback, useState } from 'react';
import { FileText, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface NctInputProps {
  nctId: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isLoading?: boolean;
  error?: string | null;
}

/**
 * NCT Input Component
 *
 * Provides a form for entering NCT ID with validation and submission.
 * Validates NCT ID format (NCT followed by 8 digits).
 */
export function NctInput({
  nctId,
  onChange,
  onSubmit,
  isLoading = false,
  error = null,
}: NctInputProps) {
  const [validationError, setValidationError] = useState<string | null>(null);

  const validateNctId = useCallback((value: string): boolean => {
    if (!value) {
      setValidationError('NCT ID is required');
      return false;
    }

    // NCT ID format: NCT followed by 8 digits (e.g., NCT03389555)
    const nctIdPattern = /^NCT\d{8}$/i;
    if (!nctIdPattern.test(value)) {
      setValidationError(
        'Invalid NCT ID format. Expected format: NCT followed by 8 digits (e.g., NCT03389555)'
      );
      return false;
    }

    setValidationError(null);
    return true;
  }, []);

  const handleChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const value = event.target.value.trim().toUpperCase();
      onChange(value);
      // Clear validation error when user types
      if (validationError) {
        setValidationError(null);
      }
    },
    [onChange, validationError]
  );

  const handleSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (validateNctId(nctId)) {
        onSubmit();
      }
    },
    [nctId, validateNctId, onSubmit]
  );

  const displayError = validationError || error;

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-border bg-card/30 p-6 shadow-sm space-y-4"
      role="search"
      aria-label="NCT eligibility extraction"
    >
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="nct-id-input" className="text-lg font-semibold">
            Enter NCT ID
          </Label>
          <FileText className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        </div>
        <p className="text-sm text-muted-foreground">
          Extract eligibility criteria from ClinicalTrials.gov study data
        </p>
      </div>

      <div className="space-y-2">
        <Input
          id="nct-id-input"
          value={nctId}
          onChange={handleChange}
          placeholder="NCT03389555"
          className="w-full text-lg"
          disabled={isLoading}
          aria-invalid={!!displayError}
          aria-describedby={displayError ? 'nct-id-error' : 'nct-id-help'}
          autoComplete="off"
          spellCheck={false}
        />
        {!displayError && (
          <p id="nct-id-help" className="text-xs text-muted-foreground">
            Format: NCT followed by 8 digits
          </p>
        )}
      </div>

      {displayError && (
        <Alert variant="destructive" id="nct-id-error">
          <AlertDescription>{displayError}</AlertDescription>
        </Alert>
      )}

      <Button
        type="submit"
        className="w-full gap-2"
        disabled={isLoading || !nctId}
        size="lg"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
            Extracting...
          </>
        ) : (
          <>
            <FileText className="h-5 w-5" aria-hidden="true" />
            Fetch & Extract Eligibility
          </>
        )}
      </Button>

      {isLoading && (
        <div className="space-y-2 rounded-md bg-muted/50 p-3">
          <p className="text-sm font-medium">Processing Steps:</p>
          <ul className="space-y-1 text-xs text-muted-foreground">
            <li>• Fetching NCT data from ClinicalTrials.gov...</li>
            <li>• Selecting relevant examples...</li>
            <li>• Extracting structured criteria...</li>
          </ul>
        </div>
      )}
    </form>
  );
}
