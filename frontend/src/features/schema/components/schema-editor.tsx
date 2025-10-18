'use client';

import { useMemo } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useSchemaWorkspace } from '../context';
import { generateId } from '../lib/utils';
import type {
  SchemaSection,
  SchemaValidationIssue,
  TrialVariableType,
} from '../types';

const VARIABLE_TYPE_OPTIONS: Array<{ label: string; value: TrialVariableType }> = [
  { label: 'Numeric', value: 'numeric' },
  { label: 'Categorical', value: 'categorical' },
  { label: 'Boolean', value: 'boolean' },
  { label: 'Text', value: 'text' },
  { label: 'Date', value: 'date' },
];

const OUTCOME_METRIC_OPTIONS = [
  'hazard ratio',
  'odds ratio',
  'relative risk',
  'risk difference',
  'time-to-event',
];

interface SchemaEditorProps {
  onRequestSave: () => void;
  onResetDraft: () => void;
}

function useIssueLookup(validation: SchemaValidationIssue[]) {
  return useMemo(() => {
    const map = new Map<string, SchemaValidationIssue[]>();
    validation.forEach((issue) => {
      const list = map.get(issue.path) ?? [];
      list.push(issue);
      map.set(issue.path, list);
    });
    return map;
  }, [validation]);
}

function fieldHasSeverity(
  lookup: Map<string, SchemaValidationIssue[]>,
  path: string,
  severity: SchemaValidationIssue['severity'] | 'any' = 'any',
) {
  const issues = lookup.get(path) ?? [];
  if (severity === 'any') return issues.length > 0;
  return issues.some((issue) => issue.severity === severity);
}

