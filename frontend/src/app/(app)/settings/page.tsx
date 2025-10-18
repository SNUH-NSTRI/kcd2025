import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const PREFERENCE_ITEMS = [
  {
    id: 'notifications',
    title: 'Notifications',
    description: 'Control alerts for pipeline runs, schema approvals, and report delivery.',
  },
  {
    id: 'workspace',
    title: 'Workspace defaults',
    description: 'Set default datasets, time horizons, and analysis templates for new studies.',
  },
];

export default function SettingsPage() {
  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-heading font-semibold text-foreground">Settings</h1>
        <p className="max-w-2xl text-base text-muted-foreground">
          Configure workspace defaults and tailor your notification preferences for trial emulation workflows.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {PREFERENCE_ITEMS.map((item) => (
          <Card key={item.id} className="border-dashed bg-card/50">
            <CardHeader>
              <CardTitle className="text-xl">{item.title}</CardTitle>
              <CardDescription>{item.description}</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Placeholder controls will live here once configuration endpoints are available.
            </CardContent>
          </Card>
        ))}
        <Card className="flex flex-col justify-between border border-primary/40 bg-card/60">
          <CardHeader>
            <CardTitle className="text-xl text-foreground">Audit log & version history</CardTitle>
            <CardDescription>
              Review immutable timelines for schema edits, cohort generations, analysis runs, and report exports.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <Button asChild variant="outline" className="mt-2">
              <Link href="/settings/audit">Open audit console</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
