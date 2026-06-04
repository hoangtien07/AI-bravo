"""
memory.py — Hội thoại đa lượt: VIẾT LẠI câu hỏi follow-up thành câu ĐỘC LẬP (condense)
ở LỚP GỌI (app.py / api.py). KHÔNG đụng rag.ask — grounding vẫn chỉ từ ngữ cảnh truy hồi.

Vì sao ở lớp gọi: giữ rag.ask/retrieve bất biến -> eval (không history) KHÔNG đổi điểm.
An toàn: PII pre-check trên TOÀN lịch sử trước khi gửi ra cloud (history lượt trước có thể
chứa PII mà rag.pii_findings hiện chỉ soi câu hỏi đơn).
"""
import config
import provider
import rag

_CONDENSE_SYS = (
    "Bạn viết lại CÂU HỎI MỚI của người dùng thành MỘT câu hỏi ĐỘC LẬP, đầy đủ ngữ cảnh, "
    "dựa trên LỊCH SỬ hội thoại: thay các tham chiếu/đại từ ('nó', 'cái đó', 'vậy còn', "
    "'bút toán đó'...) bằng danh từ/cụm cụ thể từ lịch sử. "
    "CHỈ trả về câu hỏi đã viết lại trên MỘT dòng, không giải thích, không thêm gì. "
    "Nếu câu mới đã độc lập, trả nguyên văn câu đó."
)

MAX_TURNS = 4   # chỉ lấy vài lượt gần nhất để condense (đủ ngữ cảnh, gọn token)


def condense_question(history, question):
    """history: list[{'role','content'}] các lượt TRƯỚC câu hiện tại. Trả câu hỏi độc lập (str).

    Trả NGUYÊN câu hỏi (không condense) khi: không có lịch sử · lịch sử+câu chứa PII và đang
    dùng cloud (tránh rò PII lượt trước ra ngoài) · lỗi gọi LLM. An toàn > tiện lợi."""
    turns = [m for m in (history or []) if m.get("role") in ("user", "assistant")][-MAX_TURNS:]
    if not turns:
        return question
    convo = "\n".join(
        f"{'Người dùng' if m['role'] == 'user' else 'Trợ lý'}: {m['content']}" for m in turns)

    # Rào chắn (5) mở rộng: không gửi lịch sử chứa PII ra cloud để condense.
    if provider.is_cloud() and rag.pii_findings(convo + "\n" + question):
        return question

    try:
        out = rag._strip_think(provider.chat(
            _CONDENSE_SYS, f"LỊCH SỬ:\n{convo}\n\nCÂU HỎI MỚI: {question}"))
        out = (out or "").strip().strip('"').strip("“”").splitlines()
        out = out[0].strip() if out else ""
        return out or question
    except Exception:
        return question