export function SchemaEditor({ onRequestSave, onResetDraft }: SchemaEditorProps) {
  const {
    schema,
    updateSchema,
    activeSection,
    validation,
    hasUnsavedChanges,
    selectedArticles,
  } = useSchemaWorkspace();
  const issueLookup = useIssueLookup(validation);

  if (!schema) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Initialising schema workspace…
        </CardContent>
      </Card>
    );
  }

  const sectionMeta: Record<SchemaSection, { title: string; hint: string }> = {
      overview: {
        title: 'Clinical overview',
        hint:
          'Define the schema narrative so downstream teams understand objectives and population focus.',
      },
      criteria: {
        title: 'Eligibility criteria',
        hint:
          'Tweak inclusion and exclusion rules. These guardrails map to cohort filters.',
      },
      variables: {
        title: 'Variable catalogue',
        hint:
          'Adjust exposure, confounder, and context variables used for cohort generation.',
      },
      outcomes: {
        title: 'Outcome definitions',
        hint:
          'Document endpoints and metrics that analytic agents will compute.',
      },
      metadata: {
        title: 'Source metadata',
        hint: 'Document provenance across journals, registries, and population notes.',
      },
    } as const;

  const activeCopy = sectionMeta[activeSection];

  const renderOverview = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="schema-title">Title</Label>
        <Input
          id="schema-title"
          value={schema.title}
          onChange={(event) =>
            updateSchema((draft) => {
              draft.title = event.target.value;
              return draft;
            })
          }
          className={cn(
            fieldHasSeverity(issueLookup, 'title', 'error') &&
              'border-destructive focus-visible:ring-destructive',
          )}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="schema-objective">Objective</Label>
        <Textarea
          id="schema-objective"
          value={schema.objective}
          onChange={(event) =>
            updateSchema((draft) => {
              draft.objective = event.target.value;
              return draft;
            })
          }
          rows={4}
          className={cn(
            fieldHasSeverity(issueLookup, 'objective', 'error') &&
              'border-destructive focus-visible:ring-destructive',
          )}
        />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="schema-population">Population narrative</Label>
          <Textarea
            id="schema-population"
            value={schema.population}
            onChange={(event) =>
              updateSchema((draft) => {
                draft.population = event.target.value;
                return draft;
              })
            }
            rows={3}
            className={cn(
              fieldHasSeverity(issueLookup, 'population', 'error') &&
                'border-destructive focus-visible:ring-destructive',
            )}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="schema-notes">Notes</Label>
          <Textarea
            id="schema-notes"
            value={schema.notes ?? ''}
            onChange={(event) =>
              updateSchema((draft) => {
                draft.notes = event.target.value;
                return draft;
              })
            }
            rows={3}
          />
        </div>
      </div>
      {selectedArticles.length > 0 && (
        <div className="rounded-lg border border-border bg-primary/5 p-3 text-xs text-primary">
          Seeded from: {selectedArticles.map((article) => article.title).join('; ')}
        </div>
      )}
    </div>
  );

  const renderCriteriaList = (
    items: string[],
    type: 'inclusion' | 'exclusion',
  ) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-semibold capitalize">{type} criteria</Label>
        <Button
          variant="ghost"
          size="sm"
          className="inline-flex items-center gap-1"
          onClick={() =>
            updateSchema((draft) => {
              const list = type === 'inclusion' ? draft.inclusionCriteria : draft.exclusionCriteria;
              list.push('');
              return draft;
            })
          }
        >
          <Plus className="h-4 w-4" aria-hidden /> Add
        </Button>
      </div>
      <div className="space-y-2">
        {items.map((item, index) => {
          const path = type === 'inclusion' ? 'inclusion' : 'exclusion';
          return (
            <div key={`${type}-${index}`} className="flex gap-2">
              <Textarea
                value={item}
                onChange={(event) =>
                  updateSchema((draft) => {
                    const list =
                      type === 'inclusion'
                        ? draft.inclusionCriteria
                        : draft.exclusionCriteria;
                    list[index] = event.target.value;
                    return draft;
                  })
                }
                rows={2}
                className={cn(
                  'flex-1',
                  fieldHasSeverity(issueLookup, path, 'error') &&
                    'border-destructive focus-visible:ring-destructive',
                )}
              />
              <Button
                variant="ghost"
                size="icon"
                onClick={() =>
                  updateSchema((draft) => {
                    const list =
                      type === 'inclusion'
                        ? draft.inclusionCriteria
                        : draft.exclusionCriteria;
                    list.splice(index, 1);
                    return draft;
                  })
                }
                aria-label={`Remove ${type} criterion ${index + 1}`}
              >
                <Trash2 className="h-4 w-4" aria-hidden />
              </Button>
            </div>
          );
        })}
        {items.length === 0 && (
          <p className="text-xs italic text-muted-foreground">
            No {type} criteria defined. Add at least one item to guide cohort generation.
          </p>
        )}
      </div>
    </div>
  );

  const renderCriteria = () => (
    <div className="grid gap-6 lg:grid-cols-2">
      {renderCriteriaList(schema.inclusionCriteria, 'inclusion')}
      {renderCriteriaList(schema.exclusionCriteria, 'exclusion')}
    </div>
  );

  const renderVariables = () => (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <Label className="font-semibold">Variables</Label>
          <p className="text-xs text-muted-foreground">
            Describe covariates and exposures. Order matches downstream processing.
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="inline-flex items-center gap-1"
          onClick={() =>
            updateSchema((draft) => {
              draft.variables.push({
                id: generateId('var'),
                name: 'New variable',
                type: 'text',
                description: '',
                required: false,
              });
              return draft;
            })
          }
        >
          <Plus className="h-4 w-4" aria-hidden /> Add variable
        </Button>
      </div>

      <div className="space-y-3">
        {schema.variables.map((variable, index) => {
          const pathPrefix = `variables[${index}]`;
          return (
            <Card key={variable.id} className="border border-border/70">
              <CardContent className="space-y-3 pt-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex flex-col">
                    <Label>Name</Label>
                    <Input
                      value={variable.name}
                      onChange={(event) =>
                        updateSchema((draft) => {
                          const target = draft.variables.find((item) => item.id === variable.id);
                          if (target) {
                            target.name = event.target.value;
                          }
                          return draft;
                        })
                      }
                      className={cn(
                        fieldHasSeverity(issueLookup, `${pathPrefix}.name`, 'error') &&
                          'border-destructive focus-visible:ring-destructive',
                      )}
                    />
                  </div>
                  <div className="w-40">
                    <Label>Type</Label>
                    <Select
                      value={variable.type}
                      onValueChange={(value: TrialVariableType) =>
                        updateSchema((draft) => {
                          const target = draft.variables.find((item) => item.id === variable.id);
                          if (target) {
                            target.type = value;
                          }
                          return draft;
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        {VARIABLE_TYPE_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center gap-2 pt-6">
                    <Checkbox
                      id={`variable-required-${variable.id}`}
                      checked={variable.required}
                      onCheckedChange={(checked) =>
                        updateSchema((draft) => {
                          const target = draft.variables.find((item) => item.id === variable.id);
                          if (target) {
                            target.required = Boolean(checked);
                          }
                          return draft;
                        })
                      }
                    />
                    <Label htmlFor={`variable-required-${variable.id}`} className="text-xs">
                      Required
                    </Label>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() =>
                      updateSchema((draft) => {
                        draft.variables = draft.variables.filter((item) => item.id !== variable.id);
                        return draft;
                      })
                    }
                    aria-label={`Remove ${variable.name}`}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </Button>
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    value={variable.description}
                    onChange={(event) =>
                      updateSchema((draft) => {
                        const target = draft.variables.find((item) => item.id === variable.id);
                        if (target) {
                          target.description = event.target.value;
                        }
                        return draft;
                      })
                    }
                    rows={2}
                  />
                </div>
                {variable.sourceHint && (
                  <p className="text-xs text-muted-foreground">
                    Derived from article {variable.sourceHint}
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
        {schema.variables.length === 0 && (
          <p className="text-xs italic text-muted-foreground">
            No variables defined. Add at least one variable to persist version changes.
          </p>
        )}
      </div>
    </div>
  );

  const renderOutcomes = () => (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="font-semibold">Outcomes</Label>
        <Button
          variant="ghost"
          size="sm"
          className="inline-flex items-center gap-1"
          onClick={() =>
            updateSchema((draft) => {
              draft.outcomes.push({
                id: generateId('outcome'),
                name: 'New outcome',
                description: '',
                metric: 'relative risk',
              });
              return draft;
            })
          }
        >
          <Plus className="h-4 w-4" aria-hidden /> Add outcome
        </Button>
      </div>
      <div className="space-y-3">
        {schema.outcomes.map((outcome) => (
          <Card key={outcome.id} className="border border-border/70">
            <CardContent className="space-y-3 pt-4">
              <div className="grid gap-3 md:grid-cols-[1fr_220px_auto]">
                <div className="space-y-1">
                  <Label>Name</Label>
                  <Input
                    value={outcome.name}
                    onChange={(event) =>
                      updateSchema((draft) => {
                        const target = draft.outcomes.find((item) => item.id === outcome.id);
                        if (target) {
                          target.name = event.target.value;
                        }
                        return draft;
                      })
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label>Metric</Label>
                  <Select
                    value={outcome.metric}
                    onValueChange={(value) =>
                      updateSchema((draft) => {
                        const target = draft.outcomes.find((item) => item.id === outcome.id);
                        if (target) {
                          target.metric = value;
                        }
                        return draft;
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {OUTCOME_METRIC_OPTIONS.map((metric) => (
                        <SelectItem key={metric} value={metric}>
                          {metric}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-end justify-end">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() =>
                      updateSchema((draft) => {
                        draft.outcomes = draft.outcomes.filter((item) => item.id !== outcome.id);
                        return draft;
                      })
                    }
                    aria-label={`Remove ${outcome.name}`}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </Button>
                </div>
              </div>
              <div className="space-y-1">
                <Label>Description</Label>
                <Textarea
                  value={outcome.description}
                  onChange={(event) =>
                    updateSchema((draft) => {
                      const target = draft.outcomes.find((item) => item.id === outcome.id);
                      if (target) {
                        target.description = event.target.value;
                      }
                      return draft;
                    })
                  }
                  rows={2}
                />
              </div>
            </CardContent>
          </Card>
        ))}
        {schema.outcomes.length === 0 && (
          <p className="text-xs italic text-muted-foreground">
            No outcomes defined. Add primary and secondary endpoints to proceed.
          </p>
        )}
      </div>
    </div>
  );

  const renderMetadata = () => (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="schema-journal">Journal / Registry</Label>
          <Input
            id="schema-journal"
            value={schema.metadata.journal}
            onChange={(event) =>
              updateSchema((draft) => {
                draft.metadata.journal = event.target.value;
                return draft;
              })
            }
            className={cn(
              fieldHasSeverity(issueLookup, 'metadata.journal', 'error') &&
                'border-destructive focus-visible:ring-destructive',
            )}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="schema-source">Primary source</Label>
          <Select
            value={schema.metadata.source}
            onValueChange={(value) =>
              updateSchema((draft) => {
                draft.metadata.source = value;
                return draft;
              })
            }
          >
            <SelectTrigger id="schema-source">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="PubMed">PubMed</SelectItem>
              <SelectItem value="CTgov">ClinicalTrials.gov</SelectItem>
              <SelectItem value="Institutional">Institutional</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="schema-year">Publication year</Label>
          <Input
            id="schema-year"
            inputMode="numeric"
            value={schema.metadata.year ?? ''}
            onChange={(event) =>
              updateSchema((draft) => {
                const raw = event.target.value.trim();
                draft.metadata.year = raw === '' ? null : Number(raw);
                return draft;
              })
            }
            className={cn(
              fieldHasSeverity(issueLookup, 'metadata.year', 'warning') &&
                'border-amber-500 focus-visible:ring-amber-500',
            )}
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="schema-population-synopsis">Population synopsis</Label>
        <Textarea
          id="schema-population-synopsis"
          value={schema.metadata.populationSynopsis ?? ''}
          onChange={(event) =>
            updateSchema((draft) => {
              draft.metadata.populationSynopsis = event.target.value;
              return draft;
            })
          }
          rows={3}
        />
      </div>
    </div>
  );

  const sectionContent = {
    overview: renderOverview,
    criteria: renderCriteria,
    variables: renderVariables,
    outcomes: renderOutcomes,
    metadata: renderMetadata,
  }[activeSection]();

  return (
    <Card className="border border-border/80">
      <CardHeader className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-xl font-semibold text-foreground">
              {activeCopy.title}
            </CardTitle>
            <p className="text-sm text-muted-foreground">{activeCopy.hint}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="ghost" onClick={onResetDraft} disabled={!hasUnsavedChanges}>
              Discard changes
            </Button>
            <Button onClick={onRequestSave} disabled={!hasUnsavedChanges}>
              Save version
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">{sectionContent}</CardContent>
    </Card>
  );
}
