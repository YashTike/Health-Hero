export interface CostBenchmark {
  code: string;
  description: string;
  averageCost: number;
  lowCost: number;
  highCost: number;
}

export const mockCostBenchmarks: CostBenchmark[] = [
  {
    code: '99213',
    description: 'Office/outpatient visit, established patient',
    averageCost: 125,
    lowCost: 90,
    highCost: 180,
  },
  {
    code: '80050',
    description: 'General health panel',
    averageCost: 280,
    lowCost: 200,
    highCost: 450,
  },
  {
    code: '93000',
    description: 'Electrocardiogram (ECG/EKG)',
    averageCost: 85,
    lowCost: 60,
    highCost: 140,
  },
  {
    code: 'J1885',
    description: 'Injection, ketorolac tromethamine, per 15 mg',
    averageCost: 45,
    lowCost: 25,
    highCost: 75,
  },
  {
    code: '87086',
    description: 'Culture, bacterial; quantitative colony count',
    averageCost: 55,
    lowCost: 30,
    highCost: 95,
  },
];
