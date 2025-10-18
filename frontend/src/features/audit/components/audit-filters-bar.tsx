'use client';

import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ENTITY_LABELS, DEFAULT_FILTERS } from '../constants';
import type { AuditFilters } from '../types';
import { useAudit, useAuditLogState } from '../context';
import { cn } from '@/lib/utils';

const ENTITY_OPTIONS: Array<{ value: AuditFilters['entity']; label: string }> = [
  { value: 'all', label: 'All events' },
  { value: 'schema', label: ENTITY_LABELS.schema },
  { value: 'cohort', label: ENTITY_LABELS.cohort },
  { value: 'analysis', label: ENTITY_LABELS.analysis },
  { value: 'report', label: ENTITY_LABELS.report },
  { value: 'flow', label: ENTITY_LABELS.flow },
];

const RANGE_OPTIONS: Array<{ value: AuditFilters['range']; label: string }> = [
  { value: '7d', label: '7 days' },
  { value: '30d', label: '30 days' },
  { value: '90d', label: '90 days' },
  { value: 'all', label: 'All time' },
];

export function AuditFiltersBar() {
  const { filters, availableActors } = useAuditLogState();
  const { updateFilters, resetFilters } = useAudit();

  const handleEntityChange = (entity: AuditFilters['entity']) => {
    updateFilters({ entity });
  };

  const handleActorChange = (actor: string) => {
    updateFilters({ actor: actor as AuditFilters['actor'] });
  };

  const handleRangeChange = (range: AuditFilters['range']) => {
    updateFilters({ range });
  };

  const isDefaultFilters =
    filters.entity === DEFAULT_FILTERS.entity &&
    filters.actor === DEFAULT_FILTERS.actor &&
    filters.range === DEFAULT_FILTERS.range;

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border/60 bg-card/40 p-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        {ENTITY_OPTIONS.map((option) => (
          <Button
            key={option.value}
            type="button"
            size="sm"
            variant={filters.entity === option.value ? 'default' : 'outline'}
            className={cn(
              'rounded-full border-border/70 text-xs font-medium',
              filters.entity === option.value
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground',
            )}
            onClick={() => handleEntityChange(option.value)}
          >
            {option.label}
          </Button>
        ))}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Select value={filters.actor} onValueChange={handleActorChange}>
          <SelectTrigger className="h-9 w-[180px] text-sm">
            <SelectValue placeholder="All users" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All users</SelectItem>
            {availableActors.map((actor) => (
              <SelectItem key={actor} value={actor}>
                {actor}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex items-center gap-2">
          {RANGE_OPTIONS.map((option) => (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant={filters.range === option.value ? 'default' : 'ghost'}
              className={cn(
                'border border-transparent text-xs',
                filters.range === option.value
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )}
              onClick={() => handleRangeChange(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="self-start text-xs text-muted-foreground hover:text-foreground"
          onClick={resetFilters}
          disabled={isDefaultFilters}
        >
          Reset
        </Button>
      </div>
    </div>
  );
}
