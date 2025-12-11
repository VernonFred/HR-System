import { apiRequest } from "./client";
import type { AnalyticsSummary } from "../types/analytics";
import { MOCK_ANALYTICS } from "./mocks/analytics";

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  return apiRequest<AnalyticsSummary>({
    path: "/analytics/summary",
    fallback: MOCK_ANALYTICS,
    auth: true,
  });
}
