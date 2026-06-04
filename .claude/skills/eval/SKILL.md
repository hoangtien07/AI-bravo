---
name: eval
description: Chạy & báo cáo eval ChatAI BRAVO — help (56 câu), định khoản (exact-match TK), benchmark. Dùng khi cần đo độ tin cậy / kiểm hồi quy sau khi sửa code.
allowed-tools: Bash, Read
---

# /eval — Đo độ tin cậy ChatAI BRAVO (kỷ luật legal-AI)

Mục tiêu: cho con số TRUNG THỰC, kiểm hồi quy. KHÔNG hardcode kết quả — luôn đọc đuôi output thật.

## Cách chạy
```bash
cd /d/Tien/bravo
PYTHONUTF8=1 .venv/Scripts/python.exe eval.py                 # help 56 câu (answer + refuse)
PYTHONUTF8=1 .venv/Scripts/python.exe eval.py --accounting    # định khoản 34 case (exact-match TK)
PYTHONUTF8=1 .venv/Scripts/python.exe eval.py --accounting --? # (xem cờ rào chắn #7)
PYTHONUTF8=1 .venv/Scripts/python.exe benchmark.py            # bảng điểm tổng hợp (đọc eval_results.json, KHÔNG gọi LLM)
```

## Lưu ý bắt buộc
- **Tốn token OpenAI** (mỗi câu = 1 embed + 1 chat). Hỏi trước khi chạy nhiều vòng.
- Mốc gần nhất để so hồi quy: **đọc `data/eval_results.json`** (eval.py tự ghi), KHÔNG nhớ con số cũ.
- **Ground-truth định khoản CẦN MENTOR DUYỆT** — báo cáo kèm cảnh báo này, đừng coi 28/34 là tuyệt đối.
- Cần Qdrant chạy (`docker start bravo-qdrant`) nếu `.env` đặt `VECTOR_STORE=qdrant`; nếu không, đổi `VECTOR_STORE=numpy`.
- KHÔNG hứa "0 sai": RAG pháp lý top vẫn ảo 17–33% (Stanford 2025).
