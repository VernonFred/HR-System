import { defineStore } from "pinia";
import { login, refreshToken as refreshTokenRequest } from "../api/auth";
import type { LoginRequest } from "../types/auth";
import { clearTokens, getTokens, onTokenChange, saveTokens } from "../utils/authTokens";

// 解析 JWT token 获取用户信息
function parseJwt(token: string): { sub: number; username: string; role: string } | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => 
      '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
    ).join(''));
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

// 从 localStorage 获取用户信息
function getSavedUserInfo(): { username: string; role: string } | null {
  try {
    const saved = localStorage.getItem('userInfo');
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
}

// 保存用户信息到 localStorage
function saveUserInfo(username: string, role: string) {
  localStorage.setItem('userInfo', JSON.stringify({ username, role }));
}

// 清除用户信息
function clearUserInfo() {
  localStorage.removeItem('userInfo');
}

type UserInfo = {
  id: number;
  username: string;
  role: string;
};

type AuthState = {
  token: string;
  refreshToken: string;
  loading: boolean;
  error: string;
  synced: boolean;
  user: UserInfo | null;
};

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => {
    const tokens = getTokens();
    const savedUser = getSavedUserInfo();
    let user: UserInfo | null = null;
    
    // 尝试从 token 解析用户信息
    if (tokens.token) {
      const payload = parseJwt(tokens.token);
      if (payload) {
        user = {
          id: payload.sub,
          username: savedUser?.username || payload.username || "Admin",
          role: savedUser?.role || payload.role || "admin",
        };
      }
    }
    
    return {
      token: tokens.token,
      refreshToken: tokens.refreshToken,
    loading: false,
    error: "",
    synced: false,
      user,
    };
  },
  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.user?.username || "Admin",
    userRole: (state) => state.user?.role || "admin",
    userInitial: (state) => {
      const name = state.user?.username || "Admin";
      // 如果是中文名，取第一个字；如果是英文名，取首字母大写
      const firstChar = name.charAt(0);
      if (/[\u4e00-\u9fa5]/.test(firstChar)) {
        return firstChar; // 中文姓氏
      }
      return firstChar.toUpperCase(); // 英文首字母
    },
  },
  actions: {
    setToken(token: string, refresh?: string) {
      this.token = token;
      if (refresh) {
        this.refreshToken = refresh;
      }
      saveTokens(token, refresh || this.refreshToken);
      
      // 解析 token 获取用户信息
      const payload = parseJwt(token);
      if (payload) {
        const savedUser = getSavedUserInfo();
        this.user = {
          id: payload.sub,
          username: savedUser?.username || payload.username || "Admin",
          role: savedUser?.role || payload.role || "admin",
        };
      }
    },
    setUsername(username: string) {
      if (this.user) {
        this.user.username = username;
        saveUserInfo(username, this.user.role);
      }
    },
    clear() {
      clearTokens();
      clearUserInfo();
      this.token = "";
      this.refreshToken = "";
      this.error = "";
      this.user = null;
    },
    logout() {
      this.clear();
    },
    async login(payload: LoginRequest) {
      this.loading = true;
      this.error = "";
      try {
        const res = await login(payload);
        this.setToken(res.access_token, res.refresh_token);
      } catch (err) {
        this.error = (err as Error).message || "登录失败";
        throw err;
      } finally {
        this.loading = false;
      }
    },
    async refresh() {
      if (!this.refreshToken) throw new Error("缺少刷新令牌");
      const res = await refreshTokenRequest(this.refreshToken);
      this.setToken(res.access_token, res.refresh_token);
      return res;
    },
    startSync() {
      if (this.synced) return;
      this.synced = true;
      onTokenChange((token, refreshToken) => {
        this.token = token;
        this.refreshToken = refreshToken;
      });
    },
  },
});
