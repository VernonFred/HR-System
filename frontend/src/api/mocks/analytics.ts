import type { AnalyticsSummary } from "../../types/analytics";

export const MOCK_ANALYTICS: AnalyticsSummary = {
  positionDistribution: [
    { name: "产品", value: 32 },
    { name: "后端", value: 24 },
    { name: "前端", value: 18 },
    { name: "数据", value: 12 },
  ],
  matchDistribution: [
    { name: ">90", value: 8 },
    { name: "80-90", value: 14 },
    { name: "70-80", value: 22 },
    { name: "<70", value: 10 },
  ],
  radarIndicators: [
    { name: "外向 E", max: 24 },
    { name: "神经 N", max: 24 },
    { name: "精神 P", max: 24 },
    { name: "掩饰 L", max: 24 },
  ],
  radarSeries: [
    { name: "候选人 A", value: [18, 10, 12, 16] },
    { name: "理想模型", value: [20, 12, 14, 18] },
  ],
  personalityPie: [
    { name: "外向型", value: 40 },
    { name: "内向型", value: 32 },
    { name: "中性", value: 18 },
  ],
  dimensionTrendLabels: ["近1周", "近1月", "近3月"],
  dimensionTrendSeries: [
    { name: "外向 E", data: [18, 19, 20] },
    { name: "神经 N", data: [10, 11, 12] },
    { name: "精神 P", data: [12, 12, 13] },
    { name: "掩饰 L", data: [16, 16, 17] },
  ],
  gradeCutoffs: { A: 18, B: 12, C: 8 },
  totalCandidates: 120,
  avgScore: 79.6,
};
