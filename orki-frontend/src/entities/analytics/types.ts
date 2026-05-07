export type AnalyticsPoint = {
  label: string;
  score: number;
};

export type AnalyticsOverview = {
  averageScore: number;
  masteryLevel: "low" | "medium" | "high";
  trend: AnalyticsPoint[];
};
