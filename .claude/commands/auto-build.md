---
description: Điều phối đa tác tử tự động build/hoàn thiện ChatAI BRAVO theo phase (mặc định phase2)
argument-hint: "[phase2|review] — mặc định phase2"
---

Bạn là ĐIỀU PHỐI VIÊN (orchestrator) cho dự án ChatAI RAG BRAVO. Người dùng muốn tự động hoàn thiện sản phẩm bằng đa tác tử (multi-agent), có thể "treo máy".

Tham số: `$ARGUMENTS` (mặc định `phase2`).

## Việc cần làm

1. Đọc nhanh trạng thái hiện tại: `README.md`, `CLAUDE.md`, và plan ở `~/.claude/plans/` (nếu có) để nắm phase đang ở đâu.
2. Chạy workflow tương ứng **ở chế độ nền** bằng tool Workflow:
   - `phase2` (mặc định): `Workflow({ scriptPath: ".claude/workflows/bravo-phase2.js" })`
   - Nếu người dùng nêu phase khác và đã có script `.claude/workflows/bravo-<phase>.js` thì chạy script đó.
3. Trong khi chờ: KHÔNG tự ý làm trùng việc của workflow. Khi có `<task-notification>` báo hoàn tất, ĐỌC kết quả (đặc biệt verdict của `bravo-reviewer`).
4. Nếu reviewer báo **FAIL hồi quy** hoặc eval tụt so với mốc 55/56: sửa hoặc khôi phục từ `.checkpoints/phase1/`, rồi báo người dùng.
5. Báo cáo gọn: file/endpoint mới, số eval trước/sau, rủi ro, và **các cổng cần con người/hạ tầng** còn lại (duyệt BravoGen, duyệt keyword eval, quyền nội dung help, chroma server/Docker, auth/billing) — KHÔNG giả vờ đã xong những phần này.

## Ràng buộc
- Tôn trọng 6 rào chắn + chỉ dữ liệu công khai + không hardcode/commit key + honest cost (không bịa số liệu/ROI).
- Các sub-agent dùng: `bravo-rag-backend`, `bravo-retrieval-quality`, `bravo-multitenant`, `bravo-eval`, `bravo-devops`, `bravo-reviewer` (trong `.claude/agents/`).
- Multi-tenant SaaS thật (auth/billing/isolation) là Phase-3: chỉ scaffolding + roadmap, KHÔNG xây thật khi chưa có quyết định/hạ tầng.
