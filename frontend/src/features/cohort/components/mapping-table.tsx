'use client';

import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import type { TrialVariable } from '@/features/schema/types';
import type { DictionaryField } from '../types';

interface MappingTableProps {
  variables: TrialVariable[];
  dictionary: DictionaryField[];
  mapping: Record<string, string | null>;
  onChange: (variableId: string, fieldId: string | null) => void;
  onApplySuggestions: () => void;
  hasSuggestions: boolean;
}

export function MappingTable({
  variables,
  dictionary,
  mapping,
  onChange,
  onApplySuggestions,
  hasSuggestions,
}: MappingTableProps) {
  const dictionaryByType = useMemo(() => {
    return dictionary.reduce<Record<string, DictionaryField[]>>((acc, field) => {
      const key = field.type;
      acc[key] = acc[key] ? [...acc[key], field] : [field];
      return acc;
    }, {});
  }, [dictionary]);

  if (variables.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border/70 bg-card/40 p-4 text-sm text-muted-foreground">
        No schema variables available. Confirm that schema extraction has been saved before mapping.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Variable mapping</h3>
          <p className="text-sm text-muted-foreground">
            Align schema variables to dataset fields. Mappings persist locally for reuse.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onApplySuggestions}
          disabled={!hasSuggestions}
        >
          Auto-match suggestions
        </Button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/60">
        <table className="min-w-full divide-y divide-border/60 text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th scope="col" className="px-4 py-3 text-left font-medium text-muted-foreground">
                Schema variable
              </th>
              <th scope="col" className="px-4 py-3 text-left font-medium text-muted-foreground">
                Description
              </th>
              <th scope="col" className="px-4 py-3 text-left font-medium text-muted-foreground">
                Map to dataset field
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60 bg-background/80">
            {variables.map((variable) => {
              const selectedFieldId = mapping[variable.id] ?? '';
              const field = dictionary.find((item) => item.id === selectedFieldId);
              return (
                <tr key={variable.id}>
                  <td className="px-4 py-3 align-top">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-foreground">{variable.name}</span>
                      <span className="text-xs uppercase tracking-wide text-muted-foreground">
                        {variable.type}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    <p className="line-clamp-3 text-xs md:text-sm">{variable.description || '—'}</p>
                    {field ? (
                      <div className="mt-2 inline-flex items-center gap-2 text-xs text-primary">
                        <Badge variant="secondary" className="bg-primary/10 text-primary">
                          {field.type}
                        </Badge>
                        <span>{field.label}</span>
                      </div>
                    ) : null}
                  </td>
                  <td className="px-4 py-3">
                    <Select
                      value={selectedFieldId || '_unmapped'}
                      onValueChange={(value) =>
                        onChange(variable.id, value === '_unmapped' ? null : value)
                      }
                    >
                      <SelectTrigger aria-label={`Map ${variable.name}`} className="w-full">
                        <SelectValue placeholder="Select dataset field" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="_unmapped">
                          <span className="text-muted-foreground">Unmapped</span>
                        </SelectItem>
                        {Object.entries(dictionaryByType).map(([type, fields]) => (
                          <SelectGroup key={type}>
                            <SelectLabel className="text-xs uppercase text-muted-foreground">
                              {type}
                            </SelectLabel>
                            {fields.map((item) => (
                              <SelectItem key={item.id} value={item.id} className="text-sm">
                                <div className="flex flex-col">
                                  <span>{item.label}</span>
                                  <span className="text-xs text-muted-foreground">{item.description}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectGroup>
                        ))}
                      </SelectContent>
                    </Select>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
