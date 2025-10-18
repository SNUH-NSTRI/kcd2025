'use client';

import { useCallback } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { DEFAULT_SEARCH_PLACEHOLDER } from '../constants';

interface SearchBarProps {
  query: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function SearchBar({ query, onChange, onSubmit }: SearchBarProps) {
  const handleSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      onSubmit();
    },
    [onSubmit],
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3 rounded-lg border border-border bg-card/30 p-4 shadow-sm sm:flex-row"
      role="search"
      aria-label="Literature search"
    >
      <div className="flex-1">
        <label htmlFor="literature-search" className="sr-only">
          Search articles
        </label>
        <Input
          id="literature-search"
          value={query}
          onChange={(event) => onChange(event.target.value)}
          placeholder={DEFAULT_SEARCH_PLACEHOLDER}
          className="w-full"
          aria-describedby="literature-search-help"
        />
        <p id="literature-search-help" className="mt-1 text-xs text-muted-foreground">
          Search within titles and abstracts across PubMed and ClinicalTrials.gov.
        </p>
      </div>
      <Button type="submit" className="gap-2 self-start sm:self-auto">
        <Search className="h-4 w-4" aria-hidden="true" />
        Search
      </Button>
    </form>
  );
}
