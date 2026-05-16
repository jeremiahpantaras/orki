import { env } from "@/shared/config/env";
import type { ApiErrorResponse } from "@/shared/types/api";

type RequestInitWithBody = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export class ApiError extends Error {
  status: number;
  payload?: ApiErrorResponse;

  constructor(message: string, status: number, payload?: ApiErrorResponse) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

/**
 * Returns an Authorization header value with a fresh Firebase ID token,
 * or null when there is no authenticated Firebase user (e.g. SSR, logged out).
 */
async function getAuthorizationHeader(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  try {
    const { auth } = await import("@/shared/firebase/client");
    // Wait for Firebase to restore the persisted auth session before reading currentUser
    await auth.authStateReady();
    const token = await auth.currentUser?.getIdToken();
    return token ? `Bearer ${token}` : null;
  } catch {
    return null;
  }
}

export async function http<T>(path: string, init: RequestInitWithBody = {}): Promise<T> {
  const authHeader = await getAuthorizationHeader();

  const response = await fetch(`${env.NEXT_PUBLIC_API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authHeader ? { Authorization: authHeader } : {}),
      ...(init.headers ?? {}),
    },
    body: init.body ? JSON.stringify(init.body) : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    let payload: ApiErrorResponse | undefined;
    try {
      payload = (await response.json()) as ApiErrorResponse;
    } catch {
      payload = undefined;
    }

    throw new ApiError(payload?.detail ?? "Request failed.", response.status, payload);
  }

  // 204 No Content — return undefined cast to T
  if (response.status === 204) return undefined as T;

  return (await response.json()) as T;
}

