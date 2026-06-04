# CLAUDE.md — Sổ tay dự án cho Claude

> Đọc file này đầu mỗi session khi làm việc trong `D:\Tien\bravo`. Ngữ cảnh sâu hơn: [docs/seminar-context.md](./docs/seminar-context.md).

## 1. Dự án là gì

POC cho **bài seminar cuối khóa thử việc** của Tien tại **Công ty CP Phần mềm BRAVO** (vị trí Kỹ thuật triển khai ERP). Chủ đề: *"Tích hợp AI vào phần mềm/hệ sinh thái BRAVO"*. Trình bày trước hội đồng = đội triển khai + lãnh đạo/chuyên gia BRAVO lâu năm. Deadline: **~1 tháng kể từ 2026-06-03**.

Đây **không** liên quan repo 3DWebView (chỉ chung máy). Nền tảng Tien: lập trình web ~1 năm, SQL cơ bản, đang học sản phẩm BRAVO + kế toán.

## 2. Flagship đã chốt

**B1 — Trợ lý nghiệp vụ BRAVO: RAG có dẫn chứng trên tài liệu help, self-host, phục vụ đội triển khai.**

Đã cân nhắc và **không chọn** A1 (Text-to-SQL hỏi vào dữ liệu) vì: rủi ro dữ liệu cao (chạm sổ kế toán có PII → vướng Luật 91/2025 + Nghị định 356/2025), độ chính xác Text-to-SQL ~52% (BIRD), tụt ~6% trên schema thật (Spider 2.0). A1 để bước "walk" trong lộ trình. **Mặc định KHÔNG ghép ý tưởng** — giữ scope thử việc.

Đã loại ý tưởng **browser extension scrape** (anti-pattern "chọc UI", rủi ro bảo mật).

## 3. Thesis đã tinh chỉnh (QUAN TRỌNG — không nói sai)

KHÔNG được nói "BRAVO không có phân tích dữ liệu / BRAVO lạc hậu". Sự thật:
- BRAVO **đã có** BI Dashboard (lớp mô tả/chẩn đoán: Waterfall/Tornado/TreeMap, phân quyền dữ liệu).
- BRAVO 10 **đã có** AI OCR (trích xuất CV), cảnh báo biến động bất thường, và lab nội bộ **BravoGen** (Knowledge Graph…).
- **Gap thật** = lớp **dự báo (predictive) + đề xuất (prescriptive) + hội thoại/tạo sinh có dẫn chứng (generative)**. Định vị = **cơ hội bắt kịp**, giọng xây dựng.

## 4. Kiến trúc POC + cách chạy

**Đã pivot cloud-first PLUGGABLE** (self-host không còn là mặc định). Luồng thực tế:
`Câu hỏi → [rào chắn PII] → embed (provider) → store (numpy|chroma|qdrant) + hybrid BM25+vector+RRF → lọc ngưỡng cosine → LLM (provider) → trả lời + deep-link citation → [hậu kiểm số/TK] → audit log`.
- **Provider pluggable** (`provider.py`): `openai` (mặc định) | `gemini` | `ollama` — đổi bằng `.env`.
- **Store pluggable** (`store.py`): `numpy` (đang chạy máy này) | `chroma` | **`qdrant`** (Docker, hướng production). chromadb 1.x segfault Windows → numpy fallback.
- **7 rào chắn** (KHÔNG phải 4): grounding · ngưỡng cosine từ chối · citation · audit · PII pre-check · anti prompt-injection · **number/TK-grounding hậu kiểm** (`rag._ungrounded_tk`).
- **Định vị (đã chốt):** xương sống ĐO LƯỜNG độ tin cậy + TUÂN THỦ/chủ quyền dữ liệu (kiểu legal-AI) + demo rộng theo phòng ban. **KHÔNG hứa "0 sai"** (RAG pháp lý top vẫn ảo 17–33%) — đóng khung "giảm thiểu + đo được + người kế toán duyệt". BravoGen overlap không còn là lo ngại.

```bash
py -3.12 -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt
cp .env.example .env          # điền OPENAI_API_KEY (hoặc GEMINI_API_KEY); hoặc provider=ollama
python ingest.py --reset      # nạp help + KB quy định (~1622 chunk)
python eval.py                # help 56 câu (~55/56)
python eval.py --accounting   # định khoản 34 case (exact-match TK; ~28/34 — CHỜ MENTOR DUYỆT)
streamlit run app.py          # UI demo (3 tab)
```

File chính: `config.py` · `provider.py` · `store.py` (+Qdrant) · `ingest.py` (chunk + version/category metadata) · `rag.py` (lõi + 7 rào chắn + hybrid) · `generate.py` (sinh nội dung) · `app.py` · `api.py` (FastAPI) · `eval.py` (+`--accounting`) · `eval_questions.yaml` / `data/eval_accounting.yaml` · `data/regulations/` (KB TT200/TT99) · `crawl_bravo10_help.py`. Dữ liệu: 651 trang help + KB quy định.

## 5. Quy ước

