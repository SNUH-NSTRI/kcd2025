'use client';

import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SchemaSection, SchemaValidationIssue } from '../types';
import { useSchemaWorkspace } from '../context';

interface SectionConfig {
  key: SchemaSection;
  label: string;
  description: string;
}

const SECTIONS: SectionConfig[] = [
  {
    key: 'overview',
    label: 'Overview',
    description: 'Title, objectives, and population synopsis.',
  },
  {
    key: 'criteria',
    label: 'Eligibility',
    description: 'Inclusion and exclusion criteria management.',
  },
  {
    key: 'variables',
    label: 'Variables',
    description: 'Exposure, covariate, and confounder definitions.',
  },
  {
    key: 'outcomes',
    label: 'Outcomes',
    description: 'Clinical endpoints and monitoring metrics.',
  },
  {
    key: 'metadata',
    label: 'Metadata',
    description: 'Source attribution and registry context.',
  },
];

function countIssuesBySection(section: SchemaSection, issues: SchemaValidationIssue[]) {
  const matchers: Record<SchemaSection, RegExp[]> = {
    overview: [/^title/, /^objective/, /^population/, /^notes/],
    criteria: [/^inclusion/, /^exclusion/, /^criteria/],
    variables: [/^variables/],
    outcomes: [/^outcomes/],
    metadata: [/^metadata/],
  };

  const patterns = matchers[section];
  const relevant = issues.filter((issue) =>
    patterns.some((pattern) => pattern.test(issue.path)),
  );
  const errors = relevant.filter((issue) => issue.severity === 'error').length;
  const warnings = relevant.filter((issue) => issue.severity === 'warning').length;
  return { errors, warnings };
}

export function SchemaSectionNav() {
  const { activeSection, setActiveSection, validation, hasUnsavedChanges } =
    useSchemaWorkspace();

  return (
    <nav aria-label="Schema sections" className="space-y-3">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-foreground">Workspace</p>
          <p className="text-xs text-muted-foreground">
            {hasUnsavedChanges
              ? 'Unsaved changes pending versioning.'
              : 'In sync with latest version.'}
          </p>
        </div>
        {hasUnsavedChanges ? (
          <AlertCircle className="h-4 w-4 text-amber-500" aria-hidden />
        ) : (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden />
        )}
      </header>

      <ul className="space-y-2">
        {SECTIONS.map((section) => {
          const counts = countIssuesBySection(section.key, validation);
          return (
            <li key={section.key}>
              <button
                type="button"
                onClick={() => setActiveSection(section.key)}
                className={cn(
                  'w-full rounded-lg border border-border bg-card/60 p-3 text-left transition',
                  'hover:border-primary/80 hover:bg-primary/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  activeSection === section.key && 'border-primary bg-primary/10 shadow-sm',
                )}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {section.label}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {section.description}
                    </p>
                  </div>
                  {(counts.errors > 0 || counts.warnings > 0) && (
                    <span
                      className={cn(
                        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                        counts.errors > 0
                          ? 'bg-destructive/10 text-destructive'
                          : 'bg-amber-500/10 text-amber-600',
                      )}
                    >
                      {counts.errors > 0
                        ? `${counts.errors} error${counts.errors > 1 ? 's' : ''}`
                        : `${counts.warnings} warning${counts.warnings > 1 ? 's' : ''}`}
                    </span>
                  )}
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
