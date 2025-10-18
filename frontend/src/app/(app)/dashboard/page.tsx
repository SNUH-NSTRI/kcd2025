'use client';

import type { ReactNode } from 'react';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  BadgeCheck,
  CheckCircle2,
  Clock3,
  LineChart,
  Loader2,
  PlusCircle,
  Zap,
} from 'lucide-react';
import { useFlow } from '@/features/flow/context';
import { CreateStudyDialog } from '@/features/flow/components/create-study-dialog';

const RECENT_STUDIES = [
  {
    id: 'cardio-outcomes',
    title: 'Study on Cardiovascular Outcomes',
    updatedAt: 'Last modified: 2 days ago',
    summary: 'Cohort: 1,234 patients. Analysis: Propensity Score.',
  },
  {
    id: 'oncology-insights',
    title: 'Oncology Real-World Evidence Pilot',
    updatedAt: 'Last modified: 5 days ago',
    summary: 'Cohort: 842 patients. Analysis: Survival Curve.',
  },
  {
    id: 'respiratory-trial',
    title: 'Respiratory Trial Emulation (MIMIC-IV)',
    updatedAt: 'Last modified: 1 week ago',
    summary: 'Cohort: 2,104 patients. Analysis: Hazard Ratio.',
  },
  {
    id: 'metabolic-study',
    title: 'Metabolic Disorder Progression Study',
    updatedAt: 'Last modified: 2 weeks ago',
    summary: 'Cohort: 968 patients. Analysis: Logistic Regression.',
  },
];

const STATUS_ITEMS = [
  {
    id: 'mimic-iv',
    label: 'MIMIC-IV Dataset',
    detail: 'Connected',
  },
  {
    id: 'pubmed-api',
    label: 'PubMed API',
    detail: 'Operational',
  },
  {
    id: 'queue',
    label: 'Analysis Queue',
    detail: 'Idle',
  },
  {
    id: 'compliance',
    label: 'Compliance Monitoring',
    detail: 'All checks passed',
  },
];

export default function DashboardPage() {
  const router = useRouter();
  const { setMode, setDemoConfig, runDemoPipeline } = useFlow();
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);

  const handleStartDemo = async () => {
    setIsDemoLoading(true);
    setDemoError(null); // Reset error on new attempt
    try {
      setMode('demo');
      setDemoConfig({
        nctId: 'NCT03389555',
        projectId: 'demo_project_001',
        sampleSize: 100,
        study: {
          id: 'NCT03389555',
          name: 'Adjunctive Glucocorticoid Therapy in Patients with Septic Shock',
          purpose: 'Evaluate efficacy of hydrocortisone in septic shock',
          nctId: 'NCT03389555',
          medicine: 'hydrocortisonenasucc',
          createdAt: new Date(),
        },
      });
      await runDemoPipeline();
      // On success, navigate. The dialog will close automatically.
      router.push('/search');
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'An unexpected error occurred.';
      console.error('Failed to start demo pipeline:', error);
      setDemoError(errorMessage);
      // TODO: Show toast notification for better UX, e.g., using a library like sonner
      // toast.error('Failed to start demo', { description: errorMessage });
    } finally {
      setIsDemoLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-muted-foreground">
          Overview
        </p>
        <h1 className="text-3xl font-heading font-semibold text-foreground">
          Dashboard
        </h1>
        <p className="max-w-2xl text-base text-muted-foreground">
          Launch new trial emulations, review ongoing work, and monitor system readiness — all in one place.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px] xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="space-y-8">
          <Card className="border-dashed bg-card/60">
            <CardHeader className="space-y-4">
              <div className="flex flex-col gap-1">
                <CardTitle className="text-xl">Quick actions</CardTitle>
                <CardDescription>
                  Start a new emulation or pick up where you left off.
                </CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <CreateStudyDialog />
                <Button variant="outline" size="lg" className="gap-2">
                  <Clock3 className="h-5 w-5" />
                  Resume Last Session
                </Button>
                <Dialog
                  open={isDialogOpen}
                  onOpenChange={(open) => {
                    setIsDialogOpen(open);
                    if (!open) {
                      setDemoError(null); // Reset error when dialog is closed
                    }
                  }}
                >
                  <DialogTrigger asChild>
                    <Button variant="secondary" size="lg" className="gap-2">
                      <Zap className="h-5 w-5" />
                      Start Demo
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Start Demo Mode?</DialogTitle>
                      <DialogDescription>
                        This will launch a pre-configured trial emulation using the MIMIC-IV dataset for NCT03389555. You will be redirected to the study setup page to review the configuration.
                      </DialogDescription>
                    </DialogHeader>
                    {demoError && (
                      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                        <p className="font-semibold">Could not start demo</p>
                        <p className="text-destructive/90">{demoError}</p>
                      </div>
                    )}
                    <DialogFooter>
                      <Button
                        variant="ghost"
                        onClick={() => setIsDialogOpen(false)}
                        disabled={isDemoLoading}
                      >
                        Cancel
                      </Button>
                      <Button
                        onClick={handleStartDemo}
                        disabled={isDemoLoading}
                        className="gap-2"
                      >
                        {isDemoLoading ? (
                          <Loader2 className="h-5 w-5 animate-spin" />
                        ) : (
                          <Zap className="h-5 w-5" />
                        )}
                        {demoError ? 'Retry Demo' : 'Confirm & Run Demo'}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <QuickStat
                icon={<LineChart className="h-5 w-5" />}
                label="Active analyses"
                value="3 workflows"
              />
              <QuickStat
                icon={<BadgeCheck className="h-5 w-5" />}
                label="Reports delivered"
                value="12 this month"
              />
            </CardContent>
          </Card>

          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-heading font-semibold text-foreground">
                Recent Studies
              </h2>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/report">View archive</Link>
              </Button>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {RECENT_STUDIES.map((study) => (
                <Card key={study.id} className="flex h-full flex-col">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold">
                      {study.title}
                    </CardTitle>
                    <CardDescription>{study.updatedAt}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{study.summary}</p>
                  </CardContent>
                  <CardFooter className="mt-auto flex items-center justify-between gap-3">
                    <Button size="sm" className="gap-2">
                      <CheckCircle2 className="h-4 w-4" />
                      View Report
                    </Button>
                    <Button variant="link" size="sm" className="px-0">
                      Edit Schema
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          </section>
        </section>

        <aside className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">System Status</CardTitle>
              <CardDescription>Operational status across core services.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {STATUS_ITEMS.map((status) => (
                <div
                  key={status.id}
                  className="flex items-start justify-between gap-4 rounded-md border border-border/60 bg-muted/10 p-3"
                >
                  <div>
                    <p className="text-sm font-medium text-foreground">{status.label}</p>
                    <p className="text-xs text-muted-foreground">{status.detail}</p>
                  </div>
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600">
                    <CheckCircle2 className="h-4 w-4" />
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}

interface QuickStatProps {
  icon: ReactNode;
  label: string;
  value: string;
}

function QuickStat({ icon, label, value }: QuickStatProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-muted/20 p-4">
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
        {icon}
      </span>
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className="text-sm font-semibold text-foreground">{value}</p>
      </div>
    </div>
  );
}
