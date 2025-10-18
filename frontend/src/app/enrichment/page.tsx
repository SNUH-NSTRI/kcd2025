import { TrialSelectorForm } from '@/features/enrichment/components/TrialSelectorForm';
import { Sparkles } from 'lucide-react';

export default function EnrichmentLandingPage() {
  return (
    <main className="container mx-auto px-4 py-12">
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-16rem)] space-y-8">
        {/* Hero Section */}
        <div className="text-center space-y-4 max-w-2xl">
          <div className="flex items-center justify-center gap-3">
            <Sparkles className="w-12 h-12 text-blue-600" />
            <h1 className="text-4xl font-bold tracking-tight">Trial Enrichment</h1>
          </div>
          <p className="text-lg text-muted-foreground">
            View Stage 4 enrichment results with ICD-9/10 medical codes and MIMIC-IV database
            mappings for clinical trial criteria.
          </p>
        </div>

        {/* Selector Form */}
        <TrialSelectorForm />

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl w-full pt-8">
          <div className="bg-muted p-4 rounded-lg">
            <h3 className="font-semibold mb-2">🩺 ICD Code Mapping</h3>
            <p className="text-sm text-muted-foreground">
              Condition entities automatically mapped to ICD-9 and ICD-10 codes via LLM for
              standardized medical coding.
            </p>
          </div>
          <div className="bg-muted p-4 rounded-lg">
            <h3 className="font-semibold mb-2">🗄️ MIMIC-IV Mapping</h3>
            <p className="text-sm text-muted-foreground">
              Trial criteria operationalized into MIMIC-IV database queries with table/column
              mappings and filtering logic.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
