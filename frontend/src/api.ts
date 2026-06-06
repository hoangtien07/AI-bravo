// Client gọi FastAPI (api.py). Đường dẫn TƯƠNG ĐỐI — dev qua proxy Vite, prod cùng origin.
import type {
  AskResult,
  GenerateResult,
  Health,
  Role,
  Scoreboard,
  TasksResult,
} from "./types";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export interface AskOpts {
  k?: number;
  min_sim?: number;
  chapter?: string | null;
  history?: { role: Role; content: string }[];
}

export const api = {
  health: () => get<Health>("/healthz"),
  scoreboard: () => get<Scoreboard>("/scoreboard"),
  tasks: () => get<TasksResult>("/tasks"),

  ask: (question: string, opts: AskOpts = {}) =>
    post<AskResult>("/ask", { question, ...opts }),

  suggest: (question: string, opts: { k?: number; min_sim?: number } = {}) =>
    post<{ questions: string[] }>("/suggest", { question, ...opts }),

  generate: (task: string, input: string) =>
    post<GenerateResult>("/generate", { task, input }),

  feedback: (question: string, rating: "up" | "down") =>
    post<{ ok: boolean }>("/feedback", { question, rating }),
};
