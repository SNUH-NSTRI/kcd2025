'use client';

import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DATASET_OPTIONS, MAX_COHORT_SIZE, MIN_COHORT_SIZE } from '../constants';
import type { CohortDatasetId } from '@/features/flow/types';

interface CohortControlsProps {
  datasetId: CohortDatasetId;
  onDatasetChange: (id: CohortDatasetId) => void;
  cohortSize: number;
  onSizeChange: (size: number) => void;
  seed: string;
  onSeedChange: (seed: string) => void;
  onGenerate: () => void;
  onReset: () => void;
  disabled: boolean;
  generating: boolean;
  mappedCount: number;
  totalVariables: number;
}

export function CohortControls({
  datasetId,
  onDatasetChange,
  cohortSize,
  onSizeChange,
  seed,
  onSeedChange,
  onGenerate,
  onReset,
  disabled,
  generating,
  mappedCount,
  totalVariables,
}: CohortControlsProps) {
  const disableGenerate = disabled || mappedCount === 0;

  const datasetCopy = useMemo(
    () => DATASET_OPTIONS.find((option) => option.id === datasetId)?.description ?? '',
    [datasetId],
  );

  return (
    <section className="rounded-lg border border-border/70 bg-card/60 p-4 shadow-sm space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Load Real Cohort Data</h3>
          <p className="text-sm text-muted-foreground">
            Load actual patient cohort from MIMIC-IV based on trial inclusion/exclusion criteria.
          </p>
        </div>
        <div className="text-xs text-muted-foreground">
          {mappedCount} / {totalVariables} variables mapped
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="cohort-dataset">Dataset</Label>
          <Select value={datasetId} onValueChange={(value) => onDatasetChange(value as CohortDatasetId)}>
            <SelectTrigger id="cohort-dataset" aria-label="Dataset">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DATASET_OPTIONS.map((option) => (
                <SelectItem key={option.id} value={option.id}>
                  <div className="flex flex-col">
                    <span>{option.label}</span>
                    <span className="text-xs text-muted-foreground">{option.description}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2 opacity-50">
          <Label htmlFor="cohort-size">Cohort size (N/A for real data)</Label>
          <Input
            id="cohort-size"
            type="number"
            disabled
            value={cohortSize}
          />
          <p className="text-xs text-muted-foreground">
            Size determined by actual filtered patients.
          </p>
        </div>

        <div className="space-y-2 opacity-50">
          <Label htmlFor="cohort-seed">Seed (N/A for real data)</Label>
          <Input
            id="cohort-seed"
            disabled
            value="real-mimic-iv-data"
            placeholder="real-mimic-iv-data"
          />
          <p className="text-xs text-muted-foreground">Loading actual patient records from MIMIC-IV.</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground max-w-xl">{datasetCopy}</p>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="ghost" onClick={onReset} size="sm">
            Clear results
          </Button>
          <Button onClick={onGenerate} disabled={disableGenerate}>
            {generating ? 'Loading…' : 'Load Real Cohort'}
          </Button>
        </div>
      </div>
    </section>
  );
}
