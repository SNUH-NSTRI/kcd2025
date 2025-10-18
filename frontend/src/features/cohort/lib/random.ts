function hashSeed(input: string): number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export interface SeededRng {
  next(): number;
  nextInt(min: number, max: number): number;
  nextFloat(min: number, max: number): number;
  pick<T>(items: T[]): T;
  boolean(trueProbability?: number): boolean;
}

export function createSeededRng(seed: string): SeededRng {
  let state = hashSeed(seed) || 1;

  const nextRaw = () => {
    state = Math.imul(48271, state) % 0x7fffffff;
    return state / 0x7fffffff;
  };

  return {
    next: nextRaw,
    nextInt(min: number, max: number) {
      const low = Math.ceil(min);
      const high = Math.floor(max);
      return Math.floor(nextRaw() * (high - low + 1)) + low;
    },
    nextFloat(min: number, max: number) {
      return nextRaw() * (max - min) + min;
    },
    pick<T>(items: T[]) {
      if (items.length === 0) {
        throw new Error('Cannot pick from empty array');
      }
      const index = Math.floor(nextRaw() * items.length);
      return items[index];
    },
    boolean(trueProbability = 0.5) {
      return nextRaw() < trueProbability;
    },
  };
}
