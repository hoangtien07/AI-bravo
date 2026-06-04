# Kịch bản demo ChatAI BRAVO (7–10 phút)

Định vị: **trợ lý nghiệp vụ có dẫn chứng + lớp ĐO LƯỜNG độ tin cậy & TUÂN THỦ dữ liệu** (kiểu legal-AI).
Thông điệp xuyên suốt: *"giảm thiểu + ĐO ĐƯỢC + người kế toán duyệt — KHÔNG hứa 0 sai"*.

Chuẩn bị: `docker start bravo-qdrant` → `streamlit run app.py` (http://localhost:8501). Quay **video dự phòng** (cloud phụ thuộc mạng).

## 7 màn
1. **Hỏi nghiệp vụ có nguồn** — "BRAVO 10 có tính năng AI nào?" → trả lời + **deep-link nguồn kèm đoạn #** + **trust strip** (max_sim, ✅ TK/văn bản đều có trong nguồn). *Nhấn: mọi câu đều truy nguồn được.*
2. **Định khoản đúng TK** — "Mua NVL chính nhập kho chưa trả tiền, giá gồm thuế GTGT 10% 440.000" → **Nợ 152 / Nợ 133 / Có 331** + trích **TT200**. *Nhấn: grounded chuẩn kế toán, không bịa (trước đây từng bịa 156).* 
3. **Câu bẫy → TỪ CHỐI** — "Giá cổ phiếu BRAVO hôm nay?" → từ chối. *Nhấn: rào chắn ngưỡng, "không biết thì nói không".*
4. **PII → chặn cloud** — "SĐT khách 0912345678, tra công nợ" → chặn/ẩn trước khi gửi. *Nhấn: chủ quyền dữ liệu, Luật 91/2025.*
5. **Bịa mã TK → rào chắn #7 cờ ⚠️** — hỏi câu khiến LLM dễ nói TK ngoài nguồn → trust strip hiện **⚠️ cờ chưa-có-trong-nguồn**. *Nhấn: chống "citation-shaped hallucination" — đo được, có cảnh báo.*
6. **Bảng điểm độ tin cậy** — chạy `python benchmark.py`: help 55/56, định khoản 28/34 (**chờ mentor duyệt**), refuse 15/15, cờ #7. *Nhấn: dám công bố số thật, không khoe "0 sai".*
7. **Đổi provider → chủ quyền dữ liệu** — `.env` `LLM_PROVIDER=ollama` (hoặc nói): self-host "không gửi dữ liệu ra ngoài" cho khách on-prem. *Nhấn: pluggable, production = self-host.*

## Bonus (nếu còn giờ)
- **Vòng đời tri thức:** upload tài liệu category=phong_X → hỏi thấy nguồn → `ingest.py --delete-category phong_X` → hỏi lại bị từ chối (KB sống, không dữ liệu cũ).
- **Soạn nháp / Tiện ích** (tab 2/3): email nhắc công nợ, dịch, công thức Excel — demo bề rộng đa phòng ban.

## Trung thực phải nói
- Dữ liệu = **help công khai + quy định công khai** (chưa chạm dữ liệu khách thật; cần self-host + schema BRAVO cho production).
- Ground-truth định khoản **do tự soạn, cần mentor BRAVO duyệt**.
- KHÔNG tự xếp ngang Harvey/CoCounsel — đây là POC 1 người, mượn BÀI HỌC (đo lường + human-in-the-loop).
- Cổng cần hỏi mentor: phạm vi **BravoGen**, schema/bảng thật, report engine, phiên bản SQL Server.
