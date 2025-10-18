'use client';

import { useEnrichmentData } from '../hooks/useEnrichmentData';
import { IcdEnrichmentSection } from './IcdEnrichmentSection';
import { MimicMappingSection } from './MimicMappingSection';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Terminal, Sparkles } from 'lucide-react';
import type { EnrichedEntity } from '../types';

interface EnrichmentViewProps {
  nctId: string;
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-5 w-3/4" />
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Skeleton className="h-[500px] w-full" />
        <Skeleton className="h-[500px] w-full" />
      </div>
    </div>
  );
}

export function EnrichmentView({ nctId }: EnrichmentViewProps) {
  const { data, isLoading, isError, error } = useEnrichmentData(nctId);

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <Terminal className="h-4 w-4" />
        <AlertTitle>Error Fetching Enrichment Data</AlertTitle>
        <AlertDescription>
          {error instanceof Error ? error.message : 'An unknown error occurred'}
        </AlertDescription>
      </Alert>
    );
  }

  if (!data) {
    return (
      <Alert>
        <Terminal className="h-4 w-4" />
        <AlertTitle>No Data Available</AlertTitle>
        <AlertDescription>
          No enrichment data found for trial {nctId}. The trial may not have been processed yet.
        </AlertDescription>
      </Alert>
    );
  }

  // Collect all entities from inclusion and exclusion criteria
  const allEntities = [
    ...data.inclusion.flatMap((c) => c.entities || []),
    ...data.exclusion.flatMap((c) => c.entities || []),
  ] as EnrichedEntity[];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-blue-600" />
          <h1 className="text-3xl font-bold tracking-tight">Trial Enrichment Report</h1>
        </div>
        <p className="text-muted-foreground text-lg">
          Stage 4 enrichment results for trial{' '}
          <span className="font-mono font-semibold text-foreground">{nctId}</span>
        </p>
        <p className="text-sm text-muted-foreground">
          Automatically generated ICD medical codes and MIMIC-IV database mappings for cohort
          identification.
        </p>
      </div>

      {/* Enrichment Sections */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
        <IcdEnrichmentSection entities={allEntities} />
        <MimicMappingSection inclusion={data.inclusion} exclusion={data.exclusion} />
      </div>
    </div>
  );
}
