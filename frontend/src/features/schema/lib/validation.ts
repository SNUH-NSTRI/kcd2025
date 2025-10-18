import type { SchemaValidationIssue, TrialSchema } from '../types';

function makeIssue(
  path: string,
  message: string,
  severity: SchemaValidationIssue['severity'],
): SchemaValidationIssue {
  return {
    id: `${path}-${severity}`,
    path,
    message,
    severity,
  };
}

export function validateSchema(schema: TrialSchema): SchemaValidationIssue[] {
  const issues: SchemaValidationIssue[] = [];

  if (!schema.title.trim()) {
    issues.push(makeIssue('title', 'Title is required.', 'error'));
  }
  if (!schema.objective.trim()) {
    issues.push(makeIssue('objective', 'Objective is required to guide downstream analysis.', 'error'));
  }
  if (!schema.population.trim()) {
    issues.push(makeIssue('population', 'Population narrative is required.', 'error'));
  }
  if (!schema.metadata.journal.trim()) {
    issues.push(makeIssue('metadata.journal', 'Source journal or registry must be recorded.', 'error'));
  }
  if (!schema.metadata.source.trim()) {
    issues.push(makeIssue('metadata.source', 'Primary data source must be set.', 'error'));
  }
  if (schema.metadata.year === null) {
    issues.push(makeIssue('metadata.year', 'Publication year missing. Confirm chronology.', 'warning'));
  }

  if (schema.inclusionCriteria.length === 0) {
    issues.push(makeIssue('inclusion', 'At least one inclusion criteria is required.', 'error'));
  }
  if (schema.exclusionCriteria.length === 0) {
    issues.push(makeIssue('exclusion', 'Add exclusion criteria or confirm none apply.', 'warning'));
  }
  if (schema.variables.length === 0) {
    issues.push(makeIssue('variables', 'Define at least one variable to materialise cohort queries.', 'error'));
  }

  const variableNames = new Map<string, number>();
  schema.variables.forEach((variable, index) => {
    if (!variable.name.trim()) {
      issues.push(makeIssue(`variables[${index}].name`, 'Variable name is required.', 'error'));
    }
    if (!variable.description.trim()) {
      issues.push(
        makeIssue(
          `variables[${index}].description`,
          'Add a short description to document provenance.',
          'warning',
        ),
      );
    }
    const normalized = variable.name.trim().toLowerCase();
    if (normalized) {
      const count = variableNames.get(normalized) ?? 0;
      variableNames.set(normalized, count + 1);
    }
  });

  for (const [name, count] of variableNames.entries()) {
    if (count > 1) {
      issues.push(makeIssue('variables.duplicate', `Variable "${name}" appears ${count} times.`, 'error'));
    }
  }

  const inclusionNormalized = schema.inclusionCriteria.map((item) => item.trim().toLowerCase());
  const exclusionNormalized = schema.exclusionCriteria.map((item) => item.trim().toLowerCase());
  inclusionNormalized.forEach((item, index) => {
    const matchedIndex = exclusionNormalized.indexOf(item);
    if (matchedIndex >= 0) {
      issues.push(
        makeIssue(
          `criteria.conflict.${index}-${matchedIndex}`,
          `Criterion "${schema.inclusionCriteria[index]}" is also listed as exclusion ${matchedIndex + 1}.`,
          'error',
        ),
      );
    }
  });

  return issues;
}
