import { apiRequestWithBody } from "./client";
import type { LoginRequest, LoginResponse } from "../types/auth";

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  return apiRequestWithBody<LoginResponse>({
    path: "/auth/login",
    method: "POST",
    body: payload,
  });
}

export async function refreshToken(refresh_token: string): Promise<LoginResponse> {
  return apiRequestWithBody<LoginResponse>({
    path: "/auth/refresh",
    method: "POST",
    body: { refresh_token },
    auth: false,
  });
}
