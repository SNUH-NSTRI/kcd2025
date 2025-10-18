'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { Article } from '@/features/search/types';
import { getSchemaStorageKey, MAX_VERSION_HISTORY } from './constants';
import type {
  SchemaSection,
  SchemaValidationIssue,
  SchemaVersionSnapshot,
  TrialSchema,
} from './types';
import { generateInitialSchema } from './lib/generate-schema';
import { validateSchema } from './lib/validation';
import {
  createSnapshot,
  loadStoredVersions,
  saveVersions,
  withNewVersionMeta,
} from './lib/versioning';
import { deepClone, deepEqual } from './lib/utils';
import { useAudit } from '@/features/audit';
import { useFlow } from '@/features/flow/context';

interface SchemaWorkspaceContextValue {
  schema: TrialSchema | null;
  versions: SchemaVersionSnapshot[];
  validation: SchemaValidationIssue[];
  hasUnsavedChanges: boolean;
  activeSection: SchemaSection;
  setActiveSection: (section: SchemaSection) => void;
  updateSchema: (updater: (draft: TrialSchema) => TrialSchema) => void;
  replaceSchema: (next: TrialSchema) => void;
  saveDraftAsVersion: (message: string) => { success: boolean; rev?: number };
  revertToVersion: (rev: number) => void;
  resetToLatestVersion: () => void;
  selectedArticles: Article[];
  ready: boolean;
}

const SchemaWorkspaceContext = createContext<SchemaWorkspaceContextValue | undefined>(
  undefined,
);

interface SchemaWorkspaceProviderProps {
  selectedArticles: Article[];
  children: React.ReactNode;
}

export function SchemaWorkspaceProvider({
  selectedArticles,
  children,
}: SchemaWorkspaceProviderProps) {
  const articleIds = useMemo(
    () => selectedArticles.map((article) => article.id),
    [selectedArticles],
  );
  const storageKey = useMemo(
    () => getSchemaStorageKey(articleIds),
    [articleIds],
  );

  const [ready, setReady] = useState(false);
  const [schema, setSchema] = useState<TrialSchema | null>(null);
  const [versions, setVersions] = useState<SchemaVersionSnapshot[]>([]);
  const [validation, setValidation] = useState<SchemaValidationIssue[]>([]);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [activeSection, setActiveSection] = useState<SchemaSection>('overview');
  const { createEvent } = useAudit();
  const { setSchemaDraft } = useFlow();

  useEffect(() => {
    if (typeof window === 'undefined') return;
    setReady(false);
    setSchema(null);
    setVersions([]);
    const raw = window.localStorage.getItem(storageKey);
    const stored = loadStoredVersions(raw);
    if (stored.length > 0) {
      const latest = stored[stored.length - 1];
      setVersions(stored);
      const snapshot = deepClone(latest.schema);
      setSchema(snapshot);
      setSchemaDraft(snapshot);
      setReady(true);
      return;
    }

    const initialSchema = generateInitialSchema(selectedArticles);
    const snapshot = createSnapshot(initialSchema, null);
    setVersions([snapshot]);
    const initialClone = deepClone(initialSchema);
    setSchema(initialClone);
    setSchemaDraft(initialClone);
    saveVersions(storageKey, [snapshot]);
    setReady(true);
  }, [selectedArticles, setSchemaDraft, storageKey]);

  useEffect(() => {
    if (!schema) return;
    setValidation(validateSchema(schema));
    const latest = versions[versions.length - 1]?.schema ?? null;
    setHasUnsavedChanges(latest ? !deepEqual(schema, latest) : true);
  }, [schema, versions]);

  const updateSchema = useCallback(
    (updater: (draft: TrialSchema) => TrialSchema) => {
      setSchema((prev) => {
        if (!prev) return prev;
        const draft = deepClone(prev);
        const next = updater(draft);
        return next;
      });
    },
    [],
  );

  const replaceSchema = useCallback((next: TrialSchema) => {
    setSchema(deepClone(next));
  }, []);

  const saveDraftAsVersion = useCallback(
    (message: string) => {
      if (!schema) return { success: false } as const;
      const authoritative = versions[versions.length - 1]?.schema ?? null;
      const highestRev =
        versions.length > 0
          ? versions[versions.length - 1].schema.version.rev
          : schema.version.rev ?? 0;
      const versioned = withNewVersionMeta(schema, message, undefined, highestRev + 1);
      const snapshot = createSnapshot(versioned, authoritative);
      const nextVersions = [...versions, snapshot];
      const trimmed = nextVersions.slice(-MAX_VERSION_HISTORY);
      setVersions(trimmed);
      const clone = deepClone(versioned);
      setSchema(clone);
      setSchemaDraft(clone);
      saveVersions(storageKey, trimmed);
      createEvent('schema.version.commit', 'schema', {
        summary: message,
        rev: versioned.version.rev,
        articleIds,
        validationWarnings: validation.filter((issue) => issue.severity === 'warning').length,
      });
      return { success: true, rev: versioned.version.rev } as const;
    },
    [articleIds, createEvent, schema, setSchemaDraft, storageKey, validation, versions],
  );

  const resetToLatestVersion = useCallback(() => {
    const latest = versions[versions.length - 1];
    if (!latest) return;
    const snapshot = deepClone(latest.schema);
    setSchema(snapshot);
    setSchemaDraft(snapshot);
  }, [setSchemaDraft, versions]);

  const revertToVersion = useCallback(
    (rev: number) => {
      const target = versions.find((snapshot) => snapshot.schema.version.rev === rev);
      if (!target) return;
      const snapshot = deepClone(target.schema);
      setSchema(snapshot);
      setSchemaDraft(snapshot);
      setActiveSection('overview');
      createEvent('schema.version.revert', 'schema', {
        summary: `Reverted to revision ${rev}.`,
        toRev: rev,
      });
    },
    [createEvent, setSchemaDraft, versions],
  );

  const value = useMemo<SchemaWorkspaceContextValue>(
    () => ({
      schema,
      versions,
      validation,
      hasUnsavedChanges,
      activeSection,
      setActiveSection,
      updateSchema,
      replaceSchema,
      saveDraftAsVersion,
      revertToVersion,
      resetToLatestVersion,
      selectedArticles,
      ready,
    }),
    [
      activeSection,
      hasUnsavedChanges,
      ready,
      replaceSchema,
      resetToLatestVersion,
      revertToVersion,
      saveDraftAsVersion,
      schema,
      selectedArticles,
      updateSchema,
      validation,
      versions,
    ],
  );

  return (
    <SchemaWorkspaceContext.Provider value={value}>
      {children}
    </SchemaWorkspaceContext.Provider>
  );
}

export function useSchemaWorkspace() {
  const ctx = useContext(SchemaWorkspaceContext);
  if (!ctx) {
    throw new Error('useSchemaWorkspace must be used within SchemaWorkspaceProvider');
  }
  return ctx;
}
