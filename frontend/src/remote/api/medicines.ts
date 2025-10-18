/**
 * Medicine search API client
 */

import { apiClient } from "../client";
import type { Medicine, SearchMedicinesParams } from "../types/medicines";

/**
 * Search for medicines by query string
 */
export async function searchMedicines({
  q,
  limit = 20,
}: SearchMedicinesParams): Promise<Medicine[]> {
  const params = new URLSearchParams({
    q,
    limit: limit.toString(),
  });

  const response = await apiClient.get<Medicine[]>(
    `/api/medicines/search?${params.toString()}`
  );

  return response;
}
