import { mockCostBenchmarks, type CostBenchmark } from '../mocks/costBenchmarks';

export const findBenchmarkByCode = (code?: string): CostBenchmark | undefined => {
  if (!code) return undefined;
  return mockCostBenchmarks.find((entry) => entry.code.toLowerCase() === code.toLowerCase());
};

export const evaluateLineItemAgainstBenchmark = (amount: number, benchmark?: CostBenchmark) => {
  if (!benchmark) {
    return {
      isOverpriced: false,
      variance: 0,
    };
  }

  const variance = amount - benchmark.averageCost;
  return {
    isOverpriced: variance > 0,
    variance,
    benchmark,
  };
};
