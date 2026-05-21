"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import { useNotification } from "@/providers/notification-provider";
import { routes } from "@/shared/config/routes";
import { http } from "@/shared/api/http";

type CheckoutResponse = {
  checkout_url: string;
  reference_id: string;
};

function SubscribeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading } = useAuth();
  const { notify } = useNotification();
  
  const [isLoading, setIsLoading] = useState(false);
  const [subscriptionStatus, setSubscriptionStatus] = useState<string | null>(null);
  const isVerifyingPayment = useRef(false);

  // Check if redirected from payment success and verify subscription is active
  useEffect(() => {
    const success = searchParams.get("success");
    const cancelled = searchParams.get("cancelled");
    
    if (success === "true" && !isVerifyingPayment.current) {
      isVerifyingPayment.current = true;
      notify(
        "✓ Payment received! Verifying subscription...",
        "success"
      );
      
      // Poll for subscription to become active.
      // On the first attempt we also call /payments/verify/ which syncs
      // the payment from PayMongo in case the webhook hasn't fired yet.
      const verifySubscription = async () => {
        for (let i = 0; i < 12; i++) {
          try {
            // On first pass, trigger a manual sync from PayMongo as a
            // webhook fallback.  Subsequent passes just poll the status.
            if (i === 0) {
              try {
                await http("payments/verify/", { method: "POST" });
              } catch {
                // Webhook may have already activated — ignore and continue polling.
              }
            }

            const data = await http<{ status: string }>(
              "users/subscription/"
            );
            console.log(`[Attempt ${i + 1}] Subscription status:`, data.status);

            if (data.status === "active") {
              notify("✓ Subscription activated! Redirecting to exams...", "success");
              setTimeout(() => router.replace(routes.exams), 500);
              return;
            }
          } catch (error) {
            console.error("Failed to verify subscription:", error);
          }

          // Wait 1s between retries (gives PayMongo webhook time to fire).
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        // If we got here, subscription didn't activate in time
        notify(
          "Payment confirmed but subscription hasn't activated yet. Redirecting to exams...",
          "info"
        );
        setTimeout(() => router.replace(routes.exams), 2000);
      };
      
      verifySubscription();
    }
    
    if (cancelled === "true") {
      notify("Payment was cancelled.", "info");
    }
  }, [searchParams, notify, router, isVerifyingPayment]);

  // Fetch current subscription status on initial load
  useEffect(() => {
    if (!user) return;

    const fetchSubscription = async () => {
      try {
        const data = await http<{ status: string }>("users/subscription/");
        console.log("Subscription status on load:", data.status);
        setSubscriptionStatus(data.status);
        if (data.status === "active") {
          router.replace(routes.exams);
        }
      } catch (error) {
        console.error("Failed to fetch subscription:", error);
      }
    };

    fetchSubscription();
  }, [user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-border border-t-primary" />
      </div>
    );
  }

  const handleSubscribe = async () => {
    setIsLoading(true);
    try {
      const data = await http<CheckoutResponse>("payments/checkout/", {
        method: "POST",
      });

      // Redirect to PayMongo payment gateway
      window.location.href = data.checkout_url;
    } catch (error) {
      notify(
        error instanceof Error ? error.message : "Failed to initiate payment. Please try again.",
        "error"
      );
      setIsLoading(false);
    }
  };

  return (
    <div className="animate-page-in min-h-screen flex flex-col items-center justify-center px-6 py-20">
      <div className="max-w-md text-center space-y-8">
        {/* Header */}
        <div className="space-y-3">
          <h1 className="font-heading text-3xl font-bold text-foreground">
            Unlock Premium Learning
          </h1>
          <p className="text-base text-muted">
            Get instant access to all practice exams and premium features
          </p>
        </div>

        {/* Pricing card */}
        <div className="glass rounded-2xl p-8 space-y-6">
          {/* Plan details */}
          <div className="space-y-4">
            <div>
              <p className="text-sm text-muted font-medium uppercase tracking-wide">Orki Pro</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="font-heading text-4xl font-bold text-foreground">₱49</span>
                <span className="text-sm text-muted">/month</span>
              </div>
            </div>

            {/* Benefits */}
            <div className="space-y-3 pt-4 border-t border-border">
              <Feature text="Unlimited access to all practice exams" />
              <Feature text="Detailed performance analytics" />
              <Feature text="Study streak tracking" />
              <Feature text="Priority support" />
            </div>
          </div>

          {/* CTA Button */}
          <button
            onClick={handleSubscribe}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-primary text-white font-semibold py-3 transition-all duration-200 hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Processing...
              </>
            ) : (
              <>
                Start Subscription
                <svg width="16" height="16" viewBox="0 0 14 14" fill="none">
                  <path
                    d="M5.25 2.917 9.333 7 5.25 11.083"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </>
            )}
          </button>

          {/* Payment methods */}
          <div className="space-y-2">
            <p className="text-[11px] text-muted font-medium uppercase tracking-widest">
              Accepted Payment Methods
            </p>
            <div className="flex items-center justify-center gap-3">
              <PaymentMethodBadge name="Card" />
              <PaymentMethodBadge name="GCash" />
              <PaymentMethodBadge name="PayMaya" />
            </div>
          </div>
        </div>

        {/* Security note */}
        <div className="flex items-center justify-center gap-2 text-[11px] text-muted">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path
              d="M7 1.75L3.25 3.5v3.5c0 3.15 3.75 4.25 3.75 4.25s3.75-1.1 3.75-4.25V3.5L7 1.75Z"
              stroke="currentColor"
              strokeWidth="1"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span>Secured by PayMongo. Your payment is encrypted.</span>
        </div>

        {/* Info */}
        {subscriptionStatus === "pending" && (
          <div className="rounded-xl bg-primary/10 border border-primary/20 px-4 py-3">
            <p className="text-xs text-primary font-medium">
              ⏳ Your subscription is pending admin verification. You&apos;ll receive a notification once activated.
            </p>
          </div>
        )}

        {/* FAQ / Help */}
        <div className="space-y-2 text-xs text-muted pt-4 border-t border-border">
          <p>After payment, your subscription will be pending admin verification.</p>
          <p>You&apos;ll receive a notification once your access is activated.</p>
        </div>
      </div>
    </div>
  );
}

function Feature({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-2.5">
      <svg width="16" height="16" viewBox="0 0 14 14" fill="none" className="mt-0.5 flex-shrink-0">
        <path
          d="M2 7l3 3 6-6"
          stroke="var(--primary)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="text-sm text-foreground">{text}</span>
    </div>
  );
}

function PaymentMethodBadge({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-overlay">
      <div className="h-3 w-3 rounded-full bg-primary/50" />
      <span className="text-[11px] font-medium text-foreground">{name}</span>
    </div>
  );
}

export default function SubscribePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-border border-t-primary" />
        </div>
      }
    >
      <SubscribeContent />
    </Suspense>
  );
}
