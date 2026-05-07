export type ExamStatus = "scheduled" | "in_progress" | "completed";

export type Exam = {
  id: string;
  title: string;
  scheduledAt: string;
  durationMinutes: number;
  status: ExamStatus;
};
