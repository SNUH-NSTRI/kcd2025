'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, Sparkles, Database, AlertCircle, CheckCircle2, Info, Copy, Check } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

// Types
interface MimicMapping {
  table: string;
  columns: string[];
  filter_logic: string;
}

interface AlternativeMapping {
  table: string;
  columns: string[];
  filter_logic: string;
  reasoning: string;
}

interface MappingResult {
  mapping: MimicMapping;
  confidence: number;
  reasoning: string;
  alternatives: AlternativeMapping[];
  source: 'cache' | 'llm' | 'fallback' | 'manual';
  timestamp: string;
}

// Sample criteria for quick testing
const SAMPLE_CRITERIA = [
  { domain: 'Condition', text: 'Patients with sepsis' },
  { domain: 'Drug', text: 'Administration of hydrocortisone' },
  { domain: 'Measurement', text: 'Lactate level greater than 2.0 mmol/L' },
  { domain: 'Procedure', text: 'Mechanical ventilation for at least 24 hours' },
  { domain: 'Observation', text: 'Temperature greater than 38.3°C' },
];

export default function TrialistMapperPage() {
  const [criterionText, setCriterionText] = useState('');
  const [selectedDomain, setSelectedDomain] = useState<string>('Condition');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<MappingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!criterionText.trim()) {
      setError('Please enter a criterion text');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      // Call backend API (you'll need to implement this endpoint)
      const response = await fetch('http://localhost:8000/api/trialist/map-concept', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          concept: criterionText,
          domain: selectedDomain,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to map concept');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSampleClick = (sample: typeof SAMPLE_CRITERIA[0]) => {
    setCriterionText(sample.text);
    setSelectedDomain(sample.domain);
    setResult(null);
    setError(null);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'cache': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'llm': return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'fallback': return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'manual': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <header className="space-y-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-8 w-8 text-primary" />
          <h1 className="text-3xl font-heading font-bold text-foreground">Trialist Mapper Playground</h1>
        </div>
        <p className="text-base text-muted-foreground">
          Test the IntelligentMimicMapper system. Enter a clinical trial criterion and see how it maps to MIMIC-IV database tables.
        </p>
      </header>

      {/* Input Form */}
      <div className="rounded-lg border border-border bg-card p-6 space-y-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Domain Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              Clinical Domain
            </label>
            <div className="flex flex-wrap gap-2">
              {['Condition', 'Drug', 'Measurement', 'Procedure', 'Observation'].map((domain) => (
                <Button
                  key={domain}
                  type="button"
                  variant={selectedDomain === domain ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedDomain(domain)}
                >
                  {domain}
                </Button>
              ))}
            </div>
          </div>

          {/* Criterion Input */}
          <div className="space-y-2">
            <label htmlFor="criterion" className="text-sm font-medium text-foreground">
              Criterion Text
            </label>
            <textarea
              id="criterion"
              value={criterionText}
              onChange={(e) => setCriterionText(e.target.value)}
              placeholder="e.g., Patients with sepsis diagnosed within 24 hours"
              className="w-full min-h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>

          {/* Sample Criteria */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              Quick Samples
            </label>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_CRITERIA.map((sample, idx) => (
                <Button
                  key={idx}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleSampleClick(sample)}
                  className="text-xs"
                >
                  <span className="font-semibold mr-1">{sample.domain}:</span>
                  {sample.text.substring(0, 30)}...
                </Button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Mapping...
              </>
            ) : (
              <>
                <Database className="mr-2 h-4 w-4" />
                Map to MIMIC-IV
              </>
            )}
          </Button>
        </form>
      </div>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Result Display */}
      {result && (
        <div className="space-y-4">
          {/* Main Mapping Result */}
          <div className="rounded-lg border border-border bg-card p-6 space-y-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  Mapping Result
                </h3>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getSourceBadgeColor(result.source)}`}>
                    Source: {result.source.toUpperCase()}
                  </span>
                  <span className={`text-sm font-medium ${getConfidenceColor(result.confidence)}`}>
                    Confidence: {(result.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(result.mapping.filter_logic)}
              >
                {copied ? (
                  <>
                    <Check className="h-4 w-4 mr-1" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-1" />
                    Copy SQL
                  </>
                )}
              </Button>
            </div>

            {/* Table & Columns */}
            <div className="space-y-3">
              <div>
                <span className="text-sm font-medium text-muted-foreground">Table:</span>
                <p className="text-base font-mono font-semibold text-foreground mt-1">
                  {result.mapping.table}
                </p>
              </div>

              <div>
                <span className="text-sm font-medium text-muted-foreground">Columns:</span>
                <div className="flex flex-wrap gap-2 mt-1">
                  {result.mapping.columns.map((col, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center rounded-md bg-primary/10 px-2 py-1 text-xs font-mono text-primary"
                    >
                      {col}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-sm font-medium text-muted-foreground">Filter Logic:</span>
                <pre className="mt-1 rounded-md bg-muted p-3 text-xs font-mono overflow-x-auto">
                  {result.mapping.filter_logic}
                </pre>
              </div>

              {/* Reasoning */}
              <div>
                <span className="text-sm font-medium text-muted-foreground">Reasoning:</span>
                <p className="text-sm text-foreground mt-1 leading-relaxed">
                  {result.reasoning}
                </p>
              </div>

              {/* Timestamp */}
              <div className="text-xs text-muted-foreground">
                Mapped at: {new Date(result.timestamp).toLocaleString()}
              </div>
            </div>
          </div>

          {/* Alternative Mappings */}
          {result.alternatives && result.alternatives.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-6 space-y-4">
              <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <Info className="h-5 w-5 text-blue-600" />
                Alternative Mappings ({result.alternatives.length})
              </h3>

              <div className="space-y-3">
                {result.alternatives.map((alt, idx) => (
                  <div key={idx} className="rounded-md border border-border/50 bg-muted/30 p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-foreground">
                        Option {idx + 1}: {alt.table}
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {alt.columns.map((col, colIdx) => (
                          <span
                            key={colIdx}
                            className="inline-flex items-center rounded-md bg-background px-2 py-0.5 text-xs font-mono text-muted-foreground"
                          >
                            {col}
                          </span>
                        ))}
                      </div>
                    </div>
                    <pre className="rounded-md bg-background p-2 text-xs font-mono overflow-x-auto">
                      {alt.filter_logic}
                    </pre>
                    <p className="text-xs text-muted-foreground italic">
                      {alt.reasoning}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Info Box */}
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>About This Mapping</AlertTitle>
            <AlertDescription className="space-y-2">
              <p>
                This mapping was generated using the IntelligentMimicMapper system with OpenRouter LLM (gpt-4o-mini).
                The system uses a cascading lookup pattern: existing cache → LLM reasoning → fallback strategy.
              </p>
              {result.source === 'llm' && (
                <p className="text-sm font-medium text-purple-700">
                  ✨ This is a new mapping generated by AI and has been automatically cached for future use.
                </p>
              )}
              {result.source === 'cache' && (
                <p className="text-sm font-medium text-blue-700">
                  ⚡ This mapping was retrieved from cache for instant results.
                </p>
              )}
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* System Info */}
      <div className="rounded-lg border border-dashed border-border/70 bg-card/40 p-4 text-sm text-muted-foreground">
        <h4 className="font-semibold text-foreground mb-2">System Information</h4>
        <ul className="space-y-1 list-disc list-inside">
          <li>Backend API: <code className="text-xs font-mono bg-muted px-1 py-0.5 rounded">POST /api/trialist/map-concept</code></li>
          <li>LLM Model: <code className="text-xs font-mono bg-muted px-1 py-0.5 rounded">gpt-4o-mini</code> via OpenRouter</li>
          <li>MIMIC-IV Tables: diagnoses_icd, labevents, chartevents, prescriptions, procedures_icd, inputevents, outputevents</li>
          <li>Supported Domains: Condition, Drug, Measurement, Procedure, Observation</li>
        </ul>
      </div>
    </section>
  );
}
