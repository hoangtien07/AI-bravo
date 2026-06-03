"""
eval.py — Chạy bộ câu hỏi đánh giá, kiểm rào chắn + ĐỘ CHÍNH XÁC NỘI DUNG.

  - expect=answer : kỳ vọng trả lời được (không từ chối + CÓ nguồn) VÀ — nếu có expect_keywords —
                    câu trả lời phải chứa đủ tỷ lệ từ khoá bắt buộc (kiểm nội dung, không chỉ nhị phân).
  - expect=refuse : câu BẪY/ngoài tài liệu/PII, kỳ vọng TỪ CHỐI hoặc bị chặn (bằng chứng rào chắn).

Định dạng eval_questions.yaml: {questions: [ {q, expect, expect_keywords?, refuse_type?, ...} ]}
(hoặc danh sách phẳng — vẫn đọc được).

Chạy:  python eval.py            # cần đã ingest + provider sẵn sàng (Ollama hoặc API key)
       python eval.py --kw 0.5   # đổi tỷ lệ keyword tối thiểu để coi là PASS nội dung (mặc định 0.5)
Lưu ý: bộ câu cần MENTOR DUYỆT đáp án (người soạn đang học ERP).
"""
import sys
import unicodedata

import yaml

import config
import rag


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").lower())


def _kw_coverage(answer: str, keywords):
    if not keywords:
        return None
    a = _norm(answer)
    hit = sum(1 for kw in keywords if _norm(kw) in a)
    return hit / len(keywords)


def main():
    kw_min = 0.5
    if "--kw" in sys.argv:
        kw_min = float(sys.argv[sys.argv.index("--kw") + 1])

    data = yaml.safe_load(open("eval_questions.yaml", encoding="utf-8"))
    cases = data["questions"] if isinstance(data, dict) else data

    print(f"Provider: {config.LLM_PROVIDER}/{config.LLM_MODEL} · embed {config.EMBED_PROVIDER}/"
          f"{config.EMBED_MODEL} · {len(cases)} câu · keyword_min={kw_min}\n")

    n_ans = n_ref = ok_ans = ok_ref = 0
    cov_total, cov_count = 0.0, 0
    for c in cases:
        r = rag.ask(c["q"])
        if c["expect"] == "refuse":
            n_ref += 1
            ok = bool(r.get("refused"))
            ok_ref += int(ok)
            tag = c.get("refuse_type", "")
            print(f"[{'PASS' if ok else 'FAIL'}] (refuse/{tag:<12}) {c['q'][:64]}")
            if not ok:
                print(f"        -> KHÔNG từ chối: {r['answer'][:80]}")
        else:
            n_ans += 1
            answered = (not r.get("refused")) and bool(r.get("sources"))
            cov = _kw_coverage(r.get("answer", ""), c.get("expect_keywords"))
            content_ok = True if cov is None else (cov >= kw_min)
            if cov is not None:
                cov_total += cov; cov_count += 1
            ok = answered and content_ok
            ok_ans += int(ok)
            covtxt = "n/a" if cov is None else f"{cov:.0%}"
            print(f"[{'PASS' if ok else 'FAIL'}] (answer kw={covtxt:>4}) {c['q'][:60]}")
            if not ok:
                why = "bị từ chối/không nguồn" if not answered else f"thiếu keyword (cov={covtxt})"
                print(f"        -> {why}; đáp: {r['answer'][:80]}")

    print("\n================ KẾT QUẢ ================")
    print(f"answer : {ok_ans}/{n_ans} pass" + (
        f" · keyword coverage TB {cov_total / cov_count:.0%}" if cov_count else ""))
    print(f"refuse : {ok_ref}/{n_ref} pass (rào chắn chống bịa/PII)")
    print(f"TỔNG   : {ok_ans + ok_ref}/{n_ans + n_ref} pass")


if __name__ == "__main__":
    main()
