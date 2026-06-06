// Shape khớp dict trả về từ rag.ask / generate / suggest (xem rag.py, generate.py, api.py).

export interface ImageRef {
  key: string;
  url: string;
  alt?: string;
}

export interface Hit {
  source: string;
  url?: string;
  sim?: number;
  chunk_index?: number;
  text: string;
  images?: ImageRef[];
}

export interface Citation {
  source: string;
  url?: string;
  chunk_index?: number;
}

export interface AskResult {
  answer: string;
  sources: Citation[];
  hits: Hit[];
  refused: boolean;
  route: string;
  max_sim?: number;
  ungrounded_tk?: string[];
  ungrounded_refs?: string[];
  pii?: string[];
  blocked?: string;
  error?: boolean;
}

export interface GenerateResult {
  task: string;
  label: string;
  output: string;
  redacted: boolean;
  pii: string[];
  route?: string;
  error?: boolean;
}

export interface TaskItem {
  key: string;
  label: string;
}

export interface TasksResult {
  draft: TaskItem[];
  util: TaskItem[];
}

export interface Health {
  status: string;
  provider: string;
  embed: string;
  store: string;
  route: string;
}

export interface ScoreHelp {
  answer_pass: number;
  answer_total: number;
  refuse_pass: number;
  refuse_total: number;
  kw_coverage?: number | string;
  ts?: string;
}

export interface ScoreAccounting {
  pass: number;
  total: number;
  guardrail7_flags?: number;
}

export interface Scoreboard {
  available: boolean;
  help?: ScoreHelp;
  accounting?: ScoreAccounting;
  error?: string;
}

export type Role = "user" | "assistant";

export interface ChatTurn {
  role: Role;
  content: string;
  // chỉ tin trợ lý mới có result (để render trust strip / nguồn / minh hoạ)
  result?: AskResult;
  condensed?: string; // câu hỏi đã viết lại (nếu khác)
}
