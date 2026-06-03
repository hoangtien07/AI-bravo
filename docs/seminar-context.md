# Ngữ cảnh seminar — nhật ký quyết định + sự thật đã kiểm chứng

Tài liệu nền cho POC. Bản đầy đủ 8 sản phẩm seminar nằm trong lịch sử chat với Claude; đây là bản cô đọng để dự án tự chứa.

## 1. Mục tiêu kép
1. Tăng năng suất **người dùng cuối** (kế toán, quản trị).
2. Hỗ trợ chính **đội triển khai BRAVO** (khán giả trong phòng) — điểm khác biệt, nên nhấn.

## 2. Thesis tinh chỉnh
BRAVO mạnh lớp **mô tả/chẩn đoán** (BI Dashboard) + đã chạm AI sơ khởi (OCR, cảnh báo bất thường, BravoGen). Gap = **predictive + prescriptive + generative có dẫn chứng**. Định vị: cơ hội bắt kịp.

## 3. Chọn flagship (khung 5 trục)
Quy tắc chọn = giao của (Impact Cao) ∩ (Effort Thấp–TB) ∩ (Demo ≤4 ngày) ∩ (**Rủi ro dữ liệu Thấp**).
- **B1 RAG help docs** = giao điểm duy nhất → **flagship**. Không PII, demo 1–2 ngày, phục vụ đội triển khai.
- **A1 Text-to-SQL** trượt tiêu chí "rủi ro dữ liệu Thấp" + thiếu prerequisite (semantic layer, account read-only) → bước **walk**.
- Lưu ý prerequisite override điểm thô; mặc định không ghép.

## 4. Lộ trình crawl–walk–run
- **Crawl**: B1 trợ lý help docs, dùng nội bộ đội triển khai trước (rủi ro thấp).
- **Walk**: A1 hỏi-đáp dữ liệu read-only + semantic layer + view whitelist + human-in-the-loop, demo **mock data**.
- **Run**: dự báo dòng tiền/công nợ + đề xuất (luôn người duyệt). Cần dữ liệu + MLOps.

## 5. Rào chắn an toàn flagship
Grounding + citation · ngưỡng tương đồng (chống bịa) · self-host (không gửi dữ liệu ra ngoài) · multi-tenant isolation (nếu host nhiều khách — regression-critical) · audit log · LLM on-prem (POC 7–8B Q4; prod 14B–32B Q4).

## 6. Hai cấu hình POC vs production
- **(a) POC máy cá nhân**: model 7–8B Q4 (Ollama) hoặc cloud, **chỉ chạy trên dữ liệu công khai/giả**. Laptop 16GB, không cần GPU.
- **(b) Production khách on-prem**: self-host 14B–32B Q4 hoặc SQL Server 2025 VECTOR (dữ liệu không rời DB; embedding endpoint nội bộ).

## 7. Sự thật đã kiểm chứng (kèm nguồn)

| Chủ đề | Kết luận | Trạng thái/Nguồn |
|---|---|---|
| Pháp lý VN | ND 13/2023 **hết hiệu lực 01/01/2026** → **ND 356/2025/NĐ-CP**; Luật 91/2025/QH15 hiệu lực 01/01/2026; phạt tới 5% doanh thu (chuyển xuyên biên giới) | bocongan.gov.vn, thuvienphapluat.vn, EY VN |
| SAP Joule | Chỉ S/4HANA Cloud, **KHÔNG on-premise** (SAP Note 3632703); Cash Mgmt Agent beta Q4/2025 | Mindset Consulting, SAP News |
| Oracle Fusion | 100+ prebuilt agents [GA], OCI security boundary, Payables Agent khớp PO+receipt | Oracle (15/10/2025), epiqinfo |
| MS Dynamics BC | Analysis Assist [GA 10/2025]; bank rec assist **preview**; có Copilot Credits | Microsoft Learn |
| MISA/FAST/Bizzi | Đã GA tự động hóa HĐ-thuế-hạch toán; số năng suất (80%, x3, x5, 99,9%) = **vendor claim** | amis.misa.vn, fast.com.vn, bizzi.vn |
| SQL Server 2025 | GA 18/11/2025; VECTOR + VECTOR_DISTANCE [GA]; DiskANN/VECTOR_SEARCH/AI_GENERATE_EMBEDDINGS **preview**; embedding gọi REST ra ngoài | Microsoft Learn, Azure SQL Dev Corner |
| Chủ quyền dữ liệu | Không LLM lớn nào có region VN (Azure SEA = Singapore); OpenAI residency Á không có VN | Microsoft Learn, OpenAI |
| Text-to-SQL | GPT-4o ~52,54% (BIRD), human 92,96%; Spider 2.0 ~6%; lỗi chủ đạo = schema hallucination; read-only cần nhưng chưa đủ | BIRD/Spider leaderboard, Promethium |
| RAG self-host | bge-m3 (MIT, 1024-dim) / AITeamVN Vietnamese_Embedding; Chroma/pgvector; Ollama; 7–8B Q4 ~5–6GB/16GB RAM; Qwen3 Apache-2.0 (an toàn TM) | HuggingFace, Ollama docs |
| BRAVO hiện có | BI Dashboard [GA]; BRAVO 10 (28/10/2024) cloud-native, CYSEEX pentest Q1/2025; AI OCR (CV) [GA]; cảnh báo bất thường [GA]; BravoGen [nội bộ]; Text-to-SQL & public write-API **chưa xác minh** | bravo.com.vn, dev-dn.bravo.com.vn |

## 8. Cần verify nội bộ (xem CLAUDE.md mục 8)
BravoGen · AI hiện có 8R3/10 · kiến trúc phiên bản · schema thật · public write-API · report engine · SQL Server version khách · phân loại dữ liệu nhạy cảm (hỏi pháp chế).

## 9. Khung chấm ASK (mentor tự đối chiếu)
Nội dung/chiều sâu ~30% · hiểu nghiệp vụ+BRAVO ~25% · khả thi ~15% · trình bày/slide ~15% · Q&A/thái độ ~15%. Bài mạnh ở khả thi + cầu thị; yếu cần luyện = chiều sâu nghiệp vụ kế toán cho Q&A.
