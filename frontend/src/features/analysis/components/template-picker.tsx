'use client';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { AnalysisTemplateMeta } from '@/features/flow/types';

interface TemplatePickerProps {
  templates: AnalysisTemplateMeta[];
  selectedId: string | null;
  onSelect: (templateId: string) => void;
  disabled?: boolean;
}

export function TemplatePicker({ templates, selectedId, onSelect, disabled = false }: TemplatePickerProps) {
  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-foreground">Analysis templates</h3>
      <div className="grid gap-3 md:grid-cols-2">
        {templates.map((template) => {
          const isSelected = template.id === selectedId;
          return (
            <Card
              key={template.id}
              className={`border transition ${
                isSelected ? 'border-primary shadow-md' : 'border-border/70'
              }`}
            >
              <CardHeader className="space-y-1">
                <CardTitle className="text-base text-foreground flex items-center justify-between gap-2">
                  {template.name}
                  {isSelected ? (
                    <Badge variant="secondary" className="bg-primary/10 text-primary">
                      Selected
                    </Badge>
                  ) : null}
                </CardTitle>
                <p className="text-sm text-muted-foreground">{template.description}</p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2 text-xs text-muted-foreground">
                  <p className="font-semibold uppercase tracking-wide">Inputs</p>
                  <div className="flex flex-wrap gap-1">
                    {template.inputs.map((input) => (
                      <Badge key={input} variant="outline" className="text-xs">
                        {input}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="space-y-2 text-xs text-muted-foreground">
                  <p className="font-semibold uppercase tracking-wide">Outputs</p>
                  <div className="flex flex-wrap gap-1">
                    {template.outputs.map((output) => (
                      <Badge key={output} variant="outline" className="text-xs">
                        {output}
                      </Badge>
                    ))}
                  </div>
                </div>
                <Button
                  type="button"
                  variant={isSelected ? 'default' : 'outline'}
                  className="w-full"
                  disabled={disabled}
                  onClick={() => onSelect(template.id)}
                >
                  {isSelected ? 'Selected' : 'Use template'}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
