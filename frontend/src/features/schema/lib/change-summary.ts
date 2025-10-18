import type { TrialSchema } from '../types';

function diffStrings(prev: string, next: string, label: string, changes: string[]) {
  if (prev.trim() !== next.trim()) {
    changes.push(`${label} updated.`);
  }
}

function diffMetadata(prev: TrialSchema, next: TrialSchema, changes: string[]) {
  if (prev.metadata.journal !== next.metadata.journal) {
    changes.push('Journal metadata updated.');
  }
  if (prev.metadata.year !== next.metadata.year) {
    changes.push('Publication year adjusted.');
  }
  if (prev.metadata.source !== next.metadata.source) {
    changes.push('Primary source changed.');
  }
  if (prev.metadata.populationSynopsis !== next.metadata.populationSynopsis) {
    changes.push('Population synopsis revised.');
  }
}

function diffCriteria(prev: string[], next: string[], label: string, changes: string[]) {
  const prevSet = new Set(prev.map((item) => item.trim().toLowerCase()));
  const nextSet = new Set(next.map((item) => item.trim().toLowerCase()));

  const additions = Array.from(nextSet).filter((item) => !prevSet.has(item));
  const removals = Array.from(prevSet).filter((item) => !nextSet.has(item));

  if (additions.length > 0) {
    changes.push(`Added ${additions.length} ${label.toLowerCase()} item(s).`);
  }
  if (removals.length > 0) {
    changes.push(`Removed ${removals.length} ${label.toLowerCase()} item(s).`);
  }
}

function diffVariables(prev: TrialSchema, next: TrialSchema, changes: string[]) {
  const prevById = new Map(prev.variables.map((variable) => [variable.id, variable]));
  const nextById = new Map(next.variables.map((variable) => [variable.id, variable]));

  const added = next.variables.filter((variable) => !prevById.has(variable.id));
  const removed = prev.variables.filter((variable) => !nextById.has(variable.id));

  if (added.length > 0) {
    changes.push(`Added ${added.length} variable(s).`);
  }
  if (removed.length > 0) {
    changes.push(`Removed ${removed.length} variable(s).`);
  }

  next.variables.forEach((variable) => {
    const previous = prevById.get(variable.id);
    if (!previous) return;
    if (previous.name !== variable.name) {
      changes.push(`Renamed variable ${previous.name} to ${variable.name}.`);
    }
    if (previous.type !== variable.type) {
      changes.push(`Updated type for ${variable.name}.`);
    }
    if (previous.required !== variable.required) {
      changes.push(`Requirement flag changed for ${variable.name}.`);
    }
  });
}

function diffOutcomes(prev: TrialSchema, next: TrialSchema, changes: string[]) {
  const prevIds = new Set(prev.outcomes.map((outcome) => outcome.id));
  const nextIds = new Set(next.outcomes.map((outcome) => outcome.id));

  const added = next.outcomes.filter((outcome) => !prevIds.has(outcome.id));
  const removed = prev.outcomes.filter((outcome) => !nextIds.has(outcome.id));

  if (added.length > 0) {
    changes.push(`Added ${added.length} outcome(s).`);
  }
  if (removed.length > 0) {
    changes.push(`Removed ${removed.length} outcome(s).`);
  }
}

export function describeSchemaChanges(prev: TrialSchema, next: TrialSchema): string[] {
  const changes: string[] = [];

  diffStrings(prev.title, next.title, 'Title', changes);
  diffStrings(prev.objective, next.objective, 'Objective', changes);
  diffStrings(prev.population, next.population, 'Population', changes);
  diffStrings(prev.notes ?? '', next.notes ?? '', 'Notes', changes);

  diffMetadata(prev, next, changes);
  diffCriteria(prev.inclusionCriteria, next.inclusionCriteria, 'Inclusion criteria', changes);
  diffCriteria(prev.exclusionCriteria, next.exclusionCriteria, 'Exclusion criteria', changes);
  diffVariables(prev, next, changes);
  diffOutcomes(prev, next, changes);

  return changes.length > 0 ? Array.from(new Set(changes)) : ['No structural changes detected.'];
}
