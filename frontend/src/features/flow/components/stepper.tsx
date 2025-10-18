'use client';

import { Fragment } from 'react';
import { STEPS, STEP_ORDER } from '@/features/flow/constants';
import { useFlow } from '@/features/flow/context';
import { StepItem } from './step-item';

interface StepperProps {
  disabled?: boolean;
}

export function Stepper({ disabled = false }: StepperProps) {
  const {
    state: { currentStep, steps },
    canAccessStep,
  } = useFlow();

  const currentIndex = STEP_ORDER.indexOf(currentStep);

  return (
    <nav aria-label="Trial synthesis workflow" className="w-full max-w-3xl">
      <ol className="flex flex-1 items-center gap-3 md:gap-4">
        {STEPS.map((step, index) => {
          const state = steps[step.key];
          const isActive = currentStep === step.key;
          const isCompleted = state === 'done';
          const connectorActive = index < currentIndex;
          const locked = !canAccessStep(step.key);

          return (
            <Fragment key={step.key}>
              <li className="flex flex-1 items-center gap-3">
                <StepItem
                  step={step}
                  state={state}
                  isCurrent={isActive}
                  disabled={disabled || (locked && !isActive)}
                />
                {index < STEPS.length - 1 && (
                  <span
                    aria-hidden="true"
                    className={`
                      hidden h-px flex-1 rounded-full lg:block
                      ${connectorActive || isCompleted ? 'bg-primary' : 'bg-border'}
                    `}
                  />
                )}
              </li>
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
