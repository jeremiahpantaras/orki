import { http } from "@/shared/api/http";

export type PaymentHistoryEntry = {
  id: string;
  amount_php: number;
  currency: string;
  status: string;
  payment_method: string;
  payment_id: string;
  plan_name: string;
  payment_confirmed_at: string | null;
  start_date: string | null;
  expiry_date: string | null;
};

export type SubscriptionDetail = {
  status: string;
  is_active: boolean;
  plan: string;
  payment_methods_allowed: string[];
  expires_at: string | null;
  days_remaining: number | null;
  payment_method: string | null;
};

export function getSubscriptionDetail(): Promise<SubscriptionDetail> {
  return http<SubscriptionDetail>("users/subscription/");
}

export function getSubscriptionHistory(): Promise<{ history: PaymentHistoryEntry[] }> {
  return http<{ history: PaymentHistoryEntry[] }>("profile/subscription-history/");
}

export function deactivateAccount(): Promise<{ detail: string }> {
  return http<{ detail: string }>("profile/deactivate/", { method: "POST" });
}

export function deleteAccount(): Promise<{ detail: string }> {
  return http<{ detail: string }>("profile/delete-account/", { method: "DELETE" });
}
