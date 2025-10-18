'use client';

import { useMemo, useState } from 'react';
import { useToast } from '@/hooks/use-toast';
import { useFlow, useCohortState } from '@/features/flow/context';
import { CohortControls } from './cohort-controls';
import { MappingTable } from './mapping-table';
import { CohortSummary } from './cohort-summary';
import { DataPreview } from './data-preview';
import { COHORT_DICTIONARY } from '../lib/dictionary';
import { suggestMappings } from '../lib/generator';
import { parseCohortCSV, summarizeCohort } from '../lib/csv-parser';
import { projectsApi } from '@/remote/api/projects';
import { useAudit } from '@/features/audit';

export function CohortWorkspace() {
  const { toast } = useToast();
  const {
    state,
    setCohortMapping,
    setCohortResult,
    setCohortDataset,
    setCohortSeed,
    setCohortSize,
    markDone,
  } = useFlow();
  const cohortState = useCohortState();
  const { createEvent } = useAudit();

  // Extract studyMetadata from demoConfig when in demo mode
  const studyMetadata = state.mode === 'demo' ? state.demoConfig.study : undefined;
  const { steps, schema } = state;

  const [generating, setGenerating] = useState(false);

  const variables = useMemo(() => schema?.variables ?? [], [schema]);
  const mappedCount = useMemo(
    () =>
      variables.reduce((acc, variable) => {
        return cohortState.mapping[variable.id] ? acc + 1 : acc;
      }, 0),
    [cohortState.mapping, variables],
  );

  const suggestions = useMemo(() => suggestMappings(variables), [variables]);
  const hasSuggestions = useMemo(
    () =>
      variables.some(
        (variable) => !cohortState.mapping[variable.id] && suggestions[variable.id],
      ),
    [cohortState.mapping, suggestions, variables],
  );

  const handleApplySuggestions = () => {
    const appliedVariables: string[] = [];
    variables.forEach((variable) => {
      const suggestion = suggestions[variable.id];
      if (!suggestion) return;
      if (cohortState.mapping[variable.id]) return;
      setCohortMapping(variable.id, suggestion);
      appliedVariables.push(variable.id);
    });
    toast({
      title: 'Suggestions applied',
      description: 'Auto-mapped variables based on dictionary keywords. Review before generating.',
    });
    if (appliedVariables.length > 0) {
      createEvent('cohort.mapping.suggestion', 'cohort', {
        summary: 'Applied auto-mapping suggestions to cohort variables.',
        variables: appliedVariables,
      });
    }
  };

  const handleGenerate = async () => {
    if (!schema) {
      toast({
        title: 'Schema unavailable',
        description: 'Commit a schema version before generating a cohort.',
        variant: 'destructive',
      });
      return;
    }

    if (!studyMetadata) {
      toast({
        title: 'Study metadata unavailable',
        description: 'Study information is required to load cohort data.',
        variant: 'destructive',
      });
      return;
    }

    setGenerating(true);
    try {
      // Load real cohort CSV data from backend
      const csvText = await projectsApi.getCohortData(
        studyMetadata.nctId,
        studyMetadata.medicine
      );

      // Parse CSV into patient records
      const patients = parseCohortCSV(csvText);

      if (patients.length === 0) {
        throw new Error('No patient data found in cohort CSV');
      }

      // Generate summary from real data
      const summary = summarizeCohort(patients);

      const result = {
        patients,
        summary,
        createdAt: new Date().toISOString(),
        seed: `real-data-${studyMetadata.nctId}-${studyMetadata.medicine}`,
      };

      setCohortResult(result);
      if (steps.cohort !== 'done') {
        markDone('cohort');
      }

      toast({
        title: 'Cohort loaded',
        description: `Loaded ${result.summary.size} real patient records from MIMIC-IV.`,
      });

      createEvent('cohort.loaded', 'cohort', {
        summary: `Loaded real cohort data with ${result.summary.size} patients.`,
        nctId: studyMetadata.nctId,
        medication: studyMetadata.medicine,
        dataSource: 'MIMIC-IV v3.1',
      });
    } catch (error) {
      console.error(error);
      toast({
        title: 'Loading failed',
        description: error instanceof Error ? error.message : 'Failed to load cohort data.',
        variant: 'destructive',
      });
      createEvent('cohort.load.failed', 'cohort', {
        summary: 'Cohort loading failed.',
        message: error instanceof Error ? error.message : String(error),
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleClearResults = () => {
    setCohortResult(null);
    toast({
      title: 'Results cleared',
      description: 'Generated cohort removed from workspace.',
    });
    createEvent('cohort.result.cleared', 'cohort', {
      summary: 'Cleared generated cohort from workspace.',
    });
  };

  if (!schema) {
    return (
      <div className="space-y-4 rounded-lg border border-dashed border-border/70 bg-card/40 p-6 text-sm text-muted-foreground">
        {state.mode === 'demo' ? (
          <div>
            <p className="font-medium mb-2">Demo mode is loading...</p>
            <p>Schema and cohort data should load automatically. If you see this message, the demo data may not be loaded yet.</p>
            <p className="mt-2 text-xs">Debug: mode={state.mode}, schema={schema ? 'exists' : 'null'}, cohort result={cohortState.result ? 'exists' : 'null'}</p>
          </div>
        ) : (
          <p>Commit a schema version in the previous step to enable cohort synthesis. Saved schemas populate automatically when ready.</p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {variables.length === 0 ? (
        <div className="rounded-md border border-dashed border-border/70 bg-card/40 p-4 text-sm text-muted-foreground">
          No schema variables found. Save your schema extraction to enable cohort mapping.
        </div>
      ) : null}
      <MappingTable
        variables={variables}
        dictionary={COHORT_DICTIONARY}
        mapping={cohortState.mapping}
        onChange={setCohortMapping}
        onApplySuggestions={handleApplySuggestions}
        hasSuggestions={hasSuggestions}
      />

      <CohortControls
        datasetId={cohortState.datasetId}
        onDatasetChange={setCohortDataset}
        cohortSize={cohortState.cohortSize}
        onSizeChange={setCohortSize}
        seed={cohortState.seed}
        onSeedChange={setCohortSeed}
        onGenerate={handleGenerate}
        onReset={handleClearResults}
        disabled={variables.length === 0}
        generating={generating}
        mappedCount={mappedCount}
        totalVariables={variables.length}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_minmax(320px,360px)]">
        <DataPreview result={cohortState.result} variables={variables} />
        <CohortSummary result={cohortState.result} />
      </div>
    </div>
  );
}
