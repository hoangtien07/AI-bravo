"""
analytics.py — Báo cáo COVERAGE/observability từ log, KHÔNG gọi LLM (offline, miễn phí).

Đọc:
  data/audit_log.jsonl  — mỗi truy vấn (q đã redact PII, sources, provider/model, route, refused, blocked, pii)
  data/feedback.jsonl   — phản hồi 👍/👎 (q đã redact, rating = 'up' | 'down')

In ra:
  - tổng truy vấn, tỷ lệ TỪ CHỐI (refused) + chia theo lý do (ngưỡng/PII/khác)
  - TOP câu bị từ chối nhiều nhất  -> điểm mù tài liệu (cần bổ sung help/đặt lại câu)
  - tỷ lệ 👎 (và 👍/👎 tuyệt đối) -> chất lượng cảm nhận
  - phân bố theo ROUTE (cloud/self_host) và theo PROVIDER/model

Mục đích seminar: chứng minh hệ có VÒNG PHẢN HỒI đo được (rào chắn hoạt động bao nhiêu, người
dùng hài lòng đến đâu, tài liệu hổng ở đâu) — KHÔNG suy diễn nội dung, chỉ thống kê log.

Chạy:  python analytics.py            # đọc data/audit_log.jsonl + data/feedback.jsonl
       python analytics.py --top 15   # số dòng tối đa cho mỗi bảng top (mặc định 10)
"""
import json
import sys
from collections import Counter

import config

# Console Windows mặc định cp1252 -> vỡ khi in tiếng Việt. Ép stdout sang UTF-8 (an toàn, no-op nếu đã UTF-8).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _read_jsonl(path):
    """Đọc JSONL khoan dung lỗi (bỏ qua dòng hỏng) — log có thể bị cắt giữa chừng."""
    rows = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _bar(n, total, width=24):
    """Thanh tỷ lệ ASCII đơn giản cho dễ đọc trên terminal."""
    if total <= 0:
        return ""
    filled = int(round(width * n / total))
    return "█" * filled + "·" * (width - filled)


def _pct(n, total):
    return f"{(100 * n / total):.1f}%" if total else "0.0%"


def _refuse_reason(rec):
    """Phân loại lý do từ chối từ một bản ghi audit (chỉ áp dụng khi refused=True)."""
    if rec.get("blocked") == "pii" or rec.get("pii"):
        return "pii"
    if rec.get("blocked"):
        return str(rec.get("blocked"))
    return "duoi_nguong"   # qua rào chắn (2) hoặc soft-refusal: ngữ cảnh không đủ


def main():
    top_n = 10
    if "--top" in sys.argv:
        top_n = int(sys.argv[sys.argv.index("--top") + 1])

    audit = _read_jsonl(config.AUDIT_LOG)
    feedback = _read_jsonl(config.DATA_DIR / "feedback.jsonl")

    print("================ BÁO CÁO COVERAGE (offline, không gọi LLM) ================")
    print(f"audit_log : {config.AUDIT_LOG}")
    print(f"feedback  : {config.DATA_DIR / 'feedback.jsonl'}\n")

    total = len(audit)
    if total == 0:
        print("Chưa có truy vấn nào trong audit_log.jsonl. Hãy chạy app/eval để sinh log trước.")
        return

    # --- Tổng quan + tỷ lệ từ chối ---
    refused = [r for r in audit if r.get("refused")]
    print(f"Tổng truy vấn       : {total}")
    print(f"Bị từ chối (refused): {len(refused)}  ({_pct(len(refused), total)})  {_bar(len(refused), total)}")
    print(f"Trả lời được        : {total - len(refused)}  ({_pct(total - len(refused), total)})\n")

    # --- Phân loại lý do từ chối ---
    if refused:
        reasons = Counter(_refuse_reason(r) for r in refused)
        label = {"pii": "chặn PII (trước khi ra cloud)",
                 "duoi_nguong": "dưới ngưỡng / ngữ cảnh không đủ"}
        print("Lý do từ chối:")
        for reason, n in reasons.most_common():
            print(f"  - {label.get(reason, reason):<38} {n:>3}  ({_pct(n, len(refused))})")
        print()

    # --- Top câu bị từ chối (điểm mù tài liệu) ---
    if refused:
        qcount = Counter((r.get("q") or "").strip() for r in refused if (r.get("q") or "").strip())
        print(f"TOP câu bị từ chối (điểm mù tài liệu / cần bổ sung) — tối đa {top_n}:")
        for q, n in qcount.most_common(top_n):
            suffix = f"  (x{n})" if n > 1 else ""
            print(f"  - {q[:84]}{suffix}")
        print()

    # --- Phản hồi 👍/👎 ---
    ratings = Counter((r.get("rating") or "").lower() for r in feedback)
    up, down = ratings.get("up", 0), ratings.get("down", 0)
    fb_total = up + down
    print("Phản hồi người dùng:")
    if fb_total == 0:
        print("  (chưa có feedback 👍/👎 nào trong feedback.jsonl)\n")
    else:
        print(f"  👍 {up}   👎 {down}   (tổng {fb_total})")
        print(f"  Tỷ lệ 👎: {_pct(down, fb_total)}   {_bar(down, fb_total)}\n")

    # --- Phân bố theo route ---
    routes = Counter(r.get("route") or "?" for r in audit)
    print("Phân bố theo ROUTE (chủ quyền dữ liệu):")
    for route, n in routes.most_common():
        print(f"  - {route:<12} {n:>4}  ({_pct(n, total)})  {_bar(n, total)}")
    print()

    # --- Phân bố theo provider/model ---
    provs = Counter(f"{r.get('provider', '?')}/{r.get('model', '?')}" for r in audit)
    print("Phân bố theo PROVIDER/model:")
    for pm, n in provs.most_common():
        print(f"  - {pm:<32} {n:>4}  ({_pct(n, total)})")


if __name__ == "__main__":
    main()
