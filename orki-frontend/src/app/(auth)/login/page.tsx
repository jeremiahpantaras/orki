"use client";

import Link from "next/link";
import { useState } from "react";

import { routes } from "@/shared/config/routes";
import { signInWithGoogle } from "@/shared/firebase/auth";

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleSignIn = async () => {
    setIsLoading(true);
    setError(null);

    try {
      await signInWithGoogle();
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : "Google sign-in failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-[80vh] w-full max-w-md flex-col justify-center gap-4 px-6">
      <h1 className="text-3xl font-semibold">Sign in</h1>
      <p className="text-muted">Authenticate to continue your study progress in Orki.</p>
      <button
        className="rounded-xl bg-primary px-4 py-3 font-medium text-white disabled:opacity-70"
        type="button"
        onClick={handleGoogleSignIn}
        disabled={isLoading}
      >
        {isLoading ? "Signing in..." : "Continue with Google"}
      </button>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <p className="text-sm text-muted">
        New here?{" "}
        <Link className="font-medium text-primary" href={routes.register}>
          Create an account
        </Link>
      </p>
    </main>
  );
}
