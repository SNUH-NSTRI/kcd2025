'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, DatabaseZap } from 'lucide-react';
import type { EnrichedCriterion, ParsedMimicEntry } from '../types';

interface MimicMappingSectionProps {
  inclusion: EnrichedCriterion[];
  exclusion: EnrichedCriterion[];
}

function parseMimicMapping(mapping: Record<string, string>): ParsedMimicEntry[] {
  const entries: ParsedMimicEntry[] = [];
  const keys = Object.keys(mapping).sort();

  // Extract vars/method pairs (vars1, method1, vars2, method2, ...)
  const indices = new Set<number>();
  keys.forEach(key => {
    const match = key.match(/^(?:vars|method)(\d+)$/);
    if (match) {
      indices.add(parseInt(match[1]));
    }
  });

  Array.from(indices).sort((a, b) => a - b).forEach(idx => {
    const vars = mapping[`vars${idx}`];
    const method = mapping[`method${idx}`];
    if (vars || method) {
      entries.push({ index: idx, vars: vars || 'N/A', method: method || 'N/A' });
    }
  });

  return entries;
}

function CriterionCard({ criterion, type }: { criterion: EnrichedCriterion; type: 'inclusion' | 'exclusion' }) {
  const borderColor = type === 'inclusion' ? 'border-green-600' : 'border-red-600';
  const mimicEntries = criterion.mimic_mapping ? parseMimicMapping(criterion.mimic_mapping) : [];

  return (
    <div className={`border-l-4 ${borderColor} pl-4 py-3 bg-background rounded-r-md`}>
      <div className="flex items-center gap-2 mb-2">
        <Badge variant="outline" className="font-mono text-xs">{criterion.id}</Badge>
      </div>
      <p className="text-sm font-medium mb-3">{criterion.description}</p>

      {mimicEntries.length > 0 ? (
        <div className="space-y-2">
          {mimicEntries.map((entry) => (
            <div key={entry.index} className="bg-muted p-3 rounded-md">
              <div className="flex items-center gap-2 mb-2">
                <DatabaseZap className="w-4 h-4 text-blue-600" />
                <h4 className="text-xs font-semibold text-muted-foreground">
                  MIMIC-IV Mapping #{entry.index}
                </h4>
              </div>
              <div className="font-mono text-xs space-y-1">
                <p>
                  <span className="font-semibold text-blue-700">TABLES/VIEWS:</span>{' '}
                  <span className="text-blue-600">{entry.vars}</span>
                </p>
                <p>
                  <span className="font-semibold text-blue-700">QUERY LOGIC:</span>{' '}
                  <span className="text-foreground">{entry.method}</span>
                </p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-2 text-xs text-muted-foreground italic">
          No MIMIC-IV mapping generated for this criterion.
        </div>
      )}
    </div>
  );
}

export function MimicMappingSection({ inclusion, exclusion }: MimicMappingSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>MIMIC-IV Mapping</CardTitle>
        <CardDescription>
          Operational mapping of trial criteria to MIMIC-IV database schema for cohort queries.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Inclusion Criteria */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold">Inclusion Criteria</h3>
            <Badge variant="secondary">{inclusion.length}</Badge>
          </div>
          <div className="space-y-3">
            {inclusion.map((crit) => (
              <CriterionCard key={crit.id} criterion={crit} type="inclusion" />
            ))}
          </div>
        </div>

        {/* Exclusion Criteria */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <XCircle className="w-5 h-5 text-red-600" />
            <h3 className="font-semibold">Exclusion Criteria</h3>
            <Badge variant="secondary">{exclusion.length}</Badge>
          </div>
          <div className="space-y-3">
            {exclusion.map((crit) => (
              <CriterionCard key={crit.id} criterion={crit} type="exclusion" />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
