'use client';

import { Badge } from '@/components/ui/badge';

interface SelectionBadgeProps {
  selectedCount: number;
  excludedCount: number;
}

export function SelectionBadge({ selectedCount, excludedCount }: SelectionBadgeProps) {
  const hasSelection = selectedCount > 0 || excludedCount > 0;

  if (!hasSelection) {
    return (
      <p className="text-sm text-muted-foreground">
        No articles selected. Choose relevant papers to continue.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Badge variant="secondary" className="gap-1">
        Selected
        <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground">
          {selectedCount}
        </span>
      </Badge>
      <Badge variant="outline" className="gap-1">
        Excluded
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-semibold text-muted-foreground">
          {excludedCount}
        </span>
      </Badge>
    </div>
  );
}
