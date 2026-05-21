"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/hooks/useAuth";
import { getSubscriptionHistory, type PaymentHistoryEntry } from "@/shared/api/profile";
import { routes } from "@/shared/config/routes";

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  gcash: "GCash",
  paymaya: "Maya",
  card: "Card",
  qrph: "QRPh",
  unknown: "—",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatAmount(amount: number, currency: string): string {
  return `${currency} ${Number(amount).toFixed(2)}`;
}

export function SubscriptionHistoryCard() {
  const { user } = useAuth();

  const { data, isLoading } = useQuery({
    queryKey: ["subscription-history", user?.uid],
    queryFn: getSubscriptionHistory,
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
  });

  const history = data?.history ?? [];
  const preview = history.slice(0, 2);
  const hasMore = history.length > 2;

  if (isLoading) {
    return (
      <div className="space-y-2">
        <h3 className="px-1 text-xs font-semibold uppercase tracking-widest text-muted">
          Payment History
        </h3>
        <div className="glass overflow-hidden rounded-2xl p-5 animate-pulse space-y-3">
          {[0, 1].map((i) => (
            <div key={i} className="h-14 rounded-xl bg-overlay-hover" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted">
          Payment History
        </h3>
        {history.length > 0 && (
          <Link
            href={routes.paymentHistory}
            className="text-[11px] font-semibold text-primary transition-opacity hover:opacity-70"
          >
            View All
          </Link>
        )}
      </div>
      <div className="glass overflow-hidden rounded-2xl">
        {history.length === 0 ? (
          <div className="px-5 py-8 text-center">
            <p className="text-sm text-muted">No payment history yet.</p>
          </div>
        ) : (
          <>
            {/* Desktop header row */}
            <div className="hidden sm:grid grid-cols-[1fr_auto_auto_auto] gap-4 border-b border-border/50 bg-overlay-hover/30 px-5 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted">Plan</p>
              <p className="w-24 text-right text-[10px] font-semibold uppercase tracking-widest text-muted">
                Method
              </p>
              <p className="w-28 text-right text-[10px] font-semibold uppercase tracking-widest text-muted">
                Date
              </p>
              <p className="w-20 text-right text-[10px] font-semibold uppercase tracking-widest text-muted">
                Amount
              </p>
            </div>
            <div className="divide-y divide-border/50">
              {preview.map((entry) => (
                <HistoryRow key={entry.id} entry={entry} />
              ))}
            </div>
            {hasMore && (
              <div className="border-t border-border/50 bg-overlay-hover/20 px-5 py-3 text-center">
                <Link
                  href={routes.paymentHistory}
                  className="text-xs font-semibold text-primary transition-opacity hover:opacity-70"
                >
                  View all {history.length} transactions →
                </Link>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export function HistoryRow({ entry }: { entry: PaymentHistoryEntry }) {
  const methodLabel =
    PAYMENT_METHOD_LABELS[entry.payment_method] ?? entry.payment_method;

  return (
    <div className="px-5 py-4">
      {/* Mobile layout */}
      <div className="flex items-start justify-between sm:hidden">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-foreground">{entry.plan_name}</p>
            <span className="rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-success">
              {entry.status}
            </span>
          </div>
          <p className="text-xs text-muted">
            {methodLabel} · {formatDate(entry.payment_confirmed_at)}
          </p>
          {entry.expiry_date && (
            <p className="text-[11px] text-muted">
              Valid until {formatDate(entry.expiry_date)}
            </p>
          )}
        </div>
        <p className="ml-4 shrink-0 text-sm font-bold text-foreground">
          {formatAmount(entry.amount_php, entry.currency)}
        </p>
      </div>

      {/* Desktop layout */}
      <div className="hidden sm:grid grid-cols-[1fr_auto_auto_auto] items-center gap-4">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-foreground">{entry.plan_name}</p>
            <span className="rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-success">
              {entry.status}
            </span>
          </div>
          {entry.expiry_date && (
            <p className="text-[11px] text-muted">
              Valid until {formatDate(entry.expiry_date)}
            </p>
          )}
        </div>
        <p className="w-24 text-right text-xs text-muted">{methodLabel}</p>
        <p className="w-28 text-right text-xs text-muted">
          {formatDate(entry.payment_confirmed_at)}
        </p>
        <p className="w-20 text-right text-sm font-bold text-foreground">
          {formatAmount(entry.amount_php, entry.currency)}
        </p>
      </div>
    </div>
  );
}
