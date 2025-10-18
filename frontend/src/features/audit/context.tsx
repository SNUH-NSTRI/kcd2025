'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { AUDIT_STORAGE_KEY, DEFAULT_ACTOR, DEFAULT_FILTERS, RANGE_TO_MS } from './constants';
import type { AuditEvent, AuditFilters, AuditEntity } from './types';
import { getSeedAuditEvents } from './lib/dummy-data';
import { loadStoredEvents, persistEvents } from './lib/storage';

interface AuditStateContextValue {
  events: AuditEvent[];
  filteredEvents: AuditEvent[];
  filters: AuditFilters;
  availableActors: string[];
  hydrated: boolean;
}

interface AuditActionsContextValue {
  createEvent: (
    action: string,
    entity: AuditEntity,
    metadata?: Record<string, unknown>,
    options?: { actor?: string; ts?: number },
  ) => AuditEvent;
  updateFilters: (partial: Partial<AuditFilters>) => void;
  resetFilters: () => void;
}

const AuditStateContext = createContext<AuditStateContextValue | undefined>(undefined);
const AuditActionsContext = createContext<AuditActionsContextValue | undefined>(undefined);

function generateId(prefix: string): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  const random = Math.random().toString(36).slice(2, 10);
  return `${prefix}-${random}`;
}

export function AuditProvider({ children }: { children: React.ReactNode }) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [filters, setFilters] = useState<AuditFilters>(DEFAULT_FILTERS);
  const [hydrated, setHydrated] = useState(false);

  // Effect 1: Hydrate state from localStorage on initial client-side mount.
  useEffect(() => {
    // This effect runs only once on the client.
    if (typeof window === 'undefined') return;

    const raw = window.localStorage.getItem(AUDIT_STORAGE_KEY);
    const stored = loadStoredEvents(raw);
    const seeds = getSeedAuditEvents();

    // Simple merge and de-duplication logic.
    const allEvents = [...stored, ...seeds];
    const uniqueEventsById = Array.from(new Map(allEvents.map((e) => [e.id, e])).values());

    const sorted = uniqueEventsById.sort((a, b) => b.ts - a.ts);

    setEvents(sorted);
    setHydrated(true);
  }, []);

  // Effect 2: Persist events to localStorage whenever they change.
  useEffect(() => {
    // Avoid persisting the initial empty state before hydration is complete.
    if (hydrated) {
      persistEvents(events);
    }
  }, [events, hydrated]);

  const createEvent = useCallback<AuditActionsContextValue['createEvent']>(
    (action, entity, metadata = {}, options) => {
      const timestamp = options?.ts ?? Date.now();
      const actor = options?.actor ?? DEFAULT_ACTOR;
      const event: AuditEvent = {
        id: generateId('audit'),
        ts: timestamp,
        actor,
        entity,
        action,
        metadata: metadata ?? {},
      };
      // The persistence logic is now handled by the useEffect hook above.
      setEvents((prev) => [event, ...prev].sort((a, b) => b.ts - a.ts));
      return event;
    },
    [],
  );

  const updateFilters = useCallback((partial: Partial<AuditFilters>) => {
    setFilters((prev) => ({ ...prev, ...partial }));
  }, []);

  const resetFilters = useCallback(() => setFilters(DEFAULT_FILTERS), []);

  const filteredEvents = useMemo(() => {
    const now = Date.now();
    return events.filter((event) => {
      if (filters.entity !== 'all' && event.entity !== filters.entity) {
        return false;
      }
      if (filters.actor !== 'all' && event.actor !== filters.actor) {
        return false;
      }
      if (filters.range !== 'all') {
        const duration = RANGE_TO_MS[filters.range];
        if (event.ts < now - duration) {
          return false;
        }
      }
      return true;
    });
  }, [events, filters]);

  const availableActors = useMemo(() => {
    const actors = new Set<string>();
    events.forEach((event) => actors.add(event.actor));
    return Array.from(actors).sort((a, b) => a.localeCompare(b));
  }, [events]);

  const stateValue = useMemo<AuditStateContextValue>(
    () => ({
      events,
      filteredEvents,
      filters,
      availableActors,
      hydrated,
    }),
    // Dependencies are simplified to only include "source of truth" state.
    [events, filters, hydrated, filteredEvents, availableActors],
  );

  const actionsValue = useMemo<AuditActionsContextValue>(
    () => ({ createEvent, updateFilters, resetFilters }),
    [createEvent, resetFilters, updateFilters],
  );

  return (
    <AuditStateContext.Provider value={stateValue}>
      <AuditActionsContext.Provider value={actionsValue}>
        {children}
      </AuditActionsContext.Provider>
    </AuditStateContext.Provider>
  );
}

export function useAuditLogState() {
  const ctx = useContext(AuditStateContext);
  if (!ctx) {
    throw new Error('useAuditLogState must be used within AuditProvider');
  }
  return ctx;
}

export function useAudit() {
  const ctx = useContext(AuditActionsContext);
  if (!ctx) {
    throw new Error('useAudit must be used within AuditProvider');
  }
  return ctx;
}
