"use client";

import { useQuery } from "@tanstack/react-query";

import { http } from "@/shared/api/http";

type SubscriptionStatus = {
  status: string;
} | null;

type UseSubscriptionStatusReturn = {
  subscription: SubscriptionStatus;
  subLoading: boolean;
  isSubscribed: boolean;
};

/**
 * Fetches the current user's subscription status from the API.
 * Returns the raw `subscription` object, a `subLoading` flag, and a
 * derived `isSubscribed` boolean (true only when status === "active").
 *
 * Results are cached by React Query for 5 minutes — navigating between pages
 * will NOT trigger repeated network requests for the same user.
 *
 * Pass `userId` (or any truthy/falsy value) to control when the fetch fires.
 * Pass `null` / `undefined` to skip fetching (e.g. while auth is loading).
 */
export function useSubscriptionStatus(
  userId: string | null | undefined,
): UseSubscriptionStatusReturn {
  const { data, isLoading } = useQuery<SubscriptionStatus>({
    queryKey: ["subscription", userId],
    queryFn: async () => {
      try {
        return await http<{ status: string }>("users/subscription/");
      } catch {
        return null;
      }
    },
    enabled: !!userId,
    // Keep subscription fresh for 5 min; GC after 10 min of inactivity.
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    // On error treat as non-subscribed (paywall shown) — same as before.
    throwOnError: false,
  });

  return {
    subscription: data ?? null,
    // isLoading is true only on the first fetch when there is no cached data.
    subLoading: isLoading,
    isSubscribed: data?.status === "active",
  };
}
