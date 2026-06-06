// Banner cảnh báo route (DESIGN.md mục 5): vàng warn khi cloud, xanh trust khi self-host.
// Suy ra từ health.route ("cloud:…" vs "self-host…"). KHÔNG chỉ dùng màu — kèm icon + chữ.
import type { Health } from "../types";

export function RouteBanner({ health }: { health: Health | null }) {
  if (!health) return null;
  const isCloud = /cloud/i.test(health.route) || /openai|gemini/i.test(health.provider);
  if (isCloud) {
    return (
      <div className="border-b border-warn/20 bg-warn/10 px-4 py-2 text-sm text-warn">
        ⚠️ Đang dùng AI <strong>cloud</strong> (<span className="font-mono">{health.provider}</span>
        ). Nội dung <strong>có thể gửi ra dịch vụ bên ngoài</strong> — chỉ dùng tài liệu CÔNG KHAI /
        văn bản không chứa dữ liệu cá nhân–khách hàng. PII (SĐT/email/MST/CCCD) được tự động ẩn
        trước khi gửi.
      </div>
    );
  }
  return (
    <div className="border-b border-trust/20 bg-trust/10 px-4 py-2 text-sm text-trust">
      🔒 Đang chạy <strong>self-host</strong> — không gửi dữ liệu ra ngoài.
    </div>
  );
}
