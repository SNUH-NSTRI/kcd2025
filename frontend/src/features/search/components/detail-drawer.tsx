'use client';

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import type { Article } from '../types';
import { SOURCE_LABELS } from '../constants';

interface DetailDrawerProps {
  article: Article | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DetailDrawer({ article, open, onOpenChange }: DetailDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-xl space-y-4 overflow-y-auto">
        {article ? (
          <div className="space-y-5">
            <SheetHeader className="items-start text-left">
              <SheetTitle className="text-2xl font-heading font-semibold">
                {article.title}
              </SheetTitle>
              <SheetDescription className="text-sm text-muted-foreground">
                {SOURCE_LABELS[article.source]} • {article.journal} • {article.year}
              </SheetDescription>
            </SheetHeader>

            <section className="space-y-2">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Authors
              </h3>
              <p className="text-base text-foreground">{article.authors.join(', ')}</p>
            </section>

            <section className="space-y-2">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Abstract
              </h3>
              <p className="text-base leading-relaxed text-foreground">
                {article.abstract}
              </p>
            </section>

            <section className="space-y-2">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Keywords
              </h3>
              <div className="flex flex-wrap gap-2">
                {article.keywords.map((keyword) => (
                  <Badge key={keyword} variant="secondary">
                    {keyword}
                  </Badge>
                ))}
              </div>
            </section>

            <section className="space-y-2">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                MeSH Terms
              </h3>
              <ul className="list-inside list-disc space-y-1 text-base text-foreground">
                {article.meshTerms.map((term) => (
                  <li key={term}>{term}</li>
                ))}
              </ul>
            </section>

            <section className="space-y-1 text-sm text-muted-foreground">
              <p>
                Identifier: <span className="font-medium text-foreground">{article.id}</span>
              </p>
              <p>Source registry: {SOURCE_LABELS[article.source]}</p>
            </section>
          </div>
        ) : (
          <div className="space-y-2">
            <SheetHeader>
              <SheetTitle className="text-xl font-semibold">
                No article selected
              </SheetTitle>
              <SheetDescription>
                Choose a study from the results list to review abstract details.
              </SheetDescription>
            </SheetHeader>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
