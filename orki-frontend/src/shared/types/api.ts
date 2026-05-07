export type ApiListResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type ApiErrorResponse = {
  detail?: string;
  message?: string;
  [key: string]: unknown;
};
