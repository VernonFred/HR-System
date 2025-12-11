import router from "../router";
import { useAuthStore } from "../stores/auth";
import { getTokens } from "../utils/authTokens";

type FetchOptions<T> = {
  path: string;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: any;
  headers?: Record<string, string>;
  fallback?: T;
  baseUrl?: string;
  auth?: boolean;
  token?: string;
};

// 动态获取API地址
// 在开发环境下使用空字符串（让Vite代理处理）
// 在生产环境或局域网访问时使用实际后端地址
const getDefaultBase = () => {
  // 如果设置了环境变量，优先使用
  if (import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE;
  }
  
  // 获取当前页面的主机名
  const hostname = window.location.hostname;
  
  // 在开发环境下，如果是 localhost 或 127.0.0.1，使用空字符串让 Vite 代理处理
  if (import.meta.env.DEV && (hostname === 'localhost' || hostname === '127.0.0.1')) {
    return ''; // 使用相对路径，让 Vite 代理处理
  }
  
  // 如果是 localhost 或 127.0.0.1（生产环境），使用本地后端
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://127.0.0.1:9000';
  }
  
  // 如果是局域网IP访问，使用相同IP的后端端口9000
  return `http://${hostname}:9000`;
};

const DEFAULT_BASE = getDefaultBase();

export async function apiRequest<T>({ path, fallback, baseUrl, headers, auth, token }: FetchOptions<T>): Promise<T> {
  const url = `${baseUrl || DEFAULT_BASE}${path}`;
  // V45: 修复 - doFetch 必须正确接收并使用 token 参数
  const doFetch = (tk?: string) =>
    fetch(url, {
      headers: buildHeaders(headers, tk),
    });
  try {
    // V45: 修复 - 传递 doFetch 函数本身，而不是闭包
    const res = auth ? await withAuthRetry(doFetch, token) : await doFetch(token);
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return (await res.json()) as T;
  } catch (err) {
    if (fallback !== undefined) {
      console.warn(`[api mock] ${url} failed, use fallback:`, err);
      return fallback;
    }
    throw err;
  }
}

export async function apiRequestWithBody<T>({
  path,
  method = "POST",
  body,
  headers,
  fallback,
  baseUrl,
  auth,
  token,
}: FetchOptions<T>): Promise<T> {
  const url = `${baseUrl || DEFAULT_BASE}${path}`;
  // V45: 修复 - doFetch 必须正确接收并使用 token 参数
  const doFetch = (tk?: string) =>
    fetch(url, {
      method,
      headers: buildHeaders({ "Content-Type": "application/json", ...(headers || {}) }, tk),
      body: body ? JSON.stringify(body) : undefined,
    });
  try {
    // V45: 修复 - 传递 doFetch 函数本身，而不是闭包
    const res = auth ? await withAuthRetry(doFetch, token) : await doFetch(token);
    
    // V47: 改进错误处理 - 包含响应体详情
    if (!res.ok) {
      let errorDetail;
      try {
        errorDetail = await res.json();
      } catch {
        errorDetail = { message: `Request failed: ${res.status}` };
      }
      const error: any = new Error(`Request failed: ${res.status}`);
      error.status = res.status;
      error.detail = errorDetail.detail || errorDetail;
      error.response = { status: res.status, data: errorDetail };
      throw error;
    }
    
    // 如果是204 No Content，返回空对象而不是解析JSON
    if (res.status === 204) {
      return {} as T;
    }
    return (await res.json()) as T;
  } catch (err) {
    if (fallback !== undefined) {
      console.warn(`[api mock] ${url} failed, use fallback:`, err);
      return fallback;
    }
    throw err;
  }
}

function buildHeaders(base?: Record<string, string>, token?: string) {
  const headers: Record<string, string> = { ...(base || {}) };
  const bearer = token || headers["Authorization"];
  if (bearer && !headers["Authorization"]) {
    headers["Authorization"] = bearer.startsWith("Bearer ") ? bearer : `Bearer ${bearer}`;
  }
  return headers;
}

// V45: 修复 - withAuthRetry 接收 doFetch 函数和初始 token
async function withAuthRetry(
  doFetch: (token?: string) => Promise<Response>,
  initialTokenParam?: string
): Promise<Response> {
  const store = useAuthStore();
  const tokens = getTokens();
  // 优先使用传入的 token，其次从 store 或 localStorage 获取
  const initialToken = initialTokenParam || store.token || tokens.token || import.meta.env.VITE_AUTH_TOKEN || "";
  const refreshToken = store.refreshToken || tokens.refreshToken || "";

  console.log("[auth] Making request with token:", initialToken ? `${initialToken.substring(0, 20)}...` : "none");
  let res = await doFetch(initialToken || undefined);
  if (res.status !== 401) return res;

  console.log("[auth] Got 401, attempting token refresh...");
  if (!refreshToken) {
    console.log("[auth] No refresh token available");
    return handleUnauthorized(store);
  }

  try {
    // refresh() 返回新的 token，直接使用返回值
    const refreshResult = await store.refresh();
    const newToken = refreshResult.access_token;
    console.log("[auth] Token refreshed successfully, retrying with new token:", newToken.substring(0, 20) + "...");
    res = await doFetch(newToken);
    if (res.status !== 401) return res;
    console.log("[auth] Still got 401 after refresh");
  } catch (err) {
    console.warn("[auth] Refresh token failed:", err);
    return handleUnauthorized(store);
  }

  return handleUnauthorized(store);
}

function handleUnauthorized(store: ReturnType<typeof useAuthStore>): never {
  store.clear();
  router.push({ name: "login" });
  throw new Error("未登录或会话已过期，请重新登录");
}
