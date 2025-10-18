'use client';

import { Calendar, Filter } from 'lucide-react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import type { SearchFilters } from '@/features/flow/types';
import { ARTICLE_YEARS, SOURCE_OPTIONS } from '../lib/articles';

interface FilterPanelProps {
  filters: SearchFilters;
  onChange: (filters: Partial<SearchFilters>) => void;
}

export function FilterPanel({ filters, onChange }: FilterPanelProps) {
  return (
    <Card className="sticky top-[88px] h-fit border-border/80 bg-card/70 shadow-sm">
      <CardHeader className="space-y-1">
        <CardTitle className="flex items-center gap-2 text-base">
          <Filter className="h-4 w-4 text-primary" aria-hidden="true" />
          Filters
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Refine literature matches by publication year and source registry.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="year-filter" className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Publication year
          </Label>
          <Select
            value={filters.year === 'all' ? 'all' : String(filters.year)}
            onValueChange={(value) =>
              onChange({ year: value === 'all' ? 'all' : Number(value) })
            }
          >
            <SelectTrigger id="year-filter" aria-label="Filter by publication year">
              <SelectValue placeholder="All years" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All years</SelectItem>
              {ARTICLE_YEARS.map((option) => (
                <SelectItem key={option.value} value={String(option.value)}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="source-filter">Source</Label>
          <Select
            value={filters.source}
            onValueChange={(value) =>
              onChange({ source: value as SearchFilters['source'] })
            }
          >
            <SelectTrigger id="source-filter" aria-label="Filter by source registry">
              <SelectValue placeholder="All sources" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All sources</SelectItem>
              {SOURCE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
