'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Search, Loader2, ExternalLink, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';

import {
  searchClinicalTrials,
  getTrialDetails,
  formatTrialStatus,
  formatPhase,
  getStatusColor,
  getPhaseColor,
  type TrialSummary,
  type TrialDetail,
} from '@/remote/api/clinicaltrials';
import { CreateStudyDialog } from '@/features/flow/components/create-study-dialog';

// Mock data for default trials (for preview) - Sepsis-related trials only
const MOCK_DEFAULT_TRIALS: TrialSummary[] = [
  {
    nctId: 'NCT03389555',
    briefTitle: 'Adjunctive Corticosteroid Treatment in Critically Ill Patients With Septic Shock (ADRENAL)',
    officialTitle: 'Adjunctive Glucocorticoid Therapy in Patients with Septic Shock',
    overallStatus: 'COMPLETED',
    phase: 'PHASE3',
    studyType: 'INTERVENTIONAL',
    enrollment: 3658,
    startDate: '2013-03-01',
    completionDate: '2017-04-01',
    conditions: ['Septic Shock', 'Sepsis', 'Critical Illness'],
    interventions: [
      {
        type: 'DRUG',
        name: 'Hydrocortisone',
        description: 'Hydrocortisone 200mg/day continuous infusion for 7 days or until ICU discharge',
      },
      {
        type: 'DRUG',
        name: 'Placebo',
        description: 'Matching placebo (normal saline)',
      },
    ],
    sponsor: {
      lead: 'The George Institute',
      collaborators: ['Australian and New Zealand Intensive Care Society', 'NHMRC'],
    },
    summary: 'ADRENAL trial evaluates the effect of hydrocortisone versus placebo on mortality in patients with septic shock.',
    eligibilityCriteria: 'Inclusion: Adult patients (≥18 years), Suspected/confirmed infection, Receiving vasopressor within 24h of ICU admission. Exclusion: Pregnancy, Kidney stones within past year, ESRD requiring dialysis, G6PD deficiency, Hemochromatosis, Death within 24 hours of ICU admission',
    sex: 'All',
    minimumAge: '18 Years',
    maximumAge: 'N/A',
  },
  {
    nctId: 'NCT03509350',
    briefTitle: 'Vitamin C, Thiamine and Steroids in Sepsis (VICTAS)',
    officialTitle: 'Vitamin C, Thiamine and Steroids in Sepsis: A Randomized Controlled Trial',
    overallStatus: 'COMPLETED',
    phase: 'PHASE2',
    studyType: 'INTERVENTIONAL',
    enrollment: 501,
    startDate: '2018-08-15',
    completionDate: '2019-07-31',
    conditions: ['Sepsis', 'Septic Shock'],
    interventions: [
      {
        type: 'DRUG',
        name: 'Vitamin C, Thiamine, Hydrocortisone',
        description: 'Vitamin C 1.5g IV every 6 hours, Thiamine 200mg IV every 12 hours, Hydrocortisone 50mg IV every 6 hours for 96 hours',
      },
      {
        type: 'DRUG',
        name: 'Placebo',
        description: 'Matching placebo',
      },
    ],
    sponsor: {
      lead: 'Emory University',
      collaborators: ['National Heart, Lung, and Blood Institute (NHLBI)'],
    },
    summary: 'VICTAS evaluates the combination of vitamin C, thiamine, and hydrocortisone in patients with sepsis and septic shock.',
    eligibilityCriteria: 'Inclusion: Sepsis or septic shock, vasopressor requirement. Exclusion: Known allergy to study medications, ESKD on dialysis.',
    sex: 'All',
    minimumAge: '18 Years',
    maximumAge: 'N/A',
  },
  {
    nctId: 'NCT03258684',
    briefTitle: 'Hydrocortisone, Vitamin C, and Thiamine for Sepsis and Septic Shock (HYVCTTSSS)',
    officialTitle: 'Efficacy of Vitamin C, Hydrocortisone, and Thiamine in Patients With Septic Shock',
    overallStatus: 'COMPLETED',
    phase: 'PHASE2',
    studyType: 'INTERVENTIONAL',
    enrollment: 200,
    startDate: '2017-09-25',
    completionDate: '2019-01-07',
    conditions: ['Septic Shock', 'Sepsis', 'Critical Illness'],
    interventions: [
      {
        type: 'DRUG',
        name: 'HAT Therapy',
        description: 'Hydrocortisone 50mg IV q6h, Ascorbic acid 1.5g IV q6h, Thiamine 200mg IV q12h for 4 days',
      },
      {
        type: 'DRUG',
        name: 'Placebo',
        description: 'Matching placebo for all three components',
      },
    ],
    sponsor: {
      lead: 'Seoul National University Hospital',
      collaborators: [],
    },
    summary: 'This trial investigates the efficacy of combined hydrocortisone, ascorbic acid, and thiamine (HAT therapy) in septic shock patients.',
    eligibilityCriteria: 'Inclusion: Septic shock requiring vasopressor, ICU admission. Exclusion: Pregnancy, active bleeding, ESRD.',
    sex: 'All',
    minimumAge: '18 Years',
    maximumAge: 'N/A',
  },
  {
    nctId: 'NCT03422159',
    briefTitle: 'Metabolic Resuscitation Using Ascorbic Acid, Thiamine, and Glucocorticoids in Sepsis (ORANGES)',
    officialTitle: 'Metabolic Resuscitation Using Ascorbic Acid, Thiamine, and Glucocorticoids in Sepsis',
    overallStatus: 'COMPLETED',
    phase: 'PHASE2',
    studyType: 'INTERVENTIONAL',
    enrollment: 137,
    startDate: '2018-02-01',
    completionDate: '2019-06-30',
    conditions: ['Sepsis', 'Septic Shock', 'Severe Sepsis'],
    interventions: [
      {
        type: 'DRUG',
        name: 'Metabolic Resuscitation',
        description: 'Ascorbic acid 1.5g IV q6h, Thiamine 200mg IV q12h, Hydrocortisone 50mg IV q6h',
      },
      {
        type: 'OTHER',
        name: 'Standard Care',
        description: 'Standard sepsis management without metabolic resuscitation',
      },
    ],
    sponsor: {
      lead: 'Louisiana State University Health Sciences Center',
      collaborators: [],
    },
    summary: 'ORANGES trial evaluates metabolic resuscitation with vitamin C, thiamine, and steroids in sepsis patients.',
    eligibilityCriteria: 'Inclusion: Severe sepsis or septic shock, age ≥18. Exclusion: Pregnancy, advanced directives limiting care.',
    sex: 'All',
    minimumAge: '18 Years',
    maximumAge: 'N/A',
  },
  {
    nctId: 'NCT03333278',
    briefTitle: 'Vitamin C, Hydrocortisone and Thiamine in Septic Shock (VITAMINS)',
    officialTitle: 'The Vitamin C, Hydrocortisone and Thiamine in Patients With Septic Shock Trial',
    overallStatus: 'COMPLETED',
    phase: 'PHASE2',
    studyType: 'INTERVENTIONAL',
    enrollment: 216,
    startDate: '2018-05-08',
    completionDate: '2019-07-09',
    conditions: ['Septic Shock', 'Sepsis'],
    interventions: [
      {
        type: 'DRUG',
        name: 'Vitamin C + Hydrocortisone + Thiamine',
        description: 'Vitamin C 1.5g IV q6h, Hydrocortisone 50mg IV q6h, Thiamine 200mg IV q12h for 4 days',
      },
      {
        type: 'DRUG',
        name: 'Placebo',
        description: 'Normal saline placebo',
      },
    ],
    sponsor: {
      lead: 'Australian and New Zealand Intensive Care Society Clinical Trials Group',
      collaborators: [],
    },
    summary: 'VITAMINS trial evaluates the combination of vitamin C, hydrocortisone, and thiamine in patients with septic shock.',
    eligibilityCriteria: 'Inclusion: Septic shock requiring vasopressors, within 24h of ICU admission. Exclusion: Known allergy to study drugs.',
    sex: 'All',
    minimumAge: '18 Years',
    maximumAge: 'N/A',
  },
  {
    nctId: 'NCT03380507',
    briefTitle: 'Hydrocortisone, Vitamin C and Thiamine for Septic Shock (HYVITS)',
    officialTitle: 'Evaluation of Hydrocortisone, Vitamin C and Thiamine for the Treatment of Septic Shock',
    overallStatus: 'COMPLETED',
    phase: 'PHASE2',
    studyType: 'INTERVENTIONAL',
    enrollment: 88,
    startDate: '2018-03-01',
    completionDate: '2019-08-31',
    conditions: ['Septic Shock', 'Sepsis'],
    interventions: [
      {
        type: 'DRUG',
        name: 'Triple Therapy',
        description: 'Hydrocortisone 50mg IV q6h, Vitamin C 1.5g IV q6h, Thiamine 200mg IV q12h for 4 days',
      },
      {
        type: 'DRUG',
        name: 'Standard Care',
        description: 'Standard septic shock management',
      },
    ],
    sponsor: {
      lead: 'Cleveland Clinic',
      collaborators: [],
    },
    summary: 'HYVITS evaluates triple therapy with hydrocortisone, vitamin C, and thiamine in septic shock patients.',
    eligibilityCriteria: 'Inclusion: Septic shock, vasopressor requirement, age ≥18. Exclusion: Pregnancy, active malignancy.',
    sex: 'All',
    minimumAge: '18 Years',
    maximumAge: 'N/A',
  },
  {
    nctId: 'NCT03872011',
    briefTitle: 'Early Administration of Hydrocortisone, Vitamin C, and Thiamine in Septic Shock',
    officialTitle: 'Early Administration of Hydrocortisone, Vitamin C, and Thiamine in Adult Patients With Septic Shock: A Randomized Controlled Trial',
    overallStatus: 'COMPLETED',
    phase: 'PHASE2',
    studyType: 'INTERVENTIONAL',
    enrollment: 80,
    startDate: '2019-02-01',
    completionDate: '2021-06-30',
    conditions: ['Septic Shock', 'Sepsis', 'Multiple Organ Failure'],
    interventions: [
      {
        type: 'DRUG',
        name: 'HVT Protocol',
        description: 'Hydrocortisone 50mg IV q6h, Vitamin C 1.5g IV q6h, Thiamine 200mg IV q12h within 6h of shock onset',
      },
      {
        type: 'DRUG',
        name: 'Placebo',
        description: 'Placebo matching all components',
      },
    ],
    sponsor: {
      lead: 'Cairo University',
      collaborators: [],
    },
    summary: 'This RCT evaluates early administration of hydrocortisone, vitamin C, and thiamine in adult patients with septic shock.',
    eligibilityCriteria: 'Inclusion: Septic shock within 6h, age ≥18, vasopressor requirement. Exclusion: DNR orders, pregnancy.',
    sex: 'All',
    minimumAge: '18 Years',
    maximumAge: 'N/A',
  },
];

function CTSearchPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [searchQuery, setSearchQuery] = useState('');
  const [condition, setCondition] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedPhase, setSelectedPhase] = useState<string>('all');
  const [selectedDiseaseCategory, setSelectedDiseaseCategory] = useState<string>('all');
  const [activeQuery, setActiveQuery] = useState<{
    query?: string;
    condition?: string;
    status?: string[];
    phase?: string[];
  }>({});

  const [selectedNctId, setSelectedNctId] = useState<string | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Derive Create Study dialog state from URL
  const createFromNCT = searchParams.get('createFromNCT');
  const isCreateDialogOpen = !!createFromNCT;

  // Query for search results (when user searches)
  const { data: searchData, isLoading: searchLoading, error: searchError } = useQuery({
    queryKey: ['ct-search', activeQuery],
    queryFn: () =>
      searchClinicalTrials({
        query: activeQuery.query,
        condition: activeQuery.condition,
        status: activeQuery.status,
        phase: activeQuery.phase,
        page_size: 20,
      }),
    enabled: Object.keys(activeQuery).length > 0,
  });

  // Query for trial details (when user clicks View Details)
  const { data: detailData, isLoading: detailLoading } = useQuery({
    queryKey: ['trial-detail', selectedNctId],
    queryFn: () => getTrialDetails(selectedNctId!),
    enabled: !!selectedNctId && isDetailOpen,
  });

  // Use mock data for default trials (no API call needed for demo)
  const defaultData = MOCK_DEFAULT_TRIALS;

  // Extract unique disease categories from all trials
  const diseaseCategories = Array.from(
    new Set(
      defaultData.flatMap((trial) => trial.conditions || [])
    )
  ).sort();

  // Use search results if available, otherwise show default trials
  let rawData = searchData || { studies: defaultData, total_count: defaultData.length };

  // Apply disease category filter to the displayed data
  const filteredStudies = selectedDiseaseCategory === 'all'
    ? rawData.studies
    : rawData.studies.filter((trial) =>
        trial.conditions?.some((condition) =>
          condition.toLowerCase().includes(selectedDiseaseCategory.toLowerCase())
        )
      );

  const data = {
    studies: filteredStudies,
    total_count: filteredStudies.length
  };

  const isLoading = searchLoading;
  const error = searchError;

  const trial = detailData?.study;

  const handleSearch = () => {
    const newQuery: {
      query?: string;
      condition?: string;
      status?: string[];
      phase?: string[];
    } = {};

    if (searchQuery.trim()) {
      newQuery.query = searchQuery.trim();
    }
    if (condition.trim()) {
      newQuery.condition = condition.trim();
    }
    if (selectedStatus !== 'all') {
      newQuery.status = [selectedStatus];
    }
    if (selectedPhase !== 'all') {
      newQuery.phase = [selectedPhase];
    }

    setActiveQuery(newQuery);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleViewDetails = (nctId: string) => {
    setSelectedNctId(nctId);
    setIsDetailOpen(true);
  };

  const handleCloseDetail = () => {
    setIsDetailOpen(false);
    setSelectedNctId(null);
  };

  const handleCloseCreateDialog = () => {
    // Clean up URL parameter
    router.replace('/ct-search', { scroll: false });
  };

  return (
    <>
      {/* Create Study Dialog - Controlled by URL param */}
      <CreateStudyDialog
        open={isCreateDialogOpen}
        onOpenChange={(open) => {
          if (!open) {
            handleCloseCreateDialog();
          }
        }}
        prefilledNctId={createFromNCT || undefined}
      />

      <section className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm uppercase text-muted-foreground">Clinical Trials Database</p>
          <h1 className="text-3xl font-bold">NCT Registry Search</h1>
          <p className="text-muted-foreground">
            Search and discover clinical trials by NCT ID, condition, or intervention from ClinicalTrials.gov
          </p>
        </header>

        {/* Search Bar */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Search Criteria</CardTitle>
            <CardDescription>
              Enter search terms or use filters to find relevant clinical trials
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Main Search Input */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Try NCT03389555, or search by keyword, condition, intervention..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="pl-9"
                />
              </div>
              <Button onClick={handleSearch} className="gap-2">
                <Search className="h-4 w-4" />
                Search
              </Button>
            </div>

            {/* Filters Row */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Condition</label>
                <Input
                  placeholder="e.g., Heart Failure"
                  value={condition}
                  onChange={(e) => setCondition(e.target.value)}
                  onKeyPress={handleKeyPress}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Disease Category</label>
                <Select value={selectedDiseaseCategory} onValueChange={setSelectedDiseaseCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder="All categories" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    {diseaseCategories.map((category) => (
                      <SelectItem key={category} value={category}>
                        {category}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Status</label>
                <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                  <SelectTrigger>
                    <SelectValue placeholder="All statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="RECRUITING">Recruiting</SelectItem>
                    <SelectItem value="ACTIVE_NOT_RECRUITING">Active, not recruiting</SelectItem>
                    <SelectItem value="COMPLETED">Completed</SelectItem>
                    <SelectItem value="TERMINATED">Terminated</SelectItem>
                    <SelectItem value="SUSPENDED">Suspended</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Phase</label>
                <Select value={selectedPhase} onValueChange={setSelectedPhase}>
                  <SelectTrigger>
                    <SelectValue placeholder="All phases" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Phases</SelectItem>
                    <SelectItem value="PHASE1">Phase 1</SelectItem>
                    <SelectItem value="PHASE2">Phase 2</SelectItem>
                    <SelectItem value="PHASE3">Phase 3</SelectItem>
                    <SelectItem value="PHASE4">Phase 4</SelectItem>
                    <SelectItem value="N/A">Not Applicable</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Results Section */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && (
          <Card className="border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive">Search Error</CardTitle>
              <CardDescription>
                {error instanceof Error ? error.message : 'Failed to search trials'}
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {data && !isLoading && (
          <>
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Found <span className="font-semibold text-foreground">{data.total_count}</span> trials
              </p>
            </div>

            <div className="space-y-3">
              {data.studies.map((trial: TrialSummary) => (
                <Card key={trial.nctId} className="hover:bg-accent/50 transition-colors">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      {/* Left: Trial Info */}
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-3">
                          <CardTitle className="text-lg font-semibold">{trial.nctId}</CardTitle>
                          <div className="flex gap-1.5">
                            <Badge variant={getPhaseColor(trial.phase)} className="text-xs">
                              {formatPhase(trial.phase)}
                            </Badge>
                            <Badge variant={getStatusColor(trial.overallStatus)} className="text-xs">
                              {formatTrialStatus(trial.overallStatus)}
                            </Badge>
                          </div>
                        </div>

                        <p className="text-sm text-foreground line-clamp-2">
                          {trial.briefTitle}
                        </p>

                        <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                          {trial.conditions && trial.conditions.length > 0 && (
                            <div className="flex items-center gap-1.5">
                              <span className="font-medium">Conditions:</span>
                              <div className="flex flex-wrap gap-1">
                                {trial.conditions.slice(0, 2).map((condition, idx) => (
                                  <Badge key={idx} variant="outline" className="text-xs">
                                    {condition}
                                  </Badge>
                                ))}
                                {trial.conditions.length > 2 && (
                                  <Badge variant="outline" className="text-xs">
                                    +{trial.conditions.length - 2}
                                  </Badge>
                                )}
                              </div>
                            </div>
                          )}

                          {trial.enrollment && (
                            <span>
                              <span className="font-medium">Enrollment:</span> {trial.enrollment.toLocaleString()} participants
                            </span>
                          )}

                          {trial.startDate && (
                            <span>
                              <span className="font-medium">Start:</span> {trial.startDate}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Right: Actions */}
                      <div className="flex shrink-0 items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewDetails(trial.nctId)}
                        >
                          View Details
                        </Button>
                        <Button asChild size="sm">
                          <Link
                            href={`/ct-search?createFromNCT=${trial.nctId}`}
                            replace
                            scroll={false}
                          >
                            Create Study
                          </Link>
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}
      </section>

      {/* Detail Sheet */}
      <Sheet open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
          {detailLoading ? (
            <>
              <SheetTitle>Loading Trial Details</SheetTitle>
              <SheetDescription>Please wait while we fetch trial information...</SheetDescription>
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            </>
          ) : trial ? (
            <>
              <SheetHeader>
                <SheetTitle className="text-lg leading-tight">{trial.briefTitle}</SheetTitle>
                {trial.officialTitle && trial.officialTitle !== trial.briefTitle && (
                  <SheetDescription className="text-sm">{trial.officialTitle}</SheetDescription>
                )}
              </SheetHeader>
              <div className="space-y-6 pb-6 pt-4">
                <div className="flex items-center gap-3">
                  <a
                    href={`https://clinicaltrials.gov/study/${trial.nctId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-base font-bold text-primary hover:underline"
                  >
                    {trial.nctId}
                    <ExternalLink className="h-4 w-4" />
                  </a>
                  <Badge variant={getPhaseColor(trial.phase)}>{formatPhase(trial.phase)}</Badge>
                  <Badge variant={getStatusColor(trial.overallStatus)}>
                    {formatTrialStatus(trial.overallStatus)}
                  </Badge>
                </div>

              {trial.summary && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold">Summary</h3>
                  <p className="text-sm text-muted-foreground">{trial.summary}</p>
                </div>
              )}

              <Separator />

              <div className="space-y-4">
                <h3 className="text-sm font-semibold">Study Information</h3>
                <div className="grid gap-3 text-sm">
                  <div>
                    <span className="font-medium">Lead Sponsor:</span>{' '}
                    <span className="text-muted-foreground">{trial.sponsor.lead}</span>
                  </div>
                  {trial.sponsor.collaborators && trial.sponsor.collaborators.length > 0 && (
                    <div>
                      <span className="font-medium">Collaborators:</span>{' '}
                      <span className="text-muted-foreground">
                        {trial.sponsor.collaborators.join(', ')}
                      </span>
                    </div>
                  )}
                  {trial.studyType && (
                    <div>
                      <span className="font-medium">Study Type:</span>{' '}
                      <span className="text-muted-foreground">{trial.studyType}</span>
                    </div>
                  )}
                  {trial.enrollment && (
                    <div>
                      <span className="font-medium">Enrollment:</span>{' '}
                      <span className="text-muted-foreground">
                        {trial.enrollment.toLocaleString()} participants
                      </span>
                    </div>
                  )}
                  {trial.startDate && (
                    <div>
                      <span className="font-medium">Start Date:</span>{' '}
                      <span className="text-muted-foreground">{trial.startDate}</span>
                    </div>
                  )}
                  {trial.completionDate && (
                    <div>
                      <span className="font-medium">Completion Date:</span>{' '}
                      <span className="text-muted-foreground">{trial.completionDate}</span>
                    </div>
                  )}
                </div>
              </div>

              {trial.conditions && trial.conditions.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold">Conditions</h3>
                    <div className="flex flex-wrap gap-2">
                      {trial.conditions.map((condition, idx) => (
                        <Badge key={idx} variant="outline">
                          {condition}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {trial.eligibilityCriteria && (
                <>
                  <Separator />
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold">Eligibility Criteria</h3>
                    <div className="grid gap-2 text-sm">
                      {trial.sex && (
                        <div>
                          <span className="font-medium">Sex:</span>{' '}
                          <span className="text-muted-foreground">{trial.sex}</span>
                        </div>
                      )}
                      {trial.minimumAge && (
                        <div>
                          <span className="font-medium">Minimum Age:</span>{' '}
                          <span className="text-muted-foreground">{trial.minimumAge}</span>
                        </div>
                      )}
                      {trial.maximumAge && (
                        <div>
                          <span className="font-medium">Maximum Age:</span>{' '}
                          <span className="text-muted-foreground">{trial.maximumAge}</span>
                        </div>
                      )}
                    </div>
                    <div className="rounded-md bg-muted p-3">
                      <pre className="whitespace-pre-wrap text-xs text-muted-foreground">
                        {trial.eligibilityCriteria}
                      </pre>
                    </div>
                  </div>
                </>
              )}

              {trial.interventions && trial.interventions.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold">Interventions</h3>
                    <div className="space-y-3">
                      {trial.interventions.map((intervention, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex items-start gap-2">
                            <Badge variant="secondary" className="mt-0.5 text-xs">
                              {intervention.type}
                            </Badge>
                            <div className="flex-1 space-y-1">
                              <p className="text-sm font-medium">{intervention.name}</p>
                              {intervention.description && (
                                <p className="text-xs text-muted-foreground">
                                  {intervention.description}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {trial.arms && trial.arms.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold">Study Arms</h3>
                    <div className="space-y-3">
                      {trial.arms.map((arm, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex items-start gap-2">
                            <Badge variant="outline" className="mt-0.5 text-xs">
                              {arm.type}
                            </Badge>
                            <div className="flex-1 space-y-1">
                              <p className="text-sm font-medium">{arm.label}</p>
                              {arm.description && (
                                <p className="text-xs text-muted-foreground">{arm.description}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {((trial.primaryOutcomes && trial.primaryOutcomes.length > 0) ||
                (trial.secondaryOutcomes && trial.secondaryOutcomes.length > 0)) && (
                <>
                  <Separator />
                  <div className="space-y-4">
                    <h3 className="text-sm font-semibold">Outcome Measures</h3>
                    {trial.primaryOutcomes && trial.primaryOutcomes.length > 0 && (
                      <div className="space-y-3">
                        <h4 className="text-sm font-medium">Primary Outcomes</h4>
                        {trial.primaryOutcomes.map((outcome, idx) => (
                          <div key={idx} className="space-y-1 pl-3">
                            <p className="text-sm font-medium">{outcome.measure}</p>
                            {outcome.description && (
                              <p className="text-xs text-muted-foreground">{outcome.description}</p>
                            )}
                            {outcome.timeFrame && (
                              <p className="text-xs text-muted-foreground">
                                <span className="font-semibold">Time Frame:</span> {outcome.timeFrame}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {trial.secondaryOutcomes && trial.secondaryOutcomes.length > 0 && (
                      <div className="space-y-3">
                        <h4 className="text-sm font-medium">Secondary Outcomes</h4>
                        {trial.secondaryOutcomes.map((outcome, idx) => (
                          <div key={idx} className="space-y-1 pl-3">
                            <p className="text-sm font-medium">{outcome.measure}</p>
                            {outcome.description && (
                              <p className="text-xs text-muted-foreground">{outcome.description}</p>
                            )}
                            {outcome.timeFrame && (
                              <p className="text-xs text-muted-foreground">
                                <span className="font-semibold">Time Frame:</span> {outcome.timeFrame}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}

              {trial.locations && trial.locations.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold">
                      Study Locations ({trial.locations.length})
                    </h3>
                    <div className="grid gap-2">
                      {trial.locations.slice(0, 5).map((location, idx) => (
                        <div key={idx} className="rounded-md border p-2">
                          <p className="text-sm font-medium">{location.facility}</p>
                          <p className="text-xs text-muted-foreground">
                            {location.city}, {location.state && `${location.state}, `}
                            {location.country}
                          </p>
                        </div>
                      ))}
                      {trial.locations.length > 5 && (
                        <p className="text-xs text-muted-foreground text-center">
                          +{trial.locations.length - 5} more locations
                        </p>
                      )}
                    </div>
                  </div>
                </>
              )}
              </div>
            </>
          ) : (
            <>
              <SheetTitle>Trial Details</SheetTitle>
              <SheetDescription>Unable to load trial information</SheetDescription>
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-muted-foreground">No trial data available</p>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}

export default function CTSearchPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    }>
      <CTSearchPageContent />
    </Suspense>
  );
}
