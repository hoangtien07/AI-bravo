import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { CHAPTERS } from "../constants";
import type { ChatTurn } from "../types";
import { Markdown } from "./Markdown";
import { Sources } from "./Sources";
import { TrustStrip } from "./TrustStrip";
import { Button, Chip, Field, Select, TextInput } from "./ui";

interface Props {
  k: number;
  minSim: number;
}

export function ChatView({ k, minSim }: Props) {
  const [chapter, setChapter] = useState<string>(CHAPTERS[0]);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [feedbackDone, setFeedbackDone] = useState<Record<number, "up" | "down">>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  async function ask() {
    const question = q.trim();
    if (!question || loading) return;
    const history = turns.map((t) => ({ role: t.role, content: t.content }));
    const userTurn: ChatTurn = { role: "user", content: question };
    setTurns((t) => [...t, userTurn]);
    setQ("");
    setSuggestions([]);
    setLoading(true);
    try {
      const chap = chapter === CHAPTERS[0] ? null : chapter;
      const r = await api.ask(question, { k, min_sim: minSim, chapter: chap, history });
      setTurns((t) => [...t, { role: "assistant", content: r.answer, result: r }]);
      // gợi ý câu hỏi liên quan (grounded, có thể rỗng) — tách endpoint, không chặn câu trả lời
      api
        .suggest(question, { k, min_sim: minSim })
        .then((s) => setSuggestions(s.questions || []))
        .catch(() => setSuggestions([]));
    } catch (e) {
      setTurns((t) => [
        ...t,
        {
          role: "assistant",
          content: `[Lỗi gọi API] ${(e as Error).message}. Kiểm tra uvicorn api:app đã chạy chưa.`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function sendFeedback(idx: number, question: string, rating: "up" | "down") {
    setFeedbackDone((f) => ({ ...f, [idx]: rating }));
    api.feedback(question, rating).catch(() => {});
  }

  return (
    <div className="space-y-5">
      <p className="text-base text-ink-600">
        Hỏi về <strong>nghiệp vụ / cấu hình BRAVO</strong> — trả lời CÓ TRÍCH NGUỒN, từ chối khi
        không có trong tài liệu. <em>(Hệ THAM CHIẾU có cảnh báo — không thay kế toán.)</em>
      </p>

      <div className="max-w-sm">
        <Field label="Phân hệ (lọc nguồn)">
          <Select value={chapter} onChange={(e) => setChapter(e.target.value)}>
            {CHAPTERS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      {/* Lịch sử hội thoại đa lượt */}
      <div className="space-y-4">
        {turns.map((t, i) =>
          t.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="fade-in max-w-[85%] rounded-card bg-brand-50 px-4 py-2.5 text-base text-ink-900">
                {t.content}
              </div>
            </div>
          ) : (
            <div key={i} className="fade-in rounded-card border border-line bg-surface px-4 py-3.5">
              <Markdown>{t.content}</Markdown>
              {t.result && <TrustStrip r={t.result} />}
              {t.result && <Sources r={t.result} />}
              {/* phản hồi 👍/👎 cho câu trả lời này */}
              <div className="mt-3 flex items-center gap-2">
                {feedbackDone[i] ? (
                  <span className="text-sm text-ink-400">
                    {feedbackDone[i] === "up" ? "Cảm ơn phản hồi!" : "Đã ghi nhận."}
                  </span>
                ) : (
                  <>
                    <Button
                      variant="ghost"
                      className="h-8 px-2"
                      onClick={() => sendFeedback(i, turns[i - 1]?.content || "", "up")}
                    >
                      👍
                    </Button>
                    <Button
                      variant="ghost"
                      className="h-8 px-2"
                      onClick={() => sendFeedback(i, turns[i - 1]?.content || "", "down")}
                    >
                      👎
                    </Button>
                  </>
                )}
              </div>
            </div>
          )
        )}

        {loading && (
          <div className="flex items-center gap-2 text-sm text-ink-600">
            <Chip tone="brand">Đang tra cứu…</Chip>
          </div>
        )}
      </div>

      {/* Gợi ý câu hỏi liên quan */}
      {suggestions.length > 0 && !loading && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-ink-600">Câu hỏi liên quan:</span>
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => setQ(s)}
              className="rounded-full border border-brand-600/20 bg-brand-50 px-3 py-1 text-sm text-brand-700 hover:bg-brand-50/70"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Ô nhập câu hỏi (cố định cuối luồng) */}
      <div className="sticky bottom-0 -mx-1 bg-canvas/80 px-1 pb-1 pt-2 backdrop-blur">
        <div className="flex gap-2">
          <TextInput
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              // không submit khi đang gõ dấu tiếng Việt (IME composition) — tránh gửi câu dở
              if (e.key === "Enter" && !e.nativeEvent.isComposing) ask();
            }}
            placeholder="Hỏi nghiệp vụ / định khoản / cấu hình BRAVO…"
          />
          <Button variant="primary" loading={loading} disabled={!q.trim()} onClick={ask}>
            Hỏi
          </Button>
        </div>
      </div>
      <div ref={bottomRef} />
    </div>
  );
}
