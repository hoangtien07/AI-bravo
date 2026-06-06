import { useEffect, useState } from "react";
import { api } from "./api";
import { TABS, type TabKey } from "./constants";
import type { Health, Scoreboard, TasksResult } from "./types";
import { ChatView } from "./components/ChatView";
import { GenerateView } from "./components/GenerateView";
import { RouteBanner } from "./components/RouteBanner";
import { Sidebar } from "./components/Sidebar";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [scoreboard, setScoreboard] = useState<Scoreboard | null>(null);
  const [tasks, setTasks] = useState<TasksResult | null>(null);
  const [tab, setTab] = useState<TabKey>("qa");
  const [k, setK] = useState(4);
  const [minSim, setMinSim] = useState(0.3);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    api.scoreboard().then(setScoreboard).catch(() => setScoreboard(null));
    api.tasks().then(setTasks).catch(() => setTasks(null));
  }, []);

  return (
    <div className="min-h-full">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-[1240px] items-center gap-3 px-4 py-3.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-lg text-white">
            🤖
          </div>
          <div>
            <h1 className="text-md font-semibold leading-tight">ChatAI BRAVO</h1>
            <p className="text-xs text-ink-400">Trợ lý nghiệp vụ & năng suất — RAG có dẫn chứng</p>
          </div>
        </div>
      </header>
      <RouteBanner health={health} />

      <div className="mx-auto grid max-w-[1240px] gap-6 px-4 py-6 lg:grid-cols-[300px_1fr]">
        <Sidebar
          health={health}
          scoreboard={scoreboard}
          k={k}
          setK={setK}
          minSim={minSim}
          setMinSim={setMinSim}
        />

        <main className="min-w-0">
          {/* Tab điều hướng */}
          <nav className="mb-5 flex gap-1 border-b border-line">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`-mb-px border-b-2 px-4 py-2.5 text-base font-medium transition-colors ${
                  tab === t.key
                    ? "border-brand-600 text-brand-700"
                    : "border-transparent text-ink-600 hover:text-ink-900"
                }`}
              >
                <span className="mr-1.5">{t.icon}</span>
                {t.label}
              </button>
            ))}
          </nav>

          <div className="rounded-card border border-line bg-surface p-5 sm:p-6">
            {tab === "qa" && <ChatView k={k} minSim={minSim} />}
            {tab === "draft" && (
              <GenerateView
                tasks={tasks?.draft ?? []}
                intro="Sinh BẢN NHÁP từ yêu cầu của anh/chị (không dùng dữ liệu nghiệp vụ BRAVO)."
                placeholder="VD: nhắc công nợ quá hạn 30 ngày, giọng lịch sự, có hạn thanh toán mới"
                submitLabel="Soạn nháp"
                draftBadge
              />
            )}
            {tab === "util" && (
              <GenerateView
                tasks={tasks?.util ?? []}
                intro="Tiện ích văn phòng trên văn bản anh/chị dán vào."
                placeholder="Dán văn bản cần dịch / soát / tóm tắt, hoặc mô tả nhu cầu công thức Excel…"
                submitLabel="Thực hiện"
                draftBadge={false}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
