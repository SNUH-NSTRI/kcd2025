'use client';

import { useCallback, useMemo, useState } from 'react';
import { cn } from '@/lib/utils';
import { STEPS } from '@/features/flow/constants';
import { useFlow } from '@/features/flow/context';
import { Stepper } from './stepper';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { ChevronDown, ChevronUp } from 'lucide-react';

export function FlowHeader() {
  const {
    state: { currentStep, steps },
    resetFlow,
    activatePrebuiltDemo,
  } = useFlow();
  const { toast } = useToast();
  const [isExpanded, setIsExpanded] = useState(true);

  const currentMeta = useMemo(
    () => STEPS.find((step) => step.key === currentStep),
    [currentStep],
  );

  const currentState = steps[currentStep];

  const handleReset = useCallback(() => {
    resetFlow();
    toast({
      title: 'Workflow reset',
      description: 'Cleared selections and returned to literature search.',
    });
  }, [resetFlow, toast]);

  const handleDemo = useCallback(() => {
    activatePrebuiltDemo();
    toast({
      title: 'Demo mode activated',
      description: 'Loaded real MIMIC-IV cohort data for demonstration.',
    });
  }, [activatePrebuiltDemo, toast]);

  return (
    <header
      className={cn(
        'sticky top-14 z-40 border-b border-border bg-background/95 backdrop-blur',
        'supports-[backdrop-filter]:bg-background/75',
      )}
      role="banner"
    >
      <div className="mx-auto w-full max-w-6xl px-6">
        {/* Header bar - always visible */}
        <div className="flex items-center justify-between py-2">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="h-8 px-2"
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Trial Workflow Progress
            </p>
            <span className="text-sm text-muted-foreground">
              · <span className="font-medium capitalize">{currentState}</span>
            </span>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="h-8"
            >
              Reset workflow
            </Button>
            <Button size="sm" onClick={handleDemo} className="h-8">
              Run demo
            </Button>
          </div>
        </div>

        {/* Collapsible content */}
        {isExpanded && (
          <div className="flex flex-col gap-2 pb-3 pt-1 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-col gap-1">
              <h1 className="text-lg font-heading font-semibold text-foreground">
                {currentMeta?.name ?? 'Trial Workflow'}
              </h1>
            </div>
            <div className="flex flex-col items-stretch gap-2 md:items-end">
              <Stepper />
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
