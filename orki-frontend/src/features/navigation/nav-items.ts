import { routes } from "@/shared/config/routes";

export const navItems = [
  { href: routes.dashboard, label: "Dashboard" },
  { href: routes.analytics, label: "Analytics" },
  { href: routes.exams, label: "Exams" },
  { href: routes.flashcards, label: "Flashcards" },
  { href: routes.profile, label: "Profile" },
] as const;
