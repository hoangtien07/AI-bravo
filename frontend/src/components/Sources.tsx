// Trích nguồn deep-link + (tuỳ chọn) đoạn audit thô. "đoạn #" trung thực — help SPA
// không có 'trang' thật (DESIGN.md mục 5, anti-pattern: không giấu citation).
import { useState } from "react";
import type { AskResult, Citation } from "../types";
import { Illustrated } from "./Illustrated";

function SourceLink({ c }: { c: Citation }) {
  const seg = c.chunk_index != null ? ` — đoạn #${c.chunk_index}` : "";
  return (
    <li>
      {c.url ? (
        <a
          href={c.url}
          target="_blank"
          rel="noreferrer"
          className="text-brand-600 hover:underline"
        >
          {c.source}
        </a>
      ) : (
        <span>{c.source}</span>
      )}
      <span className="text-ink-400">{seg}</span>
    </li>
  );
}

export function Sources({ r }: { r: AskResult }) {
  const [showAudit, setShowAudit] = useState(false);
  const illustrated = (r.hits || []).filter((h) => h.images && h.images.length > 0).slice(0, 3);

  return (
    <div className="mt-4 space-y-3">
      {r.sources?.length > 0 && (
        <div>
          <div className="mb-1 text-sm font-medium text-ink-600">
            Nguồn (deep-link tới help, kèm đoạn):
          </div>
          <ul className="space-y-0.5 pl-4 text-base [list-style:disc]">
            {r.sources.map((c, i) => (
              <SourceLink key={i} c={c} />
            ))}
          </ul>
        </div>
      )}

      {illustrated.length > 0 && (
        <details open className="rounded-card border border-line bg-canvas p-3">
          <summary className="cursor-pointer text-sm font-medium text-ink-600">
            📖 Minh hoạ từ tài liệu (có ảnh) — {illustrated.length} đoạn
          </summary>
          <p className="mt-1 text-xs text-ink-400">
            Ảnh trích NGUYÊN VĂN từ help.bravo.com.vn theo đúng vị trí trong bài. Ảnh KHÔNG gửi
            qua AI — chỉ hiển thị tại máy.
          </p>
          <div className="mt-3 space-y-4">
            {illustrated.map((h, i) => (
              <div key={i} className="border-t border-line pt-3 first:border-t-0 first:pt-0">
                <div className="mb-1 text-sm font-medium">
                  {h.source}
                  {h.chunk_index != null && (
                    <span className="text-ink-400"> — đoạn #{h.chunk_index}</span>
                  )}
                  {h.url && (
                    <a
                      href={h.url}
                      target="_blank"
                      rel="noreferrer"
                      className="ml-2 text-brand-600 hover:underline"
                    >
                      mở help
                    </a>
                  )}
                </div>
                <Illustrated hit={h} />
              </div>
            ))}
          </div>
        </details>
      )}

      {r.hits?.length > 0 && (
        <div>
          <button
            onClick={() => setShowAudit((v) => !v)}
            className="text-sm text-ink-600 hover:text-brand-600"
          >
            {showAudit ? "▾" : "▸"} Đoạn tài liệu đã truy hồi (audit)
          </button>
          {showAudit && (
            <div className="mt-2 space-y-2">
              {r.hits.map((h, i) => (
                <div key={i} className="rounded-lg border border-line bg-canvas p-2.5">
                  <div className="text-sm font-medium">
                    {h.source}{" "}
                    <span className="font-normal text-ink-400">
                      (sim={h.sim}, đoạn #{h.chunk_index})
                    </span>
                  </div>
                  <pre className="mt-1 whitespace-pre-wrap text-xs text-ink-600">
                    {h.text.slice(0, 500)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
