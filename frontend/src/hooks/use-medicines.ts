import { useState, useEffect, useMemo } from 'react';
import type { ComboboxOption } from '@/components/ui/combobox';

interface MedicinesData {
  medications: Record<string, string[]>;
}

/**
 * Fetches and processes the medicine dataset for the hierarchical selector.
 * The data is fetched once and cached for the lifetime of the component.
 */
export function useMedicines() {
  const [data, setData] = useState<MedicinesData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function fetchData() {
      // Ensure this runs only on the client
      if (typeof window === 'undefined') return;

      try {
        const response = await fetch('/medicines.json');
        if (!response.ok) {
          throw new Error(`Failed to fetch medicines data: ${response.statusText}`);
        }
        const jsonData: MedicinesData = await response.json();
        setData(jsonData);
      } catch (e) {
        console.error("Error fetching medicines.json:", e);
        setError(e as Error);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, []);

  const families = useMemo<ComboboxOption[]>(() => {
    if (!data?.medications) return [];
    return Object.keys(data.medications)
      .sort((a, b) => a.localeCompare(b))
      .map(family => ({
        value: family,
        label: family.charAt(0).toUpperCase() + family.slice(1), // Capitalize for display
      }));
  }, [data]);

  const variantsByFamily = useMemo<Record<string, string[]>>(() => {
    return data?.medications ? data.medications : {};
  }, [data]);

  return { families, variantsByFamily, isLoading, error };
}
