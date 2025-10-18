'use client';

import type { ReactNode } from 'react';
import { useFlow } from '@/features/flow/context';
import { STEPS, STEP_ORDER } from '@/features/flow/constants';
import type { Step } from '@/features/flow/types';

function getPrerequisiteStep(step: Step): Step | null {
  const index = STEP_ORDER.indexOf(step);
  if (index <= 0) {
    return null;
  }
  return STEP_ORDER[index - 1] ?? null;
}

interface RequiredStepGuardProps {
  step: Step;
  children: ReactNode;
}

export function RequiredStepGuard({ step, children }: RequiredStepGuardProps) {
  const { canAccessStep, state } = useFlow();

  // Allow all steps in demo mode
  const allowed = state.mode === 'demo' || canAccessStep(step);

  // Don't redirect - allow users to view any page
  // The locked UI below will prevent interaction if prerequisites aren't met
  if (!allowed) {
    const prerequisite = getPrerequisiteStep(step);
    const meta = prerequisite ? STEPS.find((item) => item.key === prerequisite) : null;

    return (
      <div className="rounded-lg border border-dashed border-destructive/50 bg-destructive/10 p-6 text-sm text-destructive">
        <p className="font-semibold">This step is locked.</p>
        <p className="mt-1 text-destructive/80">
          {meta
            ? `Complete ${meta.name.toLowerCase()} before progressing to this stage.`
            : 'Complete the prerequisite stages to continue the trial synthesis workflow.'}
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
