'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Search } from 'lucide-react';

export function TrialSelectorForm() {
  const [nctId, setNctId] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = nctId.trim().toUpperCase();

    if (!trimmed) return;

    // Validate NCT ID format
    if (!/^NCT\d{8}$/.test(trimmed)) {
      alert('Please enter a valid NCT ID (e.g., NCT03389555)');
      return;
    }

    setIsValidating(true);
    router.push(`/enrichment/${trimmed}`);
  };

  return (
    <Card className="w-full max-w-md shadow-lg">
      <form onSubmit={handleSubmit}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            View Enrichment Report
          </CardTitle>
          <CardDescription>
            Enter a ClinicalTrials.gov Identifier (NCT ID) to view its Stage 4 enrichment results
            with ICD codes and MIMIC-IV mappings.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="nctId">NCT ID</Label>
              <Input
                id="nctId"
                placeholder="e.g., NCT03389555"
                value={nctId}
                onChange={(e) => setNctId(e.target.value.toUpperCase())}
                pattern="^NCT\d{8}$"
                title="Please enter a valid NCT ID (e.g., NCT03389555)"
                className="font-mono"
                required
              />
            </div>
            <div className="text-xs text-muted-foreground">
              <p className="font-semibold mb-1">Example trials:</p>
              <ul className="list-disc list-inside space-y-0.5">
                <li>
                  <button
                    type="button"
                    className="text-blue-600 hover:underline"
                    onClick={() => setNctId('NCT03389555')}
                  >
                    NCT03389555
                  </button>{' '}
                  - Septic Shock Trial
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button type="submit" className="w-full" disabled={!nctId.trim() || isValidating}>
            {isValidating ? 'Loading...' : 'View Report'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
