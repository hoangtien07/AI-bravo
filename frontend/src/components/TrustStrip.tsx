// Trust strip — biến rào chắn vô hình thành HỮU HÌNH (định vị đo lường, DESIGN.md mục 5/8).
// KHÔNG bao giờ chỉ dùng màu: luôn kèm icon + chữ (anti-pattern mục 9).
import type { AskResult } from "../types";
import { Chip } from "./ui";

export function TrustStrip({ r }: { r: AskResult }) {
  const ut = r.ungrounded_tk || [];
  const uref = r.ungrounded_refs || [];
  const flags = [...ut, ...uref.map((x) => `TT/Điều ${x}`)];
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      {r.max_sim != null && (
        <Chip tone="neutral">
          độ khớp nguồn <span className="font-mono font-semibold">{r.max_sim}</span>
        </Chip>
      )}
      {r.route && (
        <Chip tone="neutral">
          route <span className="font-mono">{r.route}</span>
        </Chip>
      )}
      {flags.length > 0 ? (
        <Chip tone="warn">⚠️ chưa có trong nguồn: {flags.join(", ")}</Chip>
      ) : (
        <Chip tone="trust">✅ mọi mã TK/văn bản trích đều có trong nguồn</Chip>
      )}
    </div>
  );
}
