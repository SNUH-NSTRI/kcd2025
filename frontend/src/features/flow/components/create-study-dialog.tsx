'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Combobox, type ComboboxOption } from '@/components/ui/combobox';
import { PlusCircle, Loader2 } from 'lucide-react';
import { useFlow } from '../context';
import { useMedicines } from '@/hooks/use-medicines';
import {
  getTrialDetails,
  type TrialDetail,
  type TrialSummary,
} from '@/remote/api/clinicaltrials';
import { createStudy } from '@/remote/api/studies';
import { loadCorpusData, getTrialTitleFromCorpus } from '@/lib/corpus-loader';

interface CreateStudyDialogProps {
  trigger?: React.ReactNode;
  // Controlled mode props
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  prefilledNctId?: string;
  prefilledTrialData?: TrialDetail | TrialSummary;
}

const initialFormData = {
  name: '',
  purpose: '',
  nctId: '',
  medicineFamily: '',
  medicine: '', // This will store the selected variant
};

export function CreateStudyDialog({
  trigger,
  open: controlledOpen,
  onOpenChange: controlledOnOpenChange,
  prefilledNctId
}: CreateStudyDialogProps) {
  const router = useRouter();
  const { createNewStudy } = useFlow();

  // Dual-mode: controlled or uncontrolled
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const setIsOpen = controlledOnOpenChange || setInternalOpen;

  const [formData, setFormData] = useState(initialFormData);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isFetchingTitle, setIsFetchingTitle] = useState(false);

  // Fetch medicine data
  const { families, variantsByFamily, isLoading: isLoadingMedicines } = useMedicines();

  // Sync prefilledNctId to form state when dialog opens
  useEffect(() => {
    if (isOpen) {
      // Reset the form to ensure a clean state, then apply the prefilled ID
      setFormData({
        ...initialFormData,
        nctId: prefilledNctId || '',
      });
    }
  }, [isOpen, prefilledNctId]);

  // Auto-fill study name from local corpus.json
  useEffect(() => {
    const nctId = formData.nctId.trim();

    // Only fetch if NCT ID is valid format and name is empty (avoid overwriting user input)
    if (!nctId || !/^NCT\d{8}$/.test(nctId) || formData.name.trim() !== '') {
      return;
    }

    const loadTitle = async () => {
      setIsFetchingTitle(true);
      try {
        // Load from local corpus.json instead of API
        const corpusData = await loadCorpusData(nctId);
        const title = getTrialTitleFromCorpus(corpusData);

        if (title) {
          setFormData(prev => ({
            ...prev,
            name: title,
          }));
        } else {
          console.warn(`No title found in corpus for ${nctId}`);
          // Fallback: API 호출 (corpus가 없는 경우에만)
          const response = await getTrialDetails(nctId);
          if (response.status === 'success' && response.study?.briefTitle) {
            setFormData(prev => ({
              ...prev,
              name: response.study!.briefTitle,
            }));
          }
        }
      } catch (error) {
        console.error('Failed to load trial title:', error);
      } finally {
        setIsFetchingTitle(false);
      }
    };

    // No debounce needed - local file is fast!
    loadTitle();
  }, [formData.nctId, formData.name]);

  const handleFamilyChange = (familyValue: string) => {
    setFormData(prev => ({
      ...prev,
      medicineFamily: familyValue,
      medicine: '', // Reset variant when family changes
    }));
  };

  const variantOptions = useMemo<ComboboxOption[]>(() => {
    if (!formData.medicineFamily || !variantsByFamily) {
      return [];
    }
    const variants = variantsByFamily[formData.medicineFamily] || [];
    return variants.map(variant => ({
      value: variant,
      label: variant,
    }));
  }, [formData.medicineFamily, variantsByFamily]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate form
    if (!formData.name.trim() || !formData.purpose.trim() || !formData.nctId.trim() || !formData.medicine.trim()) {
      return;
    }

    setIsSubmitting(true);
    try {
      // Call backend API to create study and start background processing
      const response = await createStudy({
        name: formData.name,
        nctId: formData.nctId,
        researchQuestion: formData.purpose,
        medicineFamily: formData.medicineFamily,
        medicineGeneric: formData.medicine, // Use selected variant as generic
      });

      // Also update local flow state (for backward compatibility)
      await createNewStudy({
        name: formData.name,
        purpose: formData.purpose,
        nctId: formData.nctId,
        medicine: formData.medicine,
      });

      // Close dialog
      setIsOpen(false);

      // Navigate to study-specific schema page
      router.push(`/schema/${response.studyId}`);

      // Form will be reset by useEffect on next open
    } catch (error) {
      console.error('Failed to create study:', error);
      // TODO: Show toast notification to user
      alert('Failed to create study. Please check the NCT ID and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {/* Only render trigger in uncontrolled mode */}
      {controlledOpen === undefined && (
        <DialogTrigger asChild>
          {trigger || (
            <Button size="lg" className="gap-2">
              <PlusCircle className="h-5 w-5" />
              Create New Study
            </Button>
          )}
        </DialogTrigger>
      )}
      <DialogContent className="sm:max-w-2xl">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create New Study</DialogTitle>
            <DialogDescription>
              Enter the details for your new study to begin the analysis workflow.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="study-name">
                Study Name <span className="text-destructive">*</span>
                {isFetchingTitle && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    <Loader2 className="inline h-3 w-3 animate-spin" /> Fetching title...
                  </span>
                )}
              </Label>
              <Input
                id="study-name"
                placeholder="e.g., Hydrocortisone Efficacy in Sepsis"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                disabled={isFetchingTitle}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="study-purpose">
                Research Question / Purpose <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="study-purpose"
                placeholder="Describe the primary research question or objective of this study..."
                value={formData.purpose}
                onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
                rows={4}
                required
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="nct-id">
                ClinicalTrials.gov ID <span className="text-destructive">*</span>
              </Label>
              <Input
                id="nct-id"
                placeholder="NCT12345678"
                value={formData.nctId}
                onChange={(e) => setFormData({ ...formData, nctId: e.target.value })}
                pattern="^NCT\d{8}$"
                required
              />
              <p className="text-sm text-muted-foreground">
                Enter the NCT ID from ClinicalTrials.gov (e.g., NCT03389555)
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="medicine-family">
                Medicine Family <span className="text-destructive">*</span>
              </Label>
              <Combobox
                options={families}
                value={formData.medicineFamily}
                onValueChange={handleFamilyChange}
                placeholder="Select family..."
                searchPlaceholder="Search families..."
                emptyText="No family found."
                loading={isLoadingMedicines}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="medicine-variant">
                Medicine Variant <span className="text-destructive">*</span>
              </Label>
              <Combobox
                options={variantOptions}
                value={formData.medicine}
                onValueChange={(value) => setFormData({ ...formData, medicine: value })}
                placeholder="Select variant..."
                searchPlaceholder="Search variants..."
                emptyText="No variants available."
                disabled={!formData.medicineFamily}
              />
              <p className="text-sm text-muted-foreground">
                First select a medicine family, then choose a specific variant.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!formData.name.trim() || !formData.purpose.trim() || !formData.nctId.trim() || !formData.medicine.trim() || isSubmitting}
            >
              {isSubmitting ? 'Creating...' : 'Create Study'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
