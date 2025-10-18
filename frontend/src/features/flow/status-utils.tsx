'use client';

import type { ComponentType } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Loader2,
} from 'lucide-react';
import type { StepState } from './types';

interface StatusVisual {
  icon: ComponentType<{ className?: string }>;
  wrapperClass: string;
  textClass: string;
  label: string;
}

const STATUS_MAP: Record<StepState, StatusVisual> = {
  idle: {
    icon: Circle,
    wrapperClass: 'bg-muted text-muted-foreground',
    textClass: 'text-muted-foreground',
    label: 'Idle',
  },
  'in-progress': {
    icon: Loader2,
    wrapperClass: 'bg-primary/10 text-primary',
    textClass: 'text-primary',
    label: 'In progress',
  },
  done: {
    icon: CheckCircle2,
    wrapperClass: 'bg-emerald-50 text-emerald-600',
    textClass: 'text-emerald-600',
    label: 'Completed',
  },
  error: {
    icon: AlertTriangle,
    wrapperClass: 'bg-destructive/10 text-destructive',
    textClass: 'text-destructive',
    label: 'Needs attention',
  },
};

export function getStatusVisual(state: StepState): StatusVisual {
  return STATUS_MAP[state];
}
