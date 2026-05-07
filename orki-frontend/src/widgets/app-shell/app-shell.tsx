"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { navItems } from "@/features/navigation/nav-items";
import { routes } from "@/shared/config/routes";

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
          <Link className="text-xl font-semibold tracking-tight text-primary" href={routes.dashboard}>
            Orki
          </Link>
          <nav className="flex items-center gap-2">
            {navItems.map((item) => {
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  className={`rounded-lg px-3 py-2 text-sm transition ${
                    isActive ? "bg-primary text-white" : "text-muted hover:text-foreground"
                  }`}
                  href={item.href}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
