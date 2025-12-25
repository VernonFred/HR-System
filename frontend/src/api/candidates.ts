// V45: 修复API路径 - 添加 /api 前缀以匹配后端路由
import { apiRequest } from "./client";
import { MOCK_CANDIDATES } from "./mocks/candidates";
import type { Candidate, CandidateListResponse } from "../types/candidate";

type CandidateQuery = {
  page?: number;
  pageSize?: number;
  keyword?: string;
  position?: string;
  status?: string;
};

export async function fetchCandidates(params: CandidateQuery = {}): Promise<CandidateListResponse> {
  const search = new URLSearchParams();
  if (params.page) search.append("page", String(params.page));
  if (params.pageSize) search.append("page_size", String(params.pageSize));
  if (params.keyword) search.append("keyword", params.keyword);
  if (params.position) search.append("position", params.position);
  if (params.status) search.append("status", params.status);
  const qs = search.toString();
  return apiRequest<CandidateListResponse>({
    path: `/api/candidates${qs ? `?${qs}` : ""}`,
    fallback: {
      items: MOCK_CANDIDATES,
      page: params.page || 1,
      pageSize: params.pageSize || MOCK_CANDIDATES.length,
      total: MOCK_CANDIDATES.length,
    },
    auth: true, // 使用真实接口，失败时仍可回退到 mock
  });
}

export async function fetchCandidate(id: number): Promise<Candidate | undefined> {
  const mock = MOCK_CANDIDATES.find((c) => c.id === id);
  return apiRequest<Candidate>({
    path: `/api/candidates/${id}`,
    fallback: mock,
    auth: true, // 使用真实接口，失败时仍可回退到 mock
  });
}
