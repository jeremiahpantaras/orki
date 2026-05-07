import { env } from "@/shared/config/env";
import type { ApiErrorResponse } from "@/shared/types/api";

type RequestInitWithBody = RequestInit & {
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

export async function http<T>(path: string, init: RequestInitWithBody = {}): Promise<T> {
  const response = await fetch(`${env.NEXT_PUBLIC_API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
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

  return (await response.json()) as T;
}
