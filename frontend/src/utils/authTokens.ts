const TOKEN_KEY = "token";
const REFRESH_KEY = "refreshToken";
const EVENT = "auth-token-changed";

export function getTokens(): { token: string; refreshToken: string } {
  return {
    token: localStorage.getItem(TOKEN_KEY) || "",
    refreshToken: localStorage.getItem(REFRESH_KEY) || "",
  };
}

export function saveTokens(token: string, refreshToken?: string) {
  localStorage.setItem(TOKEN_KEY, token);
  if (refreshToken) {
    localStorage.setItem(REFRESH_KEY, refreshToken);
  }
  emit(token, refreshToken);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  emit("", "");
}

export function onTokenChange(cb: (token: string, refreshToken: string) => void) {
  const handler = (e: Event) => {
    const detail = (e as CustomEvent).detail || {};
    cb(detail.token || "", detail.refreshToken || "");
  };
  window.addEventListener(EVENT, handler as EventListener);
  return () => window.removeEventListener(EVENT, handler as EventListener);
}

function emit(token: string, refreshToken?: string) {
  window.dispatchEvent(
    new CustomEvent(EVENT, {
      detail: { token, refreshToken: refreshToken || localStorage.getItem(REFRESH_KEY) || "" },
    })
  );
}