- **Ngôn ngữ**: tiếng Việt cho thảo luận + UI + nội dung seminar. Tiếng Anh cho code identifier/commit. Giữ tiếng Anh cho thuật ngữ kỹ thuật.
- **Dữ liệu**: CHỈ dùng tài liệu **công khai (bravo.com.vn)** hoặc **giả lập minh hoạ** có nhãn rõ. **TUYỆT ĐỐI không** demo trên dữ liệu kế toán thật, không gửi dữ liệu khách ra LLM nước ngoài.
- **Schema/tài liệu**: nếu chưa verify được, ghi rõ là **MINH HOẠ**, gắn `[cần verify]` — hội đồng là kỹ sư BRAVO biết schema thật, bịa sai phản tác dụng nặng.
- **Thuật ngữ nghiệp vụ VN dùng đúng**: phân hệ, chứng từ, định khoản, công nợ, giá thành, giá vốn bình quân gia quyền, CĐKT, KQHĐKD, TK 131/331/632/214…, TT200, TT99/2025.
- **Python**: máy có 3.14 nhưng dùng **venv 3.12** cho chromadb/lxml.

## 6. Ràng buộc cứng (mọi đề xuất)

1. **Khả thi trên stack BRAVO**: AI là lớp-ngoài read-only hoặc tool nội bộ; giả định BRAVO không có public write-API → ghi ngược qua template import Excel.
2. **Bảo mật/chủ quyền dữ liệu VN**: ưu tiên self-host; production dùng model 14B–32B Q4 hoặc SQL Server 2025 native vector; multi-tenant isolation là regression-critical.
3. **Độ chính xác kế toán = không chấp nhận sai số**: AI chỉ tra cứu, không tự ghi sổ; phải grounding + citation + human-in-the-loop.
4. **Scope thử việc**: T-shaped, 1 flagship sâu + POC chạy được; framing "đề xuất nghiên cứu/POC", "theo tìm hiểu của em".
5. **Trung thực**: số liệu vendor gắn "theo công bố"; ROI gắn `[ước lượng, cần kiểm chứng]` — **không bịa ROI**; honest cost (token cloud + GPU self-host + năng lực đội).

## 7. Sự thật đã kiểm chứng (dùng để phản biện có dẫn chứng)

- **Nghị định 13/2023 đã hết hiệu lực 01/01/2026**, thay bằng **Nghị định 356/2025/NĐ-CP**. Luật BVDLCN **91/2025/QH15** hiệu lực 01/01/2026 (phạt tới 5% doanh thu khi chuyển dữ liệu xuyên biên giới).
- **SAP Joule KHÔNG chạy on-premise** (chỉ S/4HANA Cloud) — quan trọng vì nhiều khách BRAVO on-prem.
- **SQL Server 2025**: kiểu VECTOR + VECTOR_DISTANCE [GA 18/11/2025]; vector index DiskANN + VECTOR_SEARCH + AI_GENERATE_EMBEDDINGS **còn preview**; sinh embedding gọi REST ra ngoài.
- **Text-to-SQL**: GPT-4o ~52,54% (BIRD); ~6% trên Spider 2.0; lỗi chủ đạo = schema hallucination.
- Đối thủ VN (MISA AVA/OneAI/meInvoice, FAST AI, Bizzi) đã GA; mọi số năng suất là **vendor claim**.
- Nguồn chi tiết: [docs/seminar-context.md](./docs/seminar-context.md).

## 8. Cần verify nội bộ trước khi trình bày (Tien tự hỏi mentor)

1. **Phạm vi BravoGen** (rủi ro trùng flagship lớn nhất — định vị "sản phẩm hóa + eval").
2. Tính năng AI hiện có của BRAVO 8R3/10 (tránh đề xuất trùng).
3. Kiến trúc từng phiên bản 8/8R3/10 (WinForms/WCF/microservices…) — đang để `[cần verify]`.
4. Tên/cấu trúc bảng thật; có public write-API không; report designer dùng gì.
5. Phiên bản SQL Server khách (native vector chỉ ở 2025).
6. Phân loại "dữ liệu nhạy cảm" theo Luật 91/2025 cho dữ liệu kế toán — hỏi pháp chế.

## 9. Working style với Claude

- **Không yes-man**: khi không đồng ý → nêu lý do + dữ liệu/nguồn + đề xuất thay thế, rồi để Tien quyết.
- **Flag uncertainty rõ**: liệt kê giả định ẩn + điểm rủi ro; khi không chắc API/version → "cần verify", không hallucinate.
- **Giữ scope tối thiểu**, không overengineer, không biến seminar thử việc thành dự án tái cấu trúc.

## 10. Trạng thái & bước tiếp theo

- ✅ Gói nội dung seminar 8 sản phẩm (trong lịch sử chat) + POC scaffold chạy được + seed data.
- ⏭ Tiếp: (a) Tien hỏi mentor mục 8; (b) chạy `ingest.py --seed && eval.py`, báo kết quả; (c) mở rộng eval ~50 câu; (d) drill Q&A (Claude đóng vai hội đồng); (e) tinh slide/script theo giọng Tien.
