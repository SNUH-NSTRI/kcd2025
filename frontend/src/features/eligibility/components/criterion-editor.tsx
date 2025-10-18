'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Plus, Trash2, GripVertical } from 'lucide-react';
import type { EligibilityCriterion } from '../types';

// Predefined options for form dropdowns
const CRITERION_KEYS = [
  'Age',
  'Condition',
  'Lab Value',
  'Vital Sign',
  'ECOG Performance',
  'Karnofsky Score',
  'Pregnancy Status',
  'Organ Function',
  'Medication History',
  'Surgery History',
  'Comorbidity',
  'Prior Treatment',
  'Genetic Marker',
  'Imaging Result',
  'Consent Ability',
  'Study Compliance',
  'Other',
] as const;

const OPERATORS = [
  '>=',
  '<=',
  '==',
  '!=',
  '>',
  '<',
  'in',
  'not_in',
  'between',
  'contains',
] as const;

const UNITS = [
  'years',
  'months',
  'days',
  'mg/dL',
  'mmHg',
  'mmol/L',
  'g/dL',
  'cells/mm³',
  '%',
  'score',
  'none',
] as const;

interface CriterionEditorProps {
  criterion: EligibilityCriterion;
  index: number;
  onUpdate: (index: number, updated: EligibilityCriterion) => void;
  onRemove: (index: number) => void;
  criterionType: 'inclusion' | 'exclusion';
}

/**
 * Criterion Editor Component
 *
 * Form-based editor for individual eligibility criterion.
 * Prevents JSON errors by enforcing structured input.
 */
export function CriterionEditor({
  criterion,
  index,
  onUpdate,
  onRemove,
  criterionType,
}: CriterionEditorProps) {
  const handleFieldChange = (field: keyof EligibilityCriterion, value: any) => {
    onUpdate(index, {
      ...criterion,
      [field]: value,
    });
  };

  return (
    <Card className="relative">
      <div className="absolute left-2 top-3 cursor-move text-muted-foreground hover:text-foreground">
        <GripVertical className="h-5 w-5" />
      </div>
      <CardContent className="pt-6 pl-10 pr-4 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant={criterionType === 'inclusion' ? 'default' : 'destructive'}>
              {criterionType === 'inclusion' ? 'Inclusion' : 'Exclusion'}
            </Badge>
            <span className="text-sm font-mono text-muted-foreground">{criterion.id}</span>
          </div>
          <Button variant="ghost" size="icon" onClick={() => onRemove(index)}>
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>

        {/* Key Field */}
        <div className="space-y-2">
          <Label htmlFor={`key-${index}`}>Criterion Key *</Label>
          <Select
            value={criterion.key}
            onValueChange={(value) => handleFieldChange('key', value)}
          >
            <SelectTrigger id={`key-${index}`}>
              <SelectValue placeholder="Select criterion type..." />
            </SelectTrigger>
            <SelectContent>
              {CRITERION_KEYS.map((key) => (
                <SelectItem key={key} value={key}>
                  {key}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Operator & Value Row */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor={`operator-${index}`}>Operator *</Label>
            <Select
              value={criterion.operator}
              onValueChange={(value) => handleFieldChange('operator', value)}
            >
              <SelectTrigger id={`operator-${index}`}>
                <SelectValue placeholder="Select operator..." />
              </SelectTrigger>
              <SelectContent>
                {OPERATORS.map((op) => (
                  <SelectItem key={op} value={op}>
                    {op}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor={`value-${index}`}>
              Value *
              {(criterion.operator === 'in' || criterion.operator === 'not_in') && (
                <span className="ml-1 text-xs text-muted-foreground">
                  (comma-separated)
                </span>
              )}
            </Label>
            <Input
              id={`value-${index}`}
              value={
                Array.isArray(criterion.value)
                  ? criterion.value.join(', ')
                  : String(criterion.value)
              }
              onChange={(e) => {
                const rawValue = e.target.value;
                // Parse value based on operator
                if (criterion.operator === 'in' || criterion.operator === 'not_in') {
                  const values = rawValue.split(',').map((v) => v.trim());
                  handleFieldChange('value', values);
                } else if (criterion.operator === 'between') {
                  const values = rawValue.split(',').map((v) => parseFloat(v.trim()));
                  handleFieldChange('value', values);
                } else {
                  // Single value - try to parse as number
                  const num = parseFloat(rawValue);
                  handleFieldChange('value', isNaN(num) ? rawValue : num);
                }
              }}
              placeholder="Enter value..."
            />
          </div>
        </div>

        {/* Unit Field */}
        <div className="space-y-2">
          <Label htmlFor={`unit-${index}`}>Unit</Label>
          <Select
            value={criterion.unit || 'none'}
            onValueChange={(value) =>
              handleFieldChange('unit', value === 'none' ? undefined : value)
            }
          >
            <SelectTrigger id={`unit-${index}`}>
              <SelectValue placeholder="Select unit..." />
            </SelectTrigger>
            <SelectContent>
              {UNITS.map((unit) => (
                <SelectItem key={unit} value={unit}>
                  {unit === 'none' ? '(No unit)' : unit}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Original Text */}
        <div className="space-y-2">
          <Label htmlFor={`original-text-${index}`}>Original Text *</Label>
          <Textarea
            id={`original-text-${index}`}
            value={criterion.original_text}
            onChange={(e) => handleFieldChange('original_text', e.target.value)}
            placeholder="Enter the original criterion text from NCT..."
            rows={3}
            className="resize-none"
          />
        </div>
      </CardContent>
    </Card>
  );
}

interface CriteriaEditorListProps {
  criteria: EligibilityCriterion[];
  criterionType: 'inclusion' | 'exclusion';
  onUpdate: (criteria: EligibilityCriterion[]) => void;
}

/**
 * Criteria Editor List Component
 *
 * Manages a list of criteria (inclusion or exclusion).
 */
export function CriteriaEditorList({
  criteria,
  criterionType,
  onUpdate,
}: CriteriaEditorListProps) {
  const handleUpdateCriterion = (index: number, updated: EligibilityCriterion) => {
    const newCriteria = [...criteria];
    newCriteria[index] = updated;
    onUpdate(newCriteria);
  };

  const handleRemoveCriterion = (index: number) => {
    const newCriteria = criteria.filter((_, i) => i !== index);
    onUpdate(newCriteria);
  };

  const handleAddCriterion = () => {
    const newId = `${criterionType.substring(0, 3)}_${Date.now()}`;
    const newCriterion: EligibilityCriterion = {
      id: newId,
      key: 'Age',
      operator: '>=',
      value: '',
      original_text: '',
    };
    onUpdate([...criteria, newCriterion]);
  };

  return (
    <div className="space-y-4">
      {/* Criteria List */}
      {criteria.length > 0 ? (
        <div className="space-y-3">
          {criteria.map((criterion, index) => (
            <CriterionEditor
              key={criterion.id}
              criterion={criterion}
              index={index}
              onUpdate={handleUpdateCriterion}
              onRemove={handleRemoveCriterion}
              criterionType={criterionType}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border-2 border-dashed border-muted-foreground/30 bg-muted/10 p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No {criterionType} criteria yet. Click "Add Criterion" to create one.
          </p>
        </div>
      )}

      {/* Add Button */}
      <Button variant="outline" onClick={handleAddCriterion} className="w-full">
        <Plus className="mr-2 h-4 w-4" />
        Add {criterionType === 'inclusion' ? 'Inclusion' : 'Exclusion'} Criterion
      </Button>
    </div>
  );
}
