'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useSchemaWorkspace } from '../context';

export function SchemaJsonPreview() {
  const { schema } = useSchemaWorkspace();

  return (
    <Card className="h-fit border border-border/80 bg-card/80">
      <CardHeader className="space-y-1">
        <CardTitle className="text-base">JSON Preview</CardTitle>
        <p className="text-sm text-muted-foreground">
          Snapshot of the schema delivered to downstream agents.
        </p>
      </CardHeader>
      <CardContent>
        <pre className="max-h-[320px] overflow-auto rounded-md bg-muted p-3 text-xs text-muted-foreground">
          {schema ? JSON.stringify(schema, null, 2) : 'Schema not initialised.'}
        </pre>
      </CardContent>
    </Card>
  );
}
