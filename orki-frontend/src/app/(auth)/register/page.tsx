import Link from "next/link";

import { routes } from "@/shared/config/routes";

export default function RegisterPage() {
  return (
    <main className="mx-auto flex min-h-[80vh] w-full max-w-md flex-col justify-center gap-4 px-6">
      <h1 className="text-3xl font-semibold">Create account</h1>
      <p className="text-muted">Set up your Orki profile and begin your board exam journey.</p>
      <button className="rounded-xl bg-primary px-4 py-3 font-medium text-white" type="button">
        Register with email
      </button>
      <p className="text-sm text-muted">
        Already have an account?{" "}
        <Link className="font-medium text-primary" href={routes.login}>
          Sign in
        </Link>
      </p>
    </main>
  );
}
