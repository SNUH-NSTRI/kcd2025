'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { CohortResult } from '@/features/flow/types';
import type { TrialVariable } from '@/features/schema/types';

interface DataPreviewProps {
  result: CohortResult | null;
  variables: TrialVariable[];
}

const PAGE_SIZE_OPTIONS = [10, 25, 50];

export function DataPreview({ result, variables }: DataPreviewProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE_OPTIONS[0]);

  useEffect(() => {
    setPage(1);
  }, [pageSize, result]);

  if (!result) {
    return (
      <Card className="border border-dashed border-border/70 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">Cohort preview</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Load cohort data to inspect real patient records from MIMIC-IV.
          </p>
        </CardContent>
      </Card>
    );
  }

  const totalPages = Math.max(1, Math.ceil(result.patients.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * pageSize;
  const rows = result.patients.slice(startIndex, startIndex + pageSize);

  return (
    <Card className="border border-border/70 bg-card/80">
      <CardHeader className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-base">Cohort preview</CardTitle>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Page {currentPage} of {totalPages}</span>
            <Select
              value={`${pageSize}`}
              onValueChange={(value) => setPageSize(Number(value))}
            >
              <SelectTrigger className="h-8 w-20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZE_OPTIONS.map((option) => (
                  <SelectItem key={option} value={`${option}`}>
                    {option}/page
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Button
            variant="outline"
            size="sm"
            disabled={currentPage === 1}
            onClick={() => setPage((prev) => Math.max(1, prev - 1))}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={currentPage >= totalPages}
            onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
          >
            Next
          </Button>
        </div>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border/60 text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-muted-foreground">ID</th>
              <th className="px-4 py-2 text-left font-medium text-muted-foreground">Age</th>
              <th className="px-4 py-2 text-left font-medium text-muted-foreground">Sex</th>
              {variables.map((variable) => (
                <th
                  key={variable.id}
                  className="px-4 py-2 text-left font-medium text-muted-foreground"
                >
                  {variable.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60 bg-background/80">
            {rows.map((patient) => (
              <tr key={patient.id}>
                <td className="px-4 py-2 text-muted-foreground">{patient.id}</td>
                <td className="px-4 py-2 text-muted-foreground">{patient.age}</td>
                <td className="px-4 py-2 text-muted-foreground">{patient.sex}</td>
                {variables.map((variable) => {
                  const value = patient.vars[variable.id];
                  return (
                    <td key={variable.id} className="px-4 py-2 text-muted-foreground">
                      {value === undefined ? '—' : String(value)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
