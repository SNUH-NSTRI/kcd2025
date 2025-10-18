'use client';

import { useMemo } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { History, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useSchemaWorkspace } from '../context';

export function SchemaVersionHistory() {
  const { versions, revertToVersion, schema } = useSchemaWorkspace();

  const currentRev = schema?.version.rev ?? null;
  const sorted = useMemo(() => [...versions].sort((a, b) => a.schema.version.rev - b.schema.version.rev), [versions]);

  return (
    <Card className="border border-border/80 bg-card/80">
      <CardHeader className="space-y-1">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-primary" aria-hidden />
          <CardTitle className="text-base">Version history</CardTitle>
        </div>
        <p className="text-sm text-muted-foreground">
          Review commits stored locally. Reverting updates the working draft but keeps history intact.
        </p>
      </CardHeader>
      <CardContent>
        {sorted.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Versions will appear here after your first save.
          </p>
        ) : (
          <ul className="space-y-3">
            {sorted
              .slice()
              .reverse()
              .map((entry) => {
                const { version } = entry.schema;
                const isCurrent = version.rev === currentRev;
                const changes = entry.changes.slice(0, 3);
                const remaining = entry.changes.length - changes.length;
                return (
                  <li
                    key={version.rev}
                    className={cn(
                      'rounded-lg border px-3 py-3 shadow-sm transition',
                      isCurrent
                        ? 'border-primary/70 bg-primary/10'
                        : 'border-border bg-background/80',
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-foreground">
                          Rev {version.rev}{' '}
                          <span className="text-xs font-normal text-muted-foreground">
                            · {formatDistanceToNow(new Date(version.timestamp), { addSuffix: true })}
                          </span>
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {version.author} — {version.message}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant={isCurrent ? 'outline' : 'ghost'}
                        onClick={() => revertToVersion(version.rev)}
                        disabled={isCurrent}
                        className="inline-flex items-center gap-1"
                      >
                        <RotateCcw className="h-4 w-4" aria-hidden />
                        Revert
                      </Button>
                    </div>
                    <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                      {changes.map((change, index) => (
                        <li key={index}>• {change}</li>
                      ))}
                      {remaining > 0 && (
                        <li className="italic">• +{remaining} more change(s)</li>
                      )}
                    </ul>
                  </li>
                );
              })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
