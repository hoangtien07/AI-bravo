// Sidebar: cấu hình truy hồi (k, ngưỡng) + bảng điểm độ tin cậy. Biến rào chắn → hữu hình.
import type { Health, Scoreboard } from "../types";

interface Props {
  health: Health | null;
  scoreboard: Scoreboard | null;
  k: number;
  setK: (v: number) => void;
  minSim: number;
  setMinSim: (v: number) => void;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 text-sm">
      <span className="text-ink-600">{label}</span>
      <span className="truncate font-mono text-xs text-ink-900">{value}</span>
    </div>
  );
}

export function Sidebar({ health, scoreboard, k, setK, minSim, setMinSim }: Props) {
  const h = scoreboard?.help;
  const a = scoreboard?.accounting;
  return (
    <aside className="flex flex-col gap-5">
      <section className="rounded-card border border-line bg-surface p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-600">
          Cấu hình
        </h2>
        <div className="space-y-1.5">
          {health ? (
            <>
              <Row label="LLM" value={health.provider} />
              <Row label="Embedding" value={health.embed} />
              <Row label="Store" value={health.store} />
              <Row label="Route" value={health.route} />
            </>
          ) : (
            <p className="text-sm text-ink-400">Đang kết nối API…</p>
          )}
        </div>

        <div className="mt-4 space-y-4 border-t border-line pt-4">
          <label className="block">
            <div className="mb-1 flex justify-between text-sm">
              <span className="text-ink-600">Số đoạn truy hồi (k)</span>
              <span className="font-mono text-ink-900">{k}</span>
            </div>
            <input
              type="range"
              min={1}
              max={8}
              value={k}
              onChange={(e) => setK(Number(e.target.value))}
              className="w-full accent-brand-600"
            />
          </label>
          <label className="block">
            <div className="mb-1 flex justify-between text-sm">
              <span className="text-ink-600">Ngưỡng tương đồng</span>
              <span className="font-mono text-ink-900">{minSim.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={minSim}
              onChange={(e) => setMinSim(Number(e.target.value))}
              className="w-full accent-brand-600"
            />
            <p className="mt-1 text-xs text-ink-400">Dưới ngưỡng → trợ lý từ chối thay vì đoán.</p>
          </label>
        </div>
      </section>

      <section className="rounded-card border border-line bg-surface p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-600">
          📊 Bảng điểm độ tin cậy
        </h2>
        {scoreboard?.available ? (
          <div className="space-y-3">
            {h && (
              <div>
                <div className="text-sm font-medium text-ink-900">Hỏi-đáp help</div>
                <div className="mt-1 flex gap-4">
                  <div>
                    <div className="text-xl font-semibold text-trust">
                      {h.answer_pass}/{h.answer_total}
                    </div>
                    <div className="text-xs text-ink-400">trả lời đạt</div>
                  </div>
                  <div>
                    <div className="text-xl font-semibold text-brand-700">
                      {h.refuse_pass}/{h.refuse_total}
                    </div>
                    <div className="text-xs text-ink-400">từ chối đúng</div>
                  </div>
                </div>
                {h.ts && (
                  <div className="mt-1 text-xs text-ink-400">
                    kw_cov {String(h.kw_coverage)} · {h.ts.slice(0, 10)}
                  </div>
                )}
              </div>
            )}
            {a && (
              <div className="border-t border-line pt-3">
                <div className="text-sm font-medium text-ink-900">Định khoản (exact-match TK)</div>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-xl font-semibold text-warn">
                    {a.pass}/{a.total}
                  </span>
                  <span className="text-xs text-ink-400">cờ #7: {a.guardrail7_flags ?? 0}</span>
                </div>
                <div className="mt-1 text-xs text-warn">⚠️ ground-truth chờ mentor duyệt</div>
              </div>
            )}
            <p className="text-xs text-ink-400">
              Số liệu theo lần chạy gần nhất. KHÔNG hứa 0 sai — RAG pháp lý top vẫn ảo 17–33%
              (Stanford 2025). Hệ THAM CHIẾU + cảnh báo, người duyệt.
            </p>
          </div>
        ) : (
          <p className="text-sm text-ink-400">
            Chạy <code className="font-mono text-xs">python eval.py</code> +{" "}
            <code className="font-mono text-xs">eval.py --accounting</code> để sinh bảng điểm.
          </p>
        )}
      </section>

      <p className="px-1 text-xs text-ink-400">
        Mọi đầu ra "Soạn nháp"/"Tiện ích" là <strong>BẢN NHÁP</strong> — người dùng kiểm tra &
        duyệt.
      </p>
    </aside>
  );
}
