import type { AnalyticsOverview } from "@/entities/analytics/types";
import type { DashboardSummary } from "@/entities/dashboard/types";
import type { Exam } from "@/entities/exams/types";
import type { Flashcard } from "@/entities/flashcards/types";
import { http } from "@/shared/api/http";

export function getDashboardSummary() {
  return http<DashboardSummary>("dashboard/");
}

export function getAnalyticsOverview() {
  return http<AnalyticsOverview>("analytics/");
}

export function getExams() {
  return http<Exam[]>("exams/");
}

export function getFlashcards() {
  return http<Flashcard[]>("flashcards/");
}
