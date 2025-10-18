'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Stethoscope, FileText } from 'lucide-react';
import type { EnrichedEntity } from '../types';

interface IcdEnrichmentSectionProps {
  entities: EnrichedEntity[];
}

export function IcdEnrichmentSection({ entities }: IcdEnrichmentSectionProps) {
  // Filter entities that have ICD codes
  const conditionEntities = entities.filter(
    (entity) =>
      entity.domain === 'Condition' &&
      entity.metadata &&
      ((entity.metadata.icd9 && entity.metadata.icd9.length > 0) ||
        (entity.metadata.icd10 && entity.metadata.icd10.length > 0))
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>ICD Code Enrichment</CardTitle>
        <CardDescription>
          Condition entities automatically mapped to ICD-9 and ICD-10 medical codes via LLM.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {conditionEntities.length > 0 ? (
          <div className="space-y-4">
            {conditionEntities.map((entity, idx) => (
              <div key={idx} className="p-4 bg-muted rounded-md space-y-3">
                {/* Entity Header */}
                <div className="flex items-center gap-2">
                  <Stethoscope className="w-4 h-4 text-blue-600" />
                  <h4 className="font-semibold text-base">{entity.text}</h4>
                  {entity.standard_name && entity.standard_name !== entity.text && (
                    <Badge variant="outline" className="text-xs">
                      {entity.standard_name}
                    </Badge>
                  )}
                </div>

                {/* ICD Codes Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* ICD-9 Codes */}
                  <div className="space-y-2">
                    <h5 className="font-semibold text-xs text-muted-foreground flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      ICD-9 Codes
                    </h5>
                    {entity.metadata?.icd9 && entity.metadata.icd9.length > 0 ? (
                      <div className="space-y-1.5">
                        {entity.metadata.icd9.map((icd, i) => (
                          <div
                            key={i}
                            className="bg-background p-2 rounded border border-border text-xs"
                          >
                            <div className="font-mono font-semibold text-purple-700">
                              {icd.code}
                            </div>
                            <div className="text-muted-foreground mt-0.5">{icd.title}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs italic text-muted-foreground">None found</span>
                    )}
                  </div>

                  {/* ICD-10 Codes */}
                  <div className="space-y-2">
                    <h5 className="font-semibold text-xs text-muted-foreground flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      ICD-10 Codes
                    </h5>
                    {entity.metadata?.icd10 && entity.metadata.icd10.length > 0 ? (
                      <div className="space-y-1.5">
                        {entity.metadata.icd10.map((icd, i) => (
                          <div
                            key={i}
                            className="bg-background p-2 rounded border border-border text-xs"
                          >
                            <div className="font-mono font-semibold text-blue-700">
                              {icd.code}
                            </div>
                            <div className="text-muted-foreground mt-0.5">{icd.title}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs italic text-muted-foreground">None found</span>
                    )}
                  </div>
                </div>

                {/* Additional Metadata */}
                {entity.umls_cui && (
                  <div className="pt-2 border-t border-border">
                    <span className="text-xs text-muted-foreground">
                      UMLS CUI:{' '}
                      <span className="font-mono font-semibold text-purple-600">
                        {entity.umls_cui}
                      </span>
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-sm text-muted-foreground">
            <Stethoscope className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No condition entities with ICD codes found in this trial.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
