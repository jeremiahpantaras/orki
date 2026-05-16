import type { SessionUser } from "@/shared/types/session";
import { http } from "@/shared/api/http";

export type SessionResponse = {
  user: SessionUser;
  onboarding_complete: boolean;
};

/**
 * Create or retrieve the Firestore user profile on the backend.
 * The Firebase ID token is automatically added as an Authorization: Bearer
 * header by http.ts — no need to pass it explicitly.
 */
export function loginWithBackend(): Promise<SessionResponse> {
  return http<SessionResponse>("auth/login/", {
    method: "POST",
  });
}

/** Stateless logout — client clears Firebase Auth state. */
export function logoutFromBackend(): Promise<void> {
  return http<void>("auth/logout/", { method: "POST" });
}

/**
 * Validate the current Firebase token and return the Firestore user profile.
 * Returns 401 (ApiError) if the token is missing or invalid.
 */
export function getSession(): Promise<SessionResponse> {
  return http<SessionResponse>("auth/session/");
}

/**
 * Save the onboarding profile to the backend and mark onboarding complete.
 */
export function saveOnboarding(data: {
  first_name: string;
  last_name: string;
  age: number;
  exam_type: string;
  exam_date?: string | null;
}): Promise<{ detail: string; user: SessionUser }> {
  return http("users/onboarding/", {
    method: "POST",
    body: data,
  });
}

