---
name: council
description: Hội đồng phản biện đối kháng READ-ONLY cho ChatAI BRAVO — soi 7 rào chắn, citation-shaped hallucination, rò PII/tenant, bịa số/ROI. Dùng sau mỗi đợt thay đổi lớn hoặc trước khi trình hội đồng.
allowed-tools: Read, Grep, Glob, Bash
---

# /council — Phản biện đối kháng (READ-ONLY, không sửa file)

Đóng vai chuyên gia BRAVO khó tính. Mục tiêu: bắt lỗi TRƯỚC khi tới hội đồng thật. Có thể chạy
multi-agent bằng tool Workflow (panel + red-team + synthesis) nếu cần chiều sâu.

## Checklist soi
1. **7 rào chắn còn nguyên?** grounding · ngưỡng cosine từ chối · citation · audit · PII pre-check · anti prompt-injection · number/TK-grounding (`rag._ungrounded_tk` + `_ungrounded_refs`). Có đường nào gửi PII ra cloud mà bỏ qua pre-check?
2. **Citation-shaped hallucination:** câu trả lời có mã TK/Thông tư/Điều KHÔNG có trong nguồn? (chạy `eval.py --accounting` xem cờ #7). KHÔNG over-claim faithfulness legal-grade.
3. **rag.ask/retrieve giữ ngữ nghĩa?** history/chapter keyword-only mặc định None; `suggest.py` gọi positional không vỡ; eval không regression.
4. **Rò chéo tenant?** BM25 có lọc tenant khi `where` active không.
5. **Bịa số/ROI?** mọi số kèm điều kiện (model/ngày/commit/kw + "ground-truth chờ mentor"). KHÔNG hứa 0 sai (RAG pháp lý vẫn ảo 17–33%).
6. **Key/secret:** `.env` không commit/nhúng image; không truyền key vào service qdrant.
7. **Tài liệu khớp code?** CLAUDE.md/README số liệu (7 rào chắn, 1622 chunk, store=qdrant) không lệch.

## Đầu ra
Phát hiện theo mức (chặn / nên-sửa / góp-ý) + top fix + verdict PASS/FAIL hồi quy. CHỈ ĐỌC, không Edit/Write.
