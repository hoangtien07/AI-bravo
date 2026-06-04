"""
generate.py — Trợ lý SINH NỘI DUNG đa tác vụ (không chạm dữ liệu nghiệp vụ BRAVO).

Phủ các tính năng AN TOÀN (chạy cloud được) cho nhiều phòng ban — input là VĂN BẢN
NGƯỜI DÙNG TỰ NHẬP, KHÔNG kết nối DB/dữ liệu tài chính khách:
  soan_email · jd · call_script · interview · content · idea      (sinh nháp)
  tom_tat · dich · grammar · excel                                  (tiện ích)

An toàn dữ liệu (nhất quán với rag.ask):
- PII pre-check: nếu input chứa PII (SĐT/email/MST/CCCD) VÀ provider là cloud -> REDACT
  thành placeholder ([PHONE]/[EMAIL]/...) TRƯỚC khi gửi. Output thành "khung điền sẵn":
  AI viết khung, con người điền số/tên thật ở máy mình. Không gửi PII ra cloud.
- Mọi đầu ra là BẢN NHÁP để người duyệt; KHÔNG phải số liệu/định khoản chính thức.

Tái dùng provider gateway + helper của rag (không sửa rag.py).
"""
import sys

import config
import provider
import rag

# Mỗi tác vụ = (nhãn hiển thị, system prompt). System prompt buộc: chỉ dựa trên input người
# dùng, không bịa số/dữ kiện, trả lời tiếng Việt, đóng vai trợ lý nghiệp vụ.
_BASE = ("Bạn là trợ lý nghiệp vụ cho người dùng phần mềm BRAVO (ERP Việt Nam). "
         "CHỈ dùng thông tin trong yêu cầu của người dùng; KHÔNG bịa số liệu, tên riêng, "
         "hay dữ kiện không được cung cấp — nếu thiếu thì để chỗ trống dạng [ ... ] để người "
         "dùng tự điền. Trả lời bằng tiếng Việt, rõ ràng, đúng văn phong công sở. "
         "Đây là BẢN NHÁP để con người kiểm tra và phê duyệt.")

TASKS = {
    "soan_email": ("Soạn email", _BASE +
        " Hãy soạn một EMAIL công việc hoàn chỉnh (tiêu đề + thân + chào kết) theo yêu cầu. "
        "Lịch sự, súc tích, đúng mục đích (vd nhắc công nợ, giải trình, thông báo, mời họp)."),
    "jd": ("Viết JD tuyển dụng", _BASE +
        " Hãy viết một BẢN MÔ TẢ CÔNG VIỆC (JD) gồm: chức danh, mục tiêu, trách nhiệm chính, "
        "yêu cầu, quyền lợi. Bám đúng vị trí người dùng nêu."),
    "call_script": ("Kịch bản gọi điện", _BASE +
        " Hãy viết KỊCH BẢN GỌI ĐIỆN/telesales: mở đầu, khai thác nhu cầu, xử lý từ chối, chốt. "
        "Tự nhiên, không sáo rỗng."),
    "interview": ("Bộ câu hỏi phỏng vấn", _BASE +
        " Hãy soạn BỘ CÂU HỎI PHỎNG VẤN cho vị trí người dùng nêu: nhóm chuyên môn, nhóm hành vi, "
        "kèm gợi ý điều cần đánh giá ở mỗi câu."),
    "content": ("Dàn ý nội dung/SEO", _BASE +
        " Hãy lập DÀN Ý NỘI DUNG (bài viết/bài đăng) theo chủ đề: tiêu đề gợi ý, các mục chính, "
        "ý chính mỗi mục, và 3-5 từ khoá SEO liên quan."),
    "idea": ("Gợi ý ý tưởng", _BASE +
        " Hãy đề xuất 5-8 Ý TƯỞNG khả thi cho vấn đề người dùng nêu, mỗi ý 1-2 câu, đa dạng góc nhìn."),
    "tom_tat": ("Tóm tắt văn bản", _BASE +
        " Hãy TÓM TẮT văn bản người dùng dán: gạch đầu dòng các ý chính + (nếu có) hành động/quyết định. "
        "TUYỆT ĐỐI không thêm thông tin ngoài văn bản."),
    "dich": ("Dịch", _BASE +
        " Hãy DỊCH văn bản người dùng sang ngôn ngữ họ yêu cầu (mặc định: Việt<->Anh tuỳ nội dung), "
        "giữ nguyên thuật ngữ nghiệp vụ, không diễn giải thêm."),
    "grammar": ("Soát chính tả/văn phong", _BASE +
        " Hãy SOÁT và SỬA chính tả/ngữ pháp/văn phong cho văn bản; trả về (1) bản đã sửa, "
        "(2) liệt kê ngắn các lỗi đã sửa. Không đổi ý nghĩa."),
    "excel": ("Trợ lý công thức Excel", _BASE +
        " Người dùng mô tả nhu cầu tính toán trong Excel/Google Sheets. Hãy đưa CÔNG THỨC phù hợp "
        "(vd SUMIF/VLOOKUP/INDEX-MATCH...), giải thích ngắn từng phần, và lưu ý ô/điều kiện cần thay. "
        "KHÔNG tự tính ra con số — chỉ cung cấp công thức để người dùng áp dụng."),
}


def generate(task: str, user_input: str):
    """Sinh nội dung cho 1 tác vụ. Trả dict {task, output, redacted(bool), pii(list), route}.

    redacted=True nghĩa là input đã bị thay PII bằng placeholder trước khi gửi cloud
    (output sẽ chứa [PHONE]/[EMAIL]/... để người dùng tự điền lại ở máy mình)."""
    if task not in TASKS:
        raise ValueError(f"Tác vụ không hỗ trợ: {task}. Có: {', '.join(TASKS)}")
    label, system = TASKS[task]
    route = provider.route_label()

    text = (user_input or "").strip()
    if not text:
        return {"task": task, "label": label, "output": "(Chưa có nội dung đầu vào.)",
                "redacted": False, "pii": [], "route": route}

    # Rào chắn PII: nếu cloud + có PII -> redact thành placeholder trước khi gửi ra ngoài.
    pii = rag.pii_findings(text)
    redacted = False
    if pii and provider.is_cloud():
        text = rag._redact(text)
        redacted = True

    try:
        out = rag._strip_think(provider.chat(system, text))
    except Exception as e:
        return {"task": task, "label": label,
                "output": f"[Lỗi gọi LLM {config.LLM_PROVIDER}/{config.LLM_MODEL}] {e}. "
                          f"Kiểm tra API key (.env).",
                "redacted": redacted, "pii": pii, "route": route, "error": True}

    return {"task": task, "label": label, "output": out,
            "redacted": redacted, "pii": pii, "route": route}


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "soan_email"
    user_input = " ".join(sys.argv[2:]) or "nhắc công nợ quá hạn cho khách hàng, giọng lịch sự"
    r = generate(task, user_input)
    print(f"[{r['label']} · provider={config.LLM_PROVIDER}/{config.LLM_MODEL} · route={r['route']}]")
    if r.get("redacted"):
        print(f"⚠️ Đã ẩn PII trong input ({', '.join(r['pii'])}) trước khi gửi cloud — "
              f"output dùng placeholder, anh/chị tự điền lại.")
    print("\n" + r["output"])
