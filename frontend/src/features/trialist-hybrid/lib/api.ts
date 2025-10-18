/**
 * Trialist Hybrid API Client
 */

import { TrialistHybridRequest, TrialistHybridResponse, TrialistHybridNctResponse } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function parseTrialCriteria(
  request: TrialistHybridRequest
): Promise<TrialistHybridResponse> {
  const response = await fetch(`${API_BASE_URL}/api/agents/trialist/parse-hybrid`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

export async function parseFromNct(nctId: string): Promise<TrialistHybridNctResponse> {
  const response = await fetch(`${API_BASE_URL}/api/agents/trialist/parse-from-nct`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ nct_id: nctId }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

export const EXAMPLES = {
  simple: {
    criteria: 'Inclusion: Adult patients aged 18 years or older',
    nctId: 'NCT00000001',
    label: 'Simple (Age Only)',
  },
  septicShock: {
    criteria:
      'Inclusion: 1) Age >= 18 years 2) Septic shock with lactate > 2 mmol/L within 6 hours of ICU admission. Exclusion: 1) Pregnancy 2) History of myocardial infarction within 6 months',
    nctId: 'NCT03389555',
    label: 'Complex (Septic Shock Trial)',
  },
  ards: {
    criteria:
      'Inclusion: Age 18-80 years, Mechanical ventilation, PaO2/FiO2 ratio < 200. Exclusion: Severe COPD, Pregnancy',
    nctId: 'NCT00000002',
    label: 'Medium (ARDS Trial)',
  },
};
