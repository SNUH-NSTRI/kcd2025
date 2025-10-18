'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { useFlow } from '@/features/flow/context';
import { ArrowRight } from 'lucide-react';
import type { Step } from '@/features/flow/types';

interface StepActionsProps {
  step: Step;
}

const STEP_ORDER: Step[] = ['search', 'schema', 'cohort', 'analysis', 'report'];

const STEP_ROUTES: Record<Step, string> = {
  search: '/search',
  schema: '/schema',
  cohort: '/cohort',
  analysis: '/analysis',
  report: '/report',
};

export function StepActions({ step }: StepActionsProps) {
  const router = useRouter();
  const { markDone, markError, resetStep, setInProgress, state } = useFlow();

  const currentIndex = STEP_ORDER.indexOf(step);
  const nextStep = currentIndex < STEP_ORDER.length - 1 ? STEP_ORDER[currentIndex + 1] : null;
  const nextRoute = nextStep ? STEP_ROUTES[nextStep] : null;

  const handleNext = () => {
    markDone(step);
    if (nextRoute) {
      // Add mode parameter if in demo mode
      const route = state.mode === 'demo' ? `${nextRoute}?mode=demo` : nextRoute;
      router.push(route);
    }
  };

  return (
    <div className="flex justify-end">
      {nextStep && (
        <Button onClick={handleNext} size="lg" className="gap-2">
          Next: {nextStep.charAt(0).toUpperCase() + nextStep.slice(1)}
          <ArrowRight className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
