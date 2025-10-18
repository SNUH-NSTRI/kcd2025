'use client';

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useToast } from '@/hooks/use-toast';
import { useFlow, useSearchState } from '@/features/flow/context';
import type { SearchFilters } from '@/features/flow/types';
import { SearchBar } from '@/features/search/components/search-bar';
import { FilterPanel } from '@/features/search/components/filter-panel';
import { SelectionBadge } from '@/features/search/components/selection-badge';
import { ResultList } from '@/features/search/components/result-list';
import { DetailDrawer } from '@/features/search/components/detail-drawer';
import { ARTICLES } from '@/features/search/lib/articles';
import type { Article } from '@/features/search/types';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

function SearchPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const {
    state,
    setSearchQuery,
    setSearchFilters,
    toggleArticleSelection,
    toggleArticleExclusion,
    clearSearchSelections,
    setSearchPage,
    setSearchPageSize,
    markDone,
  } = useFlow();
  const searchState = useSearchState();

  const [draftQuery, setDraftQuery] = useState(searchState.query);
  const [drawerArticle, setDrawerArticle] = useState<Article | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [isDemoSimulating, setIsDemoSimulating] = useState(false);

  useEffect(() => {
    setDraftQuery(searchState.query);
  }, [searchState.query]);

  // Demo Mode: Auto-progress simulation
  useEffect(() => {
    const mode = searchParams.get('mode');
    if (mode === 'demo' && state.mode === 'demo' && !isDemoSimulating) {
      simulateDemoSearch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, state.mode]);

  const simulateDemoSearch = async () => {
    setIsDemoSimulating(true);

    // Simulate 0.5 second loading for literature search
    await new Promise(resolve => setTimeout(resolve, 500));

    // Mark search step as complete
    markDone('search');

    // Navigate to schema page with demo mode
    router.push('/schema?mode=demo');
  };

  const applyFilters = useCallback(
    (filters: Partial<SearchFilters>) => {
      setSearchFilters(filters);
    },
    [setSearchFilters],
  );

  const normalizedQuery = useMemo(() => searchState.query.trim().toLowerCase(), [searchState.query]);

  const filteredArticles = useMemo(() => {
    return ARTICLES.filter((article) => {
      const matchesQuery =
        normalizedQuery.length === 0 ||
        [
          article.title,
          article.abstract,
          article.authors.join(' '),
          article.keywords.join(' '),
        ]
          .join(' ')
          .toLowerCase()
          .includes(normalizedQuery);

      const matchesSource =
        searchState.filters.source === 'all' ||
        article.source === searchState.filters.source;

      const matchesYear =
        searchState.filters.year === 'all' || article.year === searchState.filters.year;

      return matchesQuery && matchesSource && matchesYear;
    });
  }, [normalizedQuery, searchState.filters]);

  useEffect(() => {
    const maxPage = Math.max(1, Math.ceil(filteredArticles.length / searchState.pageSize) || 1);
    if (searchState.currentPage > maxPage) {
      setSearchPage(maxPage);
    }
  }, [filteredArticles.length, searchState.currentPage, searchState.pageSize, setSearchPage]);

  const pagedArticles = useMemo(() => {
    const startIndex = (searchState.currentPage - 1) * searchState.pageSize;
    return filteredArticles.slice(startIndex, startIndex + searchState.pageSize);
  }, [filteredArticles, searchState.currentPage, searchState.pageSize]);

  const handleQuerySubmit = useCallback(() => {
    setSearchQuery(draftQuery);
  }, [draftQuery, setSearchQuery]);

  const handleOpenDetails = useCallback((article: Article) => {
    setDrawerArticle(article);
    setDrawerOpen(true);
  }, []);

  const handleDrawerOpenChange = useCallback((open: boolean) => {
    setDrawerOpen(open);
    if (!open) {
      setDrawerArticle(null);
    }
  }, []);

  const proceedDisabled = searchState.selectedArticleIds.length === 0;

  const handleProceed = useCallback(() => {
    if (proceedDisabled) {
      toast({
        title: 'Select at least one study',
        description: 'Choose relevant literature before advancing to schema extraction.',
        variant: 'destructive',
      });
      return;
    }

    markDone('search');
    router.push('/schema');
  }, [markDone, proceedDisabled, router, toast]);

  // Demo Mode loading UI
  if (isDemoSimulating) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <div className="text-center">
          <p className="text-lg font-medium text-foreground">Searching literature...</p>
          <p className="text-sm text-muted-foreground">Loading pre-fetched trial data from NCT03389555</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-muted-foreground">Step 1</p>
        <h2 className="text-3xl font-heading font-bold text-foreground">Literature search</h2>
        <p className="text-base text-muted-foreground">
          Curate published studies to seed the trial emulation workflow. Combine keyword search with registry filters to identify the most relevant evidence.
        </p>
      </header>

      <SearchBar
        query={draftQuery}
        onChange={setDraftQuery}
        onSubmit={handleQuerySubmit}
      />

      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <FilterPanel filters={searchState.filters} onChange={applyFilters} />
        <section className="space-y-6">
          <div className="flex flex-col gap-3 rounded-lg border border-border bg-card/60 p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
            <SelectionBadge
              selectedCount={searchState.selectedArticleIds.length}
              excludedCount={searchState.excludedArticleIds.length}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={clearSearchSelections}
                disabled={
                  searchState.selectedArticleIds.length === 0 &&
                  searchState.excludedArticleIds.length === 0
                }
              >
                Clear selections
              </Button>
              <Button onClick={handleProceed} disabled={proceedDisabled}>
                Proceed to next step
              </Button>
            </div>
          </div>

          <ResultList
            articles={pagedArticles}
            total={filteredArticles.length}
            page={searchState.currentPage}
            pageSize={searchState.pageSize}
            onPageChange={setSearchPage}
            onPageSizeChange={setSearchPageSize}
            selectedIds={searchState.selectedArticleIds}
            excludedIds={searchState.excludedArticleIds}
            onToggleSelect={toggleArticleSelection}
            onToggleExclude={toggleArticleExclusion}
            onOpenDetails={handleOpenDetails}
          />
        </section>
      </div>

      <DetailDrawer
        article={drawerArticle}
        open={drawerOpen}
        onOpenChange={handleDrawerOpenChange}
      />
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-[60vh] flex-col items-center justify-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    }>
      <SearchPageContent />
    </Suspense>
  );
}
