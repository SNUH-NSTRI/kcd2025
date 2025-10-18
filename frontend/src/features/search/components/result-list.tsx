'use client';

import { CheckCircle2, Eye, MinusCircle, PlusCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { cn } from '@/lib/utils';
import type { Article } from '../types';
import { SOURCE_LABELS } from '../constants';

interface ResultListProps {
  articles: Article[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  selectedIds: string[];
  excludedIds: string[];
  onToggleSelect: (id: string) => void;
  onToggleExclude: (id: string) => void;
  onOpenDetails: (article: Article) => void;
}

const formatAuthors = (authors: string[]) => {
  if (authors.length === 0) return 'Unknown';
  if (authors.length === 1) return authors[0];
  if (authors.length === 2) return `${authors[0]} & ${authors[1]}`;
  return `${authors[0]}, ${authors[1]} et al.`;
};

export function ResultList({
  articles,
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  selectedIds,
  excludedIds,
  onToggleSelect,
  onToggleExclude,
  onOpenDetails,
}: ResultListProps) {
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = total === 0 ? 0 : Math.min(page * pageSize, total);
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  const handlePrevious = () => {
    if (page > 1) {
      onPageChange(page - 1);
    }
  };

  const handleNext = () => {
    if (page < pageCount) {
      onPageChange(page + 1);
    }
  };

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
        <table className="min-w-full divide-y divide-border/60 text-left text-sm">
          <thead className="bg-muted/40 uppercase tracking-wide text-xs text-muted-foreground">
            <tr>
              <th scope="col" className="px-4 py-3">Title</th>
              <th scope="col" className="px-4 py-3">Authors</th>
              <th scope="col" className="px-4 py-3">Journal / Source</th>
              <th scope="col" className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {articles.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-sm text-muted-foreground">
                  No articles match the current search criteria. Adjust filters to broaden your results.
                </td>
              </tr>
            ) : (
              articles.map((article) => {
                const isSelected = selectedIds.includes(article.id);
                const isExcluded = excludedIds.includes(article.id);

                return (
                  <tr
                    key={article.id}
                    className={cn(
                      'transition-colors hover:bg-muted/30',
                      isSelected && 'bg-primary/5',
                      isExcluded && 'bg-destructive/5',
                    )}
                  >
                    <td className="max-w-[340px] px-4 py-4 align-top">
                      <div className="flex flex-col gap-2">
                        <button
                          type="button"
                          onClick={() => onOpenDetails(article)}
                          className="text-left text-base font-semibold text-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                        >
                          {article.title}
                        </button>
                        <p className="text-xs text-muted-foreground">
                          {article.abstract.slice(0, 160)}{article.abstract.length > 160 ? '…' : ''}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-4 align-top text-sm text-foreground">
                      {formatAuthors(article.authors)}
                    </td>
                    <td className="px-4 py-4 align-top text-sm text-muted-foreground">
                      <span className="block text-foreground">{article.journal}</span>
                      <span className="text-xs">{SOURCE_LABELS[article.source]} • {article.year}</span>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <div className="flex flex-col items-end gap-2">
                        <div className="flex gap-2">
                          <Button
                            variant={isSelected ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => onToggleSelect(article.id)}
                            aria-pressed={isSelected}
                          >
                            {isSelected ? (
                              <CheckCircle2 className="mr-2 h-4 w-4" aria-hidden="true" />
                            ) : (
                              <PlusCircle className="mr-2 h-4 w-4" aria-hidden="true" />
                            )}
                            {isSelected ? 'Selected' : 'Select'}
                          </Button>
                          <Button
                            variant={isExcluded ? 'destructive' : 'ghost'}
                            size="sm"
                            onClick={() => onToggleExclude(article.id)}
                            aria-pressed={isExcluded}
                          >
                            {isExcluded ? (
                              <MinusCircle className="mr-2 h-4 w-4" aria-hidden="true" />
                            ) : (
                              <XCircle className="mr-2 h-4 w-4" aria-hidden="true" />
                            )}
                            {isExcluded ? 'Excluded' : 'Exclude'}
                          </Button>
                        </div>
                        <Button
                          variant="link"
                          size="sm"
                          className="gap-1 text-primary"
                          onClick={() => onOpenDetails(article)}
                        >
                          <Eye className="h-4 w-4" aria-hidden="true" />
                          View details
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 rounded-lg border border-border bg-card/60 px-4 py-3 text-sm text-muted-foreground shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
          <p>
            Showing {start}–{end} of {total} studies
          </p>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wide">Per page</span>
            <Select
              value={String(pageSize)}
              onValueChange={(value) => onPageSizeChange(Number(value))}
            >
              <SelectTrigger className="h-8 w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[5, 10, 15].map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrevious}
            disabled={page === 1}
          >
            Previous
          </Button>
          <span className="text-xs font-medium text-foreground">
            Page {page} of {pageCount}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNext}
            disabled={page === pageCount || total === 0}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
