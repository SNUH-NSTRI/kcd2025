'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CheckCircle2, XCircle, Database } from 'lucide-react';
import type { SchemaData } from '@/remote/types/studies';

interface ParsedSchemaPanelProps {
  schema: SchemaData;
}

export function ParsedSchemaPanel({ schema }: ParsedSchemaPanelProps) {
  return (
    <Card className="h-full overflow-auto">
      <CardHeader>
        <CardTitle>Parsed Trial Schema</CardTitle>
        <CardDescription>
          AI-generated structured criteria from {schema.provenance?.method || 'LLM analysis'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="criteria" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="criteria">Inclusion/Exclusion</TabsTrigger>
            <TabsTrigger value="mapping">Medical Entities</TabsTrigger>
          </TabsList>

          {/* Criteria Tab */}
          <TabsContent value="criteria" className="space-y-4 mt-4">
            {/* Inclusion Criteria */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <h3 className="text-sm font-semibold">Inclusion Criteria</h3>
                <Badge variant="secondary" className="text-xs">{schema.inclusion.length} criteria</Badge>
              </div>

              {schema.inclusion.map((criterion) => (
                <div key={criterion.id} className="border-l-4 border-green-600 pl-4 py-2 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className="font-mono text-xs">{criterion.id}</Badge>
                    <Badge variant="secondary">{criterion.category}</Badge>
                    <Badge variant="default" className="text-xs">{criterion.kind}</Badge>
                  </div>
                  <p className="text-sm font-medium">{criterion.description}</p>

                  {/* Extracted Entities */}
                  {criterion.entities && criterion.entities.length > 0 && (
                    <div className="bg-muted rounded-md p-3 space-y-2">
                      <p className="text-xs font-semibold text-muted-foreground">
                        Extracted Entities ({criterion.entities.length}):
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {criterion.entities.map((entity, idx) => (
                          <Badge
                            key={idx}
                            variant={entity.code_system ? 'default' : 'secondary'}
                            className="text-xs"
                            title={`Domain: ${entity.domain}\nType: ${entity.type}\nConfidence: ${(entity.confidence * 100).toFixed(0)}%${entity.code_system ? `\nCode: ${entity.code_system}:${entity.primary_code}` : ''}`}
                          >
                            <span className="font-medium">{entity.text}</span>
                            {entity.code_system && (
                              <span className="ml-1 opacity-70 text-[10px]">
                                {entity.code_system}
                              </span>
                            )}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Exclusion Criteria */}
            <div className="space-y-3 pt-4">
              <div className="flex items-center gap-2">
                <XCircle className="w-5 h-5 text-red-600" />
                <h3 className="text-sm font-semibold">Exclusion Criteria</h3>
                <Badge variant="secondary" className="text-xs">{schema.exclusion.length} criteria</Badge>
              </div>

              {schema.exclusion.map((criterion) => (
                <div key={criterion.id} className="border-l-4 border-red-600 pl-4 py-2 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className="font-mono text-xs">{criterion.id}</Badge>
                    <Badge variant="secondary">{criterion.category}</Badge>
                    <Badge variant="default" className="text-xs">{criterion.kind}</Badge>
                  </div>
                  <p className="text-sm font-medium">{criterion.description}</p>

                  {/* Extracted Entities */}
                  {criterion.entities && criterion.entities.length > 0 && (
                    <div className="bg-muted rounded-md p-3 space-y-2">
                      <p className="text-xs font-semibold text-muted-foreground">
                        Extracted Entities ({criterion.entities.length}):
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {criterion.entities.map((entity, idx) => (
                          <Badge
                            key={idx}
                            variant={entity.code_system ? 'default' : 'secondary'}
                            className="text-xs"
                            title={`Domain: ${entity.domain}\nType: ${entity.type}\nConfidence: ${(entity.confidence * 100).toFixed(0)}%${entity.code_system ? `\nCode: ${entity.code_system}:${entity.primary_code}` : ''}`}
                          >
                            <span className="font-medium">{entity.text}</span>
                            {entity.code_system && (
                              <span className="ml-1 opacity-70 text-[10px]">
                                {entity.code_system}
                              </span>
                            )}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </TabsContent>

          {/* Medical Entities Tab */}
          <TabsContent value="mapping" className="space-y-4 mt-4">
            <div className="flex items-center gap-2 mb-3">
              <Database className="w-5 h-5 text-blue-600" />
              <h3 className="text-sm font-semibold">All Extracted Medical Entities</h3>
            </div>

            <div className="space-y-3">
              {/* Group all entities by domain */}
              {(() => {
                const allEntities = [
                  ...schema.inclusion.flatMap((c) => c.entities || []),
                  ...schema.exclusion.flatMap((c) => c.entities || []),
                ];
                const entityGroups = allEntities.reduce((acc, entity) => {
                  const domain = entity.domain || 'Unknown';
                  if (!acc[domain]) acc[domain] = [];
                  acc[domain].push(entity);
                  return acc;
                }, {} as Record<string, typeof allEntities>);

                return Object.entries(entityGroups).map(([domain, entities]) => (
                  <div key={domain} className="bg-muted rounded-md p-4 space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-semibold">{domain}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {entities.length} entities
                      </span>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {entities.map((entity, idx) => (
                        <div
                          key={idx}
                          className="flex items-start justify-between gap-2 text-xs bg-background p-2 rounded"
                        >
                          <div className="flex-1">
                            <div className="font-medium">{entity.text}</div>
                            <div className="text-muted-foreground">
                              {entity.standard_name}
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <Badge variant={entity.code_system ? 'default' : 'secondary'} className="text-[10px]">
                              {entity.type}
                            </Badge>
                            {entity.code_system && entity.primary_code && (
                              <div className="text-[10px] font-mono text-blue-600">
                                {entity.code_system}:{entity.primary_code}
                              </div>
                            )}
                            {entity.umls_cui && (
                              <div className="text-[10px] font-mono text-purple-600">
                                UMLS:{entity.umls_cui}
                              </div>
                            )}
                            <div className="text-[10px] text-muted-foreground">
                              {(entity.confidence * 100).toFixed(0)}% confidence
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ));
              })()}
            </div>

            {schema.features && schema.features.length > 0 && (
              <>
                <div className="flex items-center gap-2 mt-6 mb-3">
                  <Database className="w-5 h-5 text-blue-600" />
                  <h3 className="text-sm font-semibold">MIMIC-IV Feature Mapping</h3>
                  <Badge variant="secondary" className="text-xs">{schema.features.length} features</Badge>
                </div>

                <div className="space-y-3">
                  {schema.features.map((feature) => (
                    <div key={feature.name} className="bg-muted rounded-md p-4 space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="secondary" className="font-mono">{feature.name}</Badge>
                        <span className="text-xs text-muted-foreground">
                          → {feature.source}
                        </span>
                        {feature.unit && (
                          <Badge variant="outline" className="text-xs">{feature.unit}</Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {feature.metadata.description}
                      </p>
                      <div className="flex flex-col gap-1">
                        {feature.metadata.table && (
                          <div className="text-xs font-mono">
                            <span className="text-blue-600">Table:</span> {feature.metadata.table}
                          </div>
                        )}
                        {feature.metadata.column && (
                          <div className="text-xs font-mono">
                            <span className="text-blue-600">Column:</span> {feature.metadata.column}
                          </div>
                        )}
                        {feature.metadata.itemid && (
                          <div className="text-xs font-mono">
                            <span className="text-blue-600">Item ID:</span> {feature.metadata.itemid}
                          </div>
                        )}
                        {feature.timeWindow && (
                          <div className="text-xs font-mono">
                            <span className="text-blue-600">Time Window:</span> [{feature.timeWindow[0]}, {feature.timeWindow[1]}] hours
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
