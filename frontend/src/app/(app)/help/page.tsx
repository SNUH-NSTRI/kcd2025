import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const SUPPORT_ARTICLES = [
  {
    id: 'getting-started',
    title: 'Trial emulation primer',
    description: 'Understand the overall workflow from literature ingestion to RWE report delivery.',
  },
  {
    id: 'schema-editor',
    title: 'Schema editor basics',
    description: 'Learn how to review AI-extracted criteria and make manual adjustments safely.',
  },
  {
    id: 'analysis-templates',
    title: 'Analysis templates overview',
    description: 'Compare available statistical templates and how to interpret their outputs.',
  },
];

export default function HelpPage() {
  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-heading font-semibold text-foreground">Help center</h1>
        <p className="max-w-2xl text-base text-muted-foreground">
          Explore documentation and guidance to move studies forward confidently. Contact support for critical blockers.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {SUPPORT_ARTICLES.map((article) => (
          <Card key={article.id} className="border border-border/70 bg-card/50">
            <CardHeader>
              <CardTitle className="text-xl">{article.title}</CardTitle>
              <CardDescription>{article.description}</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Detailed knowledge base content will populate this section in a later milestone.
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
