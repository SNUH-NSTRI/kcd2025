/**
 * Medicine API types
 */

export interface Medicine {
  parent: string;
  variant: string;
  display: string;
}

export interface SearchMedicinesParams {
  q: string;
  limit?: number;
}
