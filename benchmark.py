"""
benchmark.py — Bảng điểm ĐỘ TIN CẬY trung thực cho slide/demo.

Đọc data/eval_results.json (do eval.py / eval.py --accounting ghi) + data/audit_log.jsonl
-> render 1 bảng. KHÔNG gọi LLM (an toàn khi demo, không tốn token, không phụ thuộc mạng).

Mọi số kèm ĐIỀU KIỆN (model, ngày, store, commit, ngưỡng) — KHÔNG công bố như hằng số tuyệt đối.
Tinh thần legal-AI: "giảm thiểu + ĐO ĐƯỢC + người duyệt", KHÔNG hứa 0 sai.

Chạy:  python benchmark.py   (sau khi đã chạy eval.py + eval.py --accounting)
"""
import json
import subprocess
import sys

import config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=str(config.BASE_DIR), text=True).strip()
    except Exception:
        return "?"


def _audit_stats():
    f = config.AUDIT_LOG
    if not f.exists():
        return None
    n = refused = pii = ung = 0
    for line in open(f, encoding="utf-8"):
        try:
            o = json.loads(line)
        except Exception:
            continue
        n += 1
        refused += int(bool(o.get("refused")))
        pii += int(o.get("blocked") == "pii")
        ung += len(o.get("ungrounded_tk") or [])
    return {"queries": n, "refused": refused, "pii_blocked": pii, "guardrail7_flags": ung}


def main():
    f = config.DATA_DIR / "eval_results.json"
    if not f.exists():
        print("[!] Chưa có data/eval_results.json. Chạy: python eval.py && python eval.py --accounting")
        sys.exit(1)
    r = json.loads(f.read_text(encoding="utf-8"))
    commit = _git_commit()

    print("=" * 64)
    print(" BẢNG ĐIỂM ĐỘ TIN CẬY — ChatAI BRAVO")
    print(f" commit {commit} · store={config.VECTOR_STORE} · {config.LLM_PROVIDER}/{config.LLM_MODEL}")
    print("=" * 64)

    h = r.get("help")
    if h:
        print(f"\n[1] HỎI-ĐÁP HELP (grounded)   — đo {h['ts']}")
        print(f"    answer  : {h['answer_pass']}/{h['answer_total']} pass"
              f" · keyword coverage TB {h.get('kw_coverage')}")
        print(f"    refuse  : {h['refuse_pass']}/{h['refuse_total']} pass (rào chắn chống bịa/PII)")
        print(f"    (điều kiện: kw_min={h.get('kw_min')}, {h['provider']}, store={h['store']})")

    a = r.get("accounting")
    if a:
        print(f"\n[2] ĐỊNH KHOẢN (exact-match TK) — đo {a['ts']}")
        print(f"    {a['pass']}/{a['total']} pass · rào chắn #7 cờ {a.get('guardrail7_flags')} mã ungrounded")
        print(f"    ⚠️ {a.get('note')}")

    s = _audit_stats()
    if s and s["queries"]:
        print(f"\n[3] VẬN HÀNH (từ audit_log, {s['queries']} truy vấn)")
        print(f"    từ chối: {s['refused']} · chặn PII: {s['pii_blocked']} · cờ #7: {s['guardrail7_flags']}")

    print("\n" + "-" * 64)
    print("LƯU Ý TRUNG THỰC: KHÔNG hứa '0 sai'. RAG pháp lý hàng đầu (Lexis/Westlaw)")
    print("vẫn ảo giác 17–33% (Stanford JELS 2025). Đây là hệ THAM CHIẾU có dẫn nguồn")
    print("+ cờ cảnh báo; mọi định khoản PHẢI người kế toán duyệt. Ground-truth chờ mentor.")
    print("-" * 64)


if __name__ == "__main__":
    main()
