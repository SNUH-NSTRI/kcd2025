export function generateRunId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `run-${Math.random().toString(36).slice(2, 10)}`;
}
