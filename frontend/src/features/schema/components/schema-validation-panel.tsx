'use client';

import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useSchemaWorkspace } from '../context';

export function SchemaValidationPanel() {
  const { validation } = useSchemaWorkspace();
  const errors = validation.filter((issue) => issue.severity === 'error');
  const warnings = validation.filter((issue) => issue.severity === 'warning');
  const healthy = validation.length === 0;

  return (
    <Card className="h-fit border border-border/80 bg-card/80">
      <CardHeader className="space-y-1">
        <div className="flex items-center gap-2">
          {healthy ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-500" aria-hidden />
          ) : errors.length > 0 ? (
            <AlertTriangle className="h-5 w-5 text-destructive" aria-hidden />
          ) : (
            <Info className="h-5 w-5 text-amber-500" aria-hidden />
          )}
          <CardTitle className="text-base">Validation</CardTitle>
        </div>
        <p className="text-sm text-muted-foreground">
          Automatically checks for missing fields, conflicts, and schema hygiene.
        </p>
      </CardHeader>
      <CardContent>
        {healthy ? (
          <p className="text-sm text-muted-foreground">
            All validation checks pass. You can proceed to versioning or cohort execution.
          </p>
        ) : (
          <ul className="space-y-2">
            {validation.map((issue) => (
              <li
                key={issue.id}
                className={cn(
                  'rounded-md border px-3 py-2 text-sm shadow-sm',
                  issue.severity === 'error'
                    ? 'border-destructive/60 bg-destructive/10 text-destructive'
                    : 'border-amber-500/60 bg-amber-500/10 text-amber-600',
                )}
              >
                <p className="font-medium capitalize">{issue.path}</p>
                <p>{issue.message}</p>
              </li>
            ))}
          </ul>
        )}
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-destructive">
            Errors: {errors.length}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-amber-600">
            Warnings: {warnings.length}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
