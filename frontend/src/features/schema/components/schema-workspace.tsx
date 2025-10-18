'use client';

import { useState } from 'react';
import { useToast } from '@/hooks/use-toast';
import { SchemaCommitSheet } from './schema-commit-sheet';
import { SchemaEditor } from './schema-editor';
import { SchemaJsonPreview } from './schema-json-preview';
import { SchemaSectionNav } from './schema-section-nav';
import { SchemaValidationPanel } from './schema-validation-panel';
import { SchemaVersionHistory } from './schema-version-history';
import { useSchemaWorkspace } from '../context';
import { useFlow } from '@/features/flow/context';

export function SchemaWorkspace() {
  const {
    ready,
    resetToLatestVersion,
    saveDraftAsVersion,
    hasUnsavedChanges,
    validation,
  } = useSchemaWorkspace();
  const { markDone } = useFlow();
  const { toast } = useToast();
  const [commitOpen, setCommitOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleCommitSubmit = (message: string) => {
    const hasBlockingErrors = validation.some((issue) => issue.severity === 'error');
    if (hasBlockingErrors) {
      toast({
        title: 'Resolve blocking validation errors',
        description: 'Fix required fields or logical conflicts before saving a new version.',
        variant: 'destructive',
      });
      return;
    }
    setSaving(true);
    const result = saveDraftAsVersion(message);
    setSaving(false);
    if (result.success) {
      toast({
        title: `Version ${result.rev} saved`,
        description: 'Changes persisted locally. Continue iterating or progress the flow.',
      });
      markDone('schema');
      setCommitOpen(false);
    } else {
      toast({
        title: 'Unable to save version',
        description: 'Resolve pending validation errors and try again.',
        variant: 'destructive',
      });
    }
  };

  const handleReset = () => {
    resetToLatestVersion();
    toast({
      title: 'Draft reset',
      description: 'Reverted to the latest saved version.',
    });
  };

  return (
    <div className="space-y-6">
      {!ready ? (
        <div className="rounded-lg border border-dashed border-border/60 p-6 text-sm text-muted-foreground">
          Loading schema workspace…
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[250px_minmax(0,1fr)_300px]">
          <div className="space-y-4">
            <SchemaSectionNav />
            <SchemaVersionHistory />
          </div>
          <SchemaEditor
            onRequestSave={() => setCommitOpen(true)}
            onResetDraft={handleReset}
          />
          <div className="space-y-4">
            <SchemaValidationPanel />
            <SchemaJsonPreview />
          </div>
        </div>
      )}

      <SchemaCommitSheet
        open={commitOpen}
        onOpenChange={(open) => {
          if (!open && !saving) {
            setCommitOpen(false);
          } else if (open) {
            setCommitOpen(true);
          }
        }}
        onSubmit={handleCommitSubmit}
        saving={saving}
        defaultMessage={
          hasUnsavedChanges
            ? 'Refined schema based on manual audit and validation fixes.'
            : 'No changes detected, but saving to capture state.'
        }
      />
    </div>
  );
}
