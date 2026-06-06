// Dùng chung cho tab Soạn nháp + Tiện ích (cùng luồng generate.generate). Mọi đầu ra là
// BẢN NHÁP — người dùng duyệt (DESIGN.md mục 5/9). KHÔNG dùng dữ liệu nghiệp vụ BRAVO.
import { useState } from "react";
import { api } from "../api";
import type { GenerateResult, TaskItem } from "../types";
import { Markdown } from "./Markdown";
import { Button, Chip, Field, Select, TextArea } from "./ui";

interface Props {
  tasks: TaskItem[];
  intro: string;
  placeholder: string;
  submitLabel: string;
  draftBadge: boolean; // tab Soạn nháp gắn "(bản nháp)" vào tiêu đề kết quả
}

export function GenerateView({ tasks, intro, placeholder, submitLabel, draftBadge }: Props) {
  const [task, setTask] = useState(tasks[0]?.key ?? "");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);

  async function run() {
    if (!input.trim() || loading) return;
    setLoading(true);
    try {
      setResult(await api.generate(task, input));
    } catch (e) {
      setResult({
        task,
        label: "Lỗi",
        output: `[Lỗi gọi API] ${(e as Error).message}.`,
        redacted: false,
        pii: [],
        error: true,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <p className="text-base text-ink-600">{intro}</p>

      <div className="grid gap-4 sm:grid-cols-[260px_1fr] sm:items-end">
        <Field label="Loại">
          <Select value={task} onChange={(e) => setTask(e.target.value)}>
            {tasks.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <Field label="Yêu cầu / nội dung">
        <TextArea
          rows={6}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
        />
      </Field>

      <Button variant="primary" loading={loading} disabled={!input.trim()} onClick={run}>
        {submitLabel}
      </Button>

      {result && (
        <div className="fade-in rounded-card border border-line bg-surface p-5">
          {result.redacted && (
            <div className="mb-3 rounded-lg border border-warn/20 bg-warn/10 p-3 text-sm text-warn">
              ⚠️ Đã ẩn PII trong đầu vào ({result.pii.join(", ")}) trước khi gửi cloud — bản nháp
              dùng placeholder [PHONE]/[EMAIL]…, anh/chị tự điền lại tại máy.
            </div>
          )}
          <div className="mb-2 flex items-center gap-2">
            <h3 className="text-lg font-semibold">
              {result.label}
              {draftBadge && <span className="text-ink-400"> (bản nháp)</span>}
            </h3>
            <Chip tone="warn">BẢN NHÁP — người dùng duyệt</Chip>
          </div>
          <Markdown>{result.output}</Markdown>
        </div>
      )}
    </div>
  );
}
