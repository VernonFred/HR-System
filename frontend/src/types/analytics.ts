export type AnalyticsBucket = {
  name: string;
  value: number;
};

export type RadarIndicator = {
  name: string;
  max: number;
};

export type RadarSeries = {
  name: string;
  value: number[];
};

export type TrendSeries = {
  name: string;
  data: number[];
};

export type AnalyticsSummary = {
  positionDistribution: AnalyticsBucket[];
  matchDistribution: AnalyticsBucket[];
  radarIndicators: RadarIndicator[];
  radarSeries: RadarSeries[];
  personalityPie: AnalyticsBucket[];
  dimensionTrendLabels: string[];
  dimensionTrendSeries: TrendSeries[];
  gradeCutoffs?: Record<string, number>;
  totalCandidates?: number;
  avgScore?: number;
};
