import { apiRequestWithBody } from "./client";
import type { SubmissionRequest, SubmissionResponse } from "../types/submission";

export async function submitAnswers(
  payload: SubmissionRequest,
  token?: string
): Promise<SubmissionResponse> {
  return apiRequestWithBody<SubmissionResponse>({
    path: "/submissions",
    method: "POST",
    body: payload,
    auth: true,
    token,
  });
}
