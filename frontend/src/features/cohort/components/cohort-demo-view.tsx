'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Filter, Users, TrendingDown, Database } from 'lucide-react';
import { useEffect, useState } from 'react';
import { cohortApi } from '@/remote/api/cohort';

interface CohortDemoViewProps {
  nctId: string;
}

interface SamplePatient {
  subject_id: number;
  age_at_admission: number;
  gender: string;
  treatment_group: number;
  icu_intime: string;
  icu_outtime: string;
  los: number; // Length of stay
  any_vasopressor: number;
  mortality: number;
}

export function CohortDemoView({ nctId }: CohortDemoViewProps) {
  const [cohortData, setCohortData] = useState<any>(null);
  const [samplePatients, setSamplePatients] = useState<SamplePatient[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingPatients, setLoadingPatients] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        // Load all data from backend API (real-time ~50ms)
        // Works for ANY cohort, not just ones with fixtures!
        const apiResponse = await cohortApi.getSummary(nctId, 'hydrocortisonenasucc');

        if (apiResponse.status === 'success' && apiResponse.data) {
          const { attrition, characteristics } = apiResponse.data;

          const transformedData = {
            summary: {
              initialPatientCount: attrition.initial_count,
              finalCohortSize: attrition.total,
              attritionFunnel: attrition.funnel,
            },
            cohort_characteristics: {
              mean_age: characteristics.age.mean,
              age_std: characteristics.age.std,
              gender_distribution: {
                male: characteristics.gender.M,
                female: characteristics.gender.F,
              },
              treatment_groups: {
                control: attrition.control,
                hydrocortisone: attrition.treatment,
              },
            },
          };

          setCohortData(transformedData);
        }
      } catch (error) {
        console.error('Failed to load cohort data:', error);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [nctId]);

  // Fetch sample patients from backend when user views the Patients tab
  const loadSamplePatients = async () => {
    if (samplePatients.length > 0) return; // Already loaded

    setLoadingPatients(true);
    try {
      const response = await cohortApi.getSamplePatients(nctId, 'hydrocortisonenasucc', 10);
      if (response.status === 'success' && response.data) {
        setSamplePatients(response.data.patients);
      }
    } catch (error) {
      console.error('Failed to load sample patients:', error);
    } finally {
      setLoadingPatients(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading cohort data...</div>;
  }

  if (!cohortData) {
    return <div className="text-center py-8 text-muted-foreground">No cohort data available</div>;
  }

  const { summary, cohort_characteristics, sample_patients } = cohortData;
  const retentionRate = ((summary.finalCohortSize / summary.initialPatientCount) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Initial Population</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.initialPatientCount.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              {cohortData.source_database}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Final Cohort Size</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.finalCohortSize.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              {retentionRate}% retention rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Filtering Steps</CardTitle>
            <Filter className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.attritionFunnel.length - 1}</div>
            <p className="text-xs text-muted-foreground">
              Inclusion + Exclusion criteria
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="funnel" className="w-full" onValueChange={(value) => {
        if (value === 'patients') {
          loadSamplePatients();
        }
      }}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="funnel" className="flex items-center gap-2">
            <TrendingDown className="w-4 h-4" />
            Attrition Funnel
          </TabsTrigger>
          <TabsTrigger value="characteristics" className="flex items-center gap-2">
            <Database className="w-4 h-4" />
            Characteristics
          </TabsTrigger>
        </TabsList>

        {/* Attrition Funnel Tab */}
        <TabsContent value="funnel" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Patient Selection Flowchart</CardTitle>
              <CardDescription>
                Step-by-step reduction from initial population to final cohort
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {summary.attritionFunnel.map((step: any, index: number) => {
                  // Use criteria_type from metadata if available, otherwise infer from criteriaId
                  const criteriaType = step.criteria_type || (step.criteriaId.startsWith('EXCLUDE_') ? 'exclusion' : 'inclusion');
                  const isExclusion = criteriaType === 'exclusion';
                  const isInclusion = criteriaType === 'inclusion';
                  const isInitial = step.criteriaId === 'INITIAL';
                  const isFinal = step.criteriaId === 'FINAL';
                  const prevCount = index > 0 ? summary.attritionFunnel[index - 1].patients_remaining : 0;
                  const removed = prevCount - step.patients_remaining;
                  const removalRate = prevCount > 0 ? ((removed / prevCount) * 100).toFixed(1) : '0.0';

                  return (
                    <div key={step.step} className="relative">
                      {/* Step Item */}
                      <div className={`flex items-center gap-4 p-4 rounded-lg border ${
                        isInitial ? 'bg-blue-50 border-blue-200' :
                        isFinal ? 'bg-blue-50 border-blue-200' :
                        isExclusion ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'
                      }`}>
                        {/* Step Number */}
                        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                          isInitial ? 'bg-blue-500 text-white' :
                          isFinal ? 'bg-blue-600 text-white' :
                          isExclusion ? 'bg-red-500 text-white' : 'bg-green-600 text-white'
                        }`}>
                          {step.step}
                        </div>

                        {/* Description */}
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs font-mono">
                              {step.criteriaId}
                            </Badge>
                            {isExclusion && <Badge variant="destructive" className="text-xs bg-red-600">Exclusion</Badge>}
                            {isInclusion && (
                              <Badge variant="default" className="text-xs bg-green-600">Inclusion</Badge>
                            )}
                          </div>
                          <p className="text-sm font-medium">{step.description}</p>
                          {/* Show exclusion reason for exclusion steps */}
                          {isExclusion && step.exclusion_reason && (
                            <p className="text-xs text-red-600 italic">→ {step.exclusion_reason}</p>
                          )}
                          {/* Show exclusion reason for inclusion steps (what was excluded) */}
                          {isInclusion && step.exclusion_reason && (
                            <p className="text-xs text-muted-foreground italic">→ Excluded: {step.exclusion_reason}</p>
                          )}
                        </div>

                        {/* Patient Count */}
                        <div className="text-right">
                          <div className="text-2xl font-bold">{step.patients_remaining.toLocaleString()}</div>
                          {!isInitial && (
                            <div className="text-xs text-muted-foreground">
                              -{removed.toLocaleString()} ({removalRate}%)
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Connector Arrow */}
                      {index < summary.attritionFunnel.length - 1 && (
                        <div className="flex justify-center py-2">
                          <div className="w-0.5 h-4 bg-border"></div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Characteristics Tab */}
        <TabsContent value="characteristics" className="space-y-4 mt-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Demographics</CardTitle>
                <CardDescription>Age and gender distribution</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Mean Age</span>
                    <span className="font-medium">{cohort_characteristics.mean_age} years</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Age SD</span>
                    <span className="font-medium">± {cohort_characteristics.age_std} years</span>
                  </div>
                </div>

                <div className="pt-4 border-t space-y-2">
                  <p className="text-sm font-medium">Gender Distribution</p>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1">
                        <div className="flex justify-between text-xs mb-1">
                          <span>Male</span>
                          <span className="font-mono">{cohort_characteristics.gender_distribution.male.toLocaleString()}</span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500"
                            style={{
                              width: `${(cohort_characteristics.gender_distribution.male / summary.finalCohortSize) * 100}%`
                            }}
                          />
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1">
                        <div className="flex justify-between text-xs mb-1">
                          <span>Female</span>
                          <span className="font-mono">{cohort_characteristics.gender_distribution.female.toLocaleString()}</span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-pink-500"
                            style={{
                              width: `${(cohort_characteristics.gender_distribution.female / summary.finalCohortSize) * 100}%`
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Treatment Assignment</CardTitle>
                <CardDescription>Randomization to study arms</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium">Control Group</span>
                        <span className="font-mono">{cohort_characteristics.treatment_groups.control.toLocaleString()}</span>
                      </div>
                      <div className="h-3 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gray-500"
                          style={{
                            width: `${(cohort_characteristics.treatment_groups.control / summary.finalCohortSize) * 100}%`
                          }}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {((cohort_characteristics.treatment_groups.control / summary.finalCohortSize) * 100).toFixed(1)}% of cohort
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium">Hydrocortisone Group</span>
                        <span className="font-mono">{cohort_characteristics.treatment_groups.hydrocortisone.toLocaleString()}</span>
                      </div>
                      <div className="h-3 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-600"
                          style={{
                            width: `${(cohort_characteristics.treatment_groups.hydrocortisone / summary.finalCohortSize) * 100}%`
                          }}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {((cohort_characteristics.treatment_groups.hydrocortisone / summary.finalCohortSize) * 100).toFixed(1)}% of cohort
                      </p>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Balance Ratio</span>
                    <span className="font-medium">
                      {(cohort_characteristics.treatment_groups.control / cohort_characteristics.treatment_groups.hydrocortisone).toFixed(2)}:1
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
