'use client';

import Link from 'next/link';
import { getStatusVisual } from '@/features/flow/status-utils';
import type { StepMeta, StepState } from '@/features/flow/types';
import { cn } from '@/lib/utils';

interface StepItemProps {
  step: StepMeta;
  state: StepState;
  isCurrent: boolean;
  disabled?: boolean;
}

export function StepItem({ step, state, isCurrent, disabled = false }: StepItemProps) {
  const visual = getStatusVisual(state);
  const Icon = visual.icon;

  const ariaLabel = `${step.name} – ${visual.label}. ${step.description}`;

  return (
    <Link
      href={step.href}
      aria-label={ariaLabel}
      aria-describedby={`${step.key}-description`}
      aria-current={isCurrent ? 'step' : undefined}
      aria-disabled={disabled ? 'true' : undefined}
      tabIndex={disabled ? -1 : 0}
      prefetch={false}
      className={cn(
        'group flex min-w-[120px] flex-col items-center gap-2 rounded-lg border border-transparent p-2 text-center outline-none transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
        disabled && 'pointer-events-none opacity-70',
      )}
      title={step.description}
    >
      <span
        className={cn(
          'flex h-10 w-10 items-center justify-center rounded-full transition-colors',
          isCurrent ? 'ring-2 ring-primary ring-offset-2' : 'ring-transparent',
          visual.wrapperClass,
        )}
      >
        <Icon
          aria-hidden="true"
          className={cn('h-5 w-5', state === 'in-progress' && 'animate-spin')}
        />
      </span>
      <span
        className={cn(
          'text-sm font-medium leading-tight text-foreground',
          visual.textClass,
        )}
      >
        {step.name}
      </span>
      <span className="sr-only" id={`${step.key}-description`}>
        {step.description}
      </span>
    </Link>
  );
}
