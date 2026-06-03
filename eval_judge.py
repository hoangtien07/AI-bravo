"""
eval_judge.py — LLM-as-judge: chấm CHẤT LƯỢNG NỘI DUNG ngoài keyword coverage.

Hai chỉ số (chấm trên các câu expect=answer trong eval_questions.yaml):
  - faithfulness     : câu trả lời CÓ ĐƯỢC ngữ cảnh truy hồi hỗ trợ không (chống bịa/ảo giác).
                       Chỉ chấm trên ngữ cảnh thật sự đưa cho LLM (hits), KHÔNG dựa kiến thức ngoài.
  - answer_relevancy : câu trả lời CÓ bám đúng câu hỏi không (đúng trọng tâm, không lạc đề).

Khác eval.py: eval.py đo keyword coverage (nhị phân/đếm từ) + rào chắn refuse — RẺ, KHÔNG gọi
LLM-judge. File này gọi LLM thêm một lần/câu để CHẤM -> TỐN TOKEN -> mặc định --limit 10.

Tái dùng provider.chat (cùng gateway/cùng provider với rag) -> KHÔNG thêm dependency, KHÔNG đổi
ngữ nghĩa rag.ask (chỉ đọc kết quả rag.ask rồi chấm).

Chạy:  python eval_judge.py              # chấm 10 câu answer đầu (tiết kiệm token)
       python eval_judge.py --limit 20  # chấm 20 câu
       python eval_judge.py --limit 0   # chấm TẤT CẢ câu answer (tốn token nhất)

LƯU Ý: judge dùng chính LLM cloud -> cùng giới hạn chủ quyền dữ liệu; chỉ chạy trên dữ liệu
CÔNG KHAI (corpus help). Điểm judge mang tính tham khảo, cần MENTOR đối chiếu.
"""
import json
import re
import sys
from datetime import datetime

import yaml

import config
import provider
import rag

# Console Windows mặc định cp1252 -> vỡ khi in tiếng Việt. Ép stdout sang UTF-8 (an toàn, no-op nếu đã UTF-8).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Prompt judge: buộc trả JSON gọn để parse ổn định; thang 1..5 cho dễ diễn giải.
JUDGE_SYSTEM = (
    "Bạn là giám khảo đánh giá chất lượng câu trả lời của một trợ lý RAG. "
    "Chấm KHÁCH QUAN, NGHIÊM KHẮC, chỉ dựa trên dữ liệu được cung cấp. "
    "Chỉ trả về JSON đúng định dạng yêu cầu, KHÔNG thêm lời dẫn, KHÔNG markdown."
)

# Hai tiêu chí gộp một lần gọi/câu để tiết kiệm token.
JUDGE_TEMPLATE = (
    "Hãy chấm hai tiêu chí cho cặp (câu hỏi, câu trả lời) dưới đây.\n\n"
    "1) faithfulness (1-5): câu TRẢ LỜI có được NGỮ CẢNH hỗ trợ không? "
    "5 = mọi ý đều có trong ngữ cảnh; 1 = bịa/mâu thuẫn ngữ cảnh. "
    "CHỈ xét ngữ cảnh, BỎ QUA kiến thức ngoài.\n"
    "2) answer_relevancy (1-5): câu TRẢ LỜI có bám đúng CÂU HỎI không? "
    "5 = trả lời trúng trọng tâm; 1 = lạc đề/không trả lời điều được hỏi.\n\n"
    "Trả về DUY NHẤT JSON: "
    '{{"faithfulness": <1-5>, "answer_relevancy": <1-5>, "reason": "<ngắn gọn tiếng Việt>"}}\n\n'
    "=== NGỮ CẢNH ===\n{context}\n\n"
    "=== CÂU HỎI ===\n{question}\n\n"
    "=== CÂU TRẢ LỜI ===\n{answer}\n"
)


def _parse_score(raw: str):
    """Bóc JSON {faithfulness, answer_relevancy, reason} từ output judge (bền với rào markdown)."""
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None

    def _clip(v):
        try:
            return max(1, min(5, int(round(float(v)))))
        except Exception:
            return None

    f = _clip(obj.get("faithfulness"))
    a = _clip(obj.get("answer_relevancy"))
    if f is None or a is None:
        return None
    return {"faithfulness": f, "answer_relevancy": a, "reason": (obj.get("reason") or "")[:160]}


def _context_from_hits(hits):
    """Dựng lại ngữ cảnh từ hits của rag.ask (đúng phần LLM đã thấy) để chấm faithfulness."""
    parts = []
    for n, h in enumerate(hits or [], 1):
        parts.append(f"[Đoạn {n} | nguồn: {h.get('source', '?')}]\n{h.get('text', '')}")
    return "\n\n".join(parts) if parts else "(không có ngữ cảnh)"


def main():
    limit = 10
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])  # 0 = tất cả

    data = yaml.safe_load(open("eval_questions.yaml", encoding="utf-8"))
    cases = data["questions"] if isinstance(data, dict) else data
    answer_cases = [c for c in cases if c.get("expect") == "answer"]
    if limit > 0:
        answer_cases = answer_cases[:limit]

    print(f"LLM-as-judge · provider {config.LLM_PROVIDER}/{config.LLM_MODEL} · "
          f"chấm {len(answer_cases)} câu (expect=answer) · {datetime.now().isoformat(timespec='seconds')}\n")

    sum_f = sum_a = scored = 0
    skipped = 0
    for c in answer_cases:
        r = rag.ask(c["q"])
        # Câu bị từ chối / lỗi: judge không áp dụng (không có câu trả lời nội dung để chấm).
        if r.get("refused") or r.get("error") or not r.get("hits"):
            skipped += 1
            print(f"[SKIP] (từ chối/không hits) {c['q'][:64]}")
            continue

        ctx = _context_from_hits(r["hits"])
        prompt = JUDGE_TEMPLATE.format(context=ctx, question=c["q"], answer=r["answer"])
        try:
            raw = provider.chat(JUDGE_SYSTEM, prompt)
        except Exception as e:
            skipped += 1
            print(f"[SKIP] (lỗi judge: {str(e)[:60]}) {c['q'][:50]}")
            continue

        sc = _parse_score(raw)
        if sc is None:
            skipped += 1
            print(f"[SKIP] (judge trả không đúng JSON) {c['q'][:50]}")
            continue

        sum_f += sc["faithfulness"]; sum_a += sc["answer_relevancy"]; scored += 1
        print(f"[faith={sc['faithfulness']} rel={sc['answer_relevancy']}] {c['q'][:56]}")
        if sc["reason"]:
            print(f"        -> {sc['reason']}")

    print("\n================ KẾT QUẢ JUDGE ================")
    if scored:
        print(f"faithfulness     TB: {sum_f / scored:.2f}/5  ({scored} câu)")
        print(f"answer_relevancy TB: {sum_a / scored:.2f}/5  ({scored} câu)")
    else:
        print("Không có câu nào được chấm (đều bị skip).")
    if skipped:
        print(f"bỏ qua: {skipped} câu (từ chối/lỗi/parse).")
    print(f"model judge: {config.LLM_PROVIDER}/{config.LLM_MODEL} · "
          f"{datetime.now().isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
