"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/hooks/useAuth";
import { getSubscriptionHistory } from "@/shared/api/profile";
import { routes } from "@/shared/config/routes";
import { HistoryRow } from "@/widgets/profile/subscription-history-card";

export default function PaymentHistoryPage() {
  const { user } = useAuth();

  const { data, isLoading } = useQuery({
    queryKey: ["subscription-history", user?.uid],
    queryFn: getSubscriptionHistory,
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
  });

  const history = data?.history ?? [];

  return (
    <div className="animate-page-in mx-auto max-w-2xl space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href={routes.profile}
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-overlay-hover transition-colors hover:bg-overlay-hover-mid"
          aria-label="Back to profile"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
              d="M10 3L5 8l5 5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-foreground"
            />
          </svg>
        </Link>
        <div className="space-y-0.5">
          <h1 className="font-heading text-2xl font-bold tracking-tight text-foreground">
            Payment History
          </h1>
          <p className="text-sm text-muted">All your Orki subscription transactions.</p>
        </div>
      </div>

      {/* Summary badge */}
      {!isLoading && history.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            {history.length} transaction{history.length !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Table */}
      <div className="glass overflow-hidden rounded-2xl">
        {isLoading ? (
          <div className="space-y-0 divide-y divide-border/50">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse px-5 py-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <div className="h-3.5 w-36 rounded-full bg-overlay-hover" />
                    <div className="h-2.5 w-24 rounded-full bg-overlay-hover/70" />
                  </div>
                  <div className="h-4 w-16 rounded-full bg-overlay-hover" />
                </div>
              </div>
            ))}
          </div>
        ) : history.length === 0 ? (
          <div className="flex flex-col items-center gap-3 px-5 py-16 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-overlay-hover">
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                <rect
                  x="3"
                  y="5"
                  width="16"
                  height="14"
                  rx="2"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  className="text-muted"
                />
                <path
                  d="M3 9h16"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  className="text-muted"
                />
                <path
                  d="M7 3v4M15 3v4"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  className="text-muted"
                />
              </svg>
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">No transactions yet</p>
              <p className="text-xs text-muted">
                Your payment history will appear here after your first subscription.
              </p>
            </div>
            <Link
              href={routes.subscribe}
              className="mt-2 rounded-xl bg-primary px-5 py-2 text-xs font-semibold text-white transition hover:opacity-90"
            >
              Subscribe Now
            </Link>
          </div>
        ) : (
          <>
            {/* Desktop header */}
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
              {history.map((entry) => (
                <HistoryRow key={entry.id} entry={entry} />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Footer note */}
      {!isLoading && history.length > 0 && (
        <p className="text-center text-[11px] text-muted">
          Payments are processed securely by PayMongo.
        </p>
      )}
    </div>
  );
}
