import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-start justify-center gap-6 px-6 py-20">
      <span className="inline-flex rounded-full border border-border px-3 py-1 text-sm text-muted">
        Orki Frontend Starter
      </span>
      <h1 className="text-4xl font-semibold tracking-tight">Your intelligent study buddy.</h1>
      <p className="max-w-2xl text-lg text-muted">
        This frontend is structured for scalable feature development with typed API modules, route groups, and reusable UI layers.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link className="rounded-xl bg-primary px-5 py-3 font-medium text-white" href="/dashboard">
          Go to Dashboard
        </Link>
        <Link className="rounded-xl border border-border px-5 py-3 font-medium" href="/login">
          Sign In
        </Link>
      </div>
    </main>
  );
}
