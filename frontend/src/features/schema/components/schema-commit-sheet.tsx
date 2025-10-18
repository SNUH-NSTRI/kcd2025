'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';

interface SchemaCommitSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (message: string) => void;
  defaultMessage?: string;
  saving?: boolean;
}

export function SchemaCommitSheet({
  open,
  onOpenChange,
  onSubmit,
  defaultMessage = 'Document manual adjustments to schema elements.',
  saving = false,
}: SchemaCommitSheetProps) {
  const [message, setMessage] = useState(defaultMessage);

  useEffect(() => {
    if (open) {
      setMessage(defaultMessage);
    }
  }, [defaultMessage, open]);

  const handleSubmit = () => {
    const trimmed = message.trim();
    onSubmit(trimmed.length > 0 ? trimmed : defaultMessage);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="max-w-2xl mx-auto">
        <SheetHeader>
          <SheetTitle>Save schema version</SheetTitle>
          <SheetDescription>
            Provide a concise commit message describing the intent of this version.
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="schema-commit-message">Commit message</Label>
            <Textarea
              id="schema-commit-message"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="e.g., Aligned inclusion criteria with cardio-metabolic cohort"
              rows={4}
            />
          </div>
        </div>
        <SheetFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={saving}>
            {saving ? 'Saving…' : 'Save version'}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
