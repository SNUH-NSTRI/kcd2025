'use client';

import { useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { AuditEvent } from '../types';
import { ENTITY_LABELS } from '../constants';

const dateFormatter = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  year: 'numeric',
});

const timeFormatter = new Intl.DateTimeFormat('en-US', {
  hour: '2-digit',
  minute: '2-digit',
});

interface AuditTimelineProps {
  events: AuditEvent[];
}

interface TimelineGroup {
  key: string;
  label: string;
  events: AuditEvent[];
}

function summariseEvent(event: AuditEvent): string {
  const summary = typeof event.metadata?.summary === 'string' ? event.metadata.summary : null;
  if (summary) return summary;
  const label = ENTITY_LABELS[event.entity] ?? event.entity;
  return `${label} ${event.action}`;
}

function describeAction(event: AuditEvent): string {
  const label = ENTITY_LABELS[event.entity] ?? event.entity;
  const actionLabel = event.action.replace(/\./g, ' › ');
  return `${label} - ${actionLabel}`;
}

function groupEventsByDate(events: AuditEvent[]): TimelineGroup[] {
  const groups = new Map<string, TimelineGroup>();
  events.forEach((event) => {
    const date = new Date(event.ts);
    const key = date.toISOString().slice(0, 10);
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        label: dateFormatter.format(date),
        events: [],
      });
    }
    groups.get(key)?.events.push(event);
  });

  return Array.from(groups.values())
    .map((group) => ({
      ...group,
      events: group.events.sort((a, b) => b.ts - a.ts),
    }))
    .sort((a, b) => (a.key < b.key ? 1 : -1));
}

export function AuditTimeline({ events }: AuditTimelineProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const groups = useMemo(() => groupEventsByDate(events), [events]);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  if (groups.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border/60 bg-card/40 p-6 text-sm text-muted-foreground">
        No audit activity captured for the selected filters yet. Run workflow actions to populate this view.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {groups.map((group) => (
        <section key={group.key} className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {group.label}
          </h3>
          <ul className="space-y-4">
            {group.events.map((event) => {
              const isExpanded = expanded.has(event.id);
              const date = new Date(event.ts);
              const timeLabel = timeFormatter.format(date);
              const entityLabel = ENTITY_LABELS[event.entity] ?? event.entity;
              const summary = summariseEvent(event);
              return (
                <li key={event.id} className="rounded-lg border border-border/60 bg-card/60 p-4 shadow-sm">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex flex-1 flex-col gap-2">
                      <div className="flex flex-wrap items-center gap-2 text-sm">
                        <Badge variant="outline" className="border-primary/60 text-primary">
                          {entityLabel}
                        </Badge>
                        <span className="text-xs uppercase tracking-wide text-muted-foreground">
                          {event.actor}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-foreground">{summary}</p>
                      <p className="text-xs text-muted-foreground">{describeAction(event)}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-medium text-muted-foreground">{timeLabel}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="text-xs text-muted-foreground hover:text-foreground"
                        onClick={() => toggle(event.id)}
                      >
                        {isExpanded ? 'Hide payload' : 'View payload'}
                      </Button>
                    </div>
                  </div>
                  {isExpanded ? (
                    <pre className="mt-3 max-h-64 overflow-auto rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
                      {JSON.stringify(event.metadata, null, 2)}
                    </pre>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
