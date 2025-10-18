'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CheckCircle2, XCircle, FileText, Code2, Database } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getStudyCorpus, getStudySchema } from '@/remote/api/studies';

interface SchemaDemoViewProps {
  nctId: string;
}

export function SchemaDemoView({ nctId }: SchemaDemoViewProps) {
  const [schemaData, setSchemaData] = useState<any>(null);
  const [corpusData, setCorpusData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        // Use real backend API
        const [schema, corpus] = await Promise.all([
          getStudySchema(nctId),
          getStudyCorpus(nctId)
        ]);

        setSchemaData(schema);
        setCorpusData(corpus);
      } catch (err) {
        console.error('Failed to load study data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [nctId]);

  if (loading) {
    return <div className="text-center py-8">Loading schema data...</div>;
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-destructive mb-2">Error loading data</p>
        <p className="text-sm text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (!schemaData || !corpusData) {
    return <div className="text-center py-8 text-muted-foreground">No data available</div>;
  }

  const trial = corpusData.documents[0];
  const eligibilityText = trial.metadata.eligibility.eligibilityCriteria;

  return (
    <div className="space-y-6">
      {/* Trial Info */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <CardTitle className="text-xl">{trial.title}</CardTitle>
            <Badge variant="secondary">{trial.metadata.nct_id}</Badge>
          </div>
          <CardDescription>
            Phase: {trial.metadata.design.phases.join(', ')} |
            Status: {trial.metadata.status} |
            Sponsor: {trial.metadata.sponsors.leadSponsor.name}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Main Content */}
      <Tabs defaultValue="parsed" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="original" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Original Text
          </TabsTrigger>
          <TabsTrigger value="parsed" className="flex items-center gap-2">
            <Code2 className="w-4 h-4" />
            Parsed Criteria
          </TabsTrigger>
          <TabsTrigger value="mapping" className="flex items-center gap-2">
            <Database className="w-4 h-4" />
            EHR Mapping
          </TabsTrigger>
        </TabsList>

        {/* Original Text Tab */}
        <TabsContent value="original" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Eligibility Criteria (Unstructured)</CardTitle>
              <CardDescription>
                Original text from ClinicalTrials.gov protocol
              </CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg font-mono">
                {eligibilityText}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Parsed Schema Tab */}
        <TabsContent value="parsed" className="space-y-4 mt-4">
          {/* Inclusion Criteria */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <CardTitle>Inclusion Criteria</CardTitle>
              </div>
              <CardDescription>
                Structured requirements for patient eligibility ({schemaData.inclusion.length} criteria)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {schemaData.inclusion.map((criterion: any) => (
                <div key={criterion.id} className="border-l-4 border-green-600 pl-4 py-2 space-y-2">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline" className="font-mono text-xs">{criterion.id}</Badge>
                        <Badge variant="secondary">{criterion.category}</Badge>
                        <Badge variant="default" className="text-xs">{criterion.kind}</Badge>
                      </div>
                      <p className="text-sm font-medium">
                        {criterion.description}
                      </p>
                    </div>
                  </div>

                  {/* Parsed Concept */}
                  <div className="bg-muted rounded-md p-3 space-y-1.5">
                    <div className="text-xs font-mono">
                      <span className="text-blue-600 font-semibold">field:</span>{' '}
                      <span className="text-foreground">{criterion.value.field}</span>
                    </div>
                    <div className="text-xs font-mono">
                      <span className="text-blue-600 font-semibold">operator:</span>{' '}
                      <span className="text-foreground">{criterion.value.op}</span>
                    </div>
                    <div className="text-xs font-mono">
                      <span className="text-blue-600 font-semibold">value:</span>{' '}
                      <span className="text-foreground">{criterion.value.value}</span>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Exclusion Criteria */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <XCircle className="w-5 h-5 text-red-600" />
                <CardTitle>Exclusion Criteria</CardTitle>
              </div>
              <CardDescription>
                Conditions that disqualify patients from the trial ({schemaData.exclusion.length} criteria)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {schemaData.exclusion.map((criterion: any) => (
                <div key={criterion.id} className="border-l-4 border-red-600 pl-4 py-2 space-y-2">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline" className="font-mono text-xs">{criterion.id}</Badge>
                        <Badge variant="secondary">{criterion.category}</Badge>
                        <Badge variant="default" className="text-xs">{criterion.kind}</Badge>
                      </div>
                      <p className="text-sm font-medium">
                        {criterion.description}
                      </p>
                    </div>
                  </div>

                  {/* Parsed Concept */}
                  <div className="bg-muted rounded-md p-3 space-y-1.5">
                    <div className="text-xs font-mono">
                      <span className="text-blue-600 font-semibold">field:</span>{' '}
                      <span className="text-foreground">{criterion.value.field}</span>
                    </div>
                    <div className="text-xs font-mono">
                      <span className="text-blue-600 font-semibold">operator:</span>{' '}
                      <span className="text-foreground">{criterion.value.op}</span>
                    </div>
                    <div className="text-xs font-mono">
                      <span className="text-blue-600 font-semibold">value:</span>{' '}
                      <span className="text-foreground">{criterion.value.value}</span>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* EHR Mapping Tab */}
        <TabsContent value="mapping" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>MIMIC-IV Feature Mapping</CardTitle>
              <CardDescription>
                How each criterion maps to real-world EHR database tables
              </CardDescription>
            </CardHeader>
            <CardContent>
              {schemaData.features && schemaData.features.length > 0 ? (
                <div className="space-y-3">
                  {schemaData.features.map((feature: any) => (
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
                        {feature.metadata?.description || 'No description'}
                      </p>
                      <div className="flex flex-col gap-1">
                        {feature.metadata?.table && (
                          <div className="text-xs font-mono">
                            <span className="text-blue-600">Table:</span> {feature.metadata.table}
                          </div>
                        )}
                        {feature.metadata?.column && (
                          <div className="text-xs font-mono">
                            <span className="text-blue-600">Column:</span> {feature.metadata.column}
                          </div>
                        )}
                        {feature.metadata?.itemid && (
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
              ) : (
                <p className="text-sm text-muted-foreground">No feature mappings available yet</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
