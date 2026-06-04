---
name: ingest
description: Nạp/cập nhật corpus ChatAI BRAVO (help + KB quy định) vào vector store; hỗ trợ vòng đời theo category. Dùng khi thêm/sửa/xóa nguồn tri thức.
allowed-tools: Bash, Read
---

# /ingest — Nạp & quản lý vòng đời tri thức BRAVO

## Lệnh
```bash
cd /d/Tien/bravo
PYTHONUTF8=1 .venv/Scripts/python.exe ingest.py --reset                 # nạp lại sạch help + KB quy định (~1622 chunk)
PYTHONUTF8=1 .venv/Scripts/python.exe ingest.py --seed                  # chỉ tài liệu minh hoạ
PYTHONUTF8=1 .venv/Scripts/python.exe ingest.py --category phong_X      # gắn category khi nạp lô tài liệu
PYTHONUTF8=1 .venv/Scripts/python.exe ingest.py --delete-category phong_X --reset  # xóa lô cũ trước khi nạp
```
Verify: in ra "Đã nạp N chunk"; đối chiếu N hợp lý (~1622 với corpus đầy đủ).

## Lưu ý bắt buộc
- **Đổi EMBED_PROVIDER ⇒ PHẢI `--reset`**: collection khoá theo embed model (dim khác nhau: bge-m3=1024, OpenAI/Gemini=3072) — trộn = hỏng.
- Vector store theo `.env` (`VECTOR_STORE=qdrant|numpy|chroma`). Qdrant cần container chạy.
- Chuyển numpy→Qdrant KHÔNG re-embed: `migrate_to_qdrant.py` (tiết kiệm token).
- Embed qua cloud tốn token; corpus lớn nạp vài phút.
- Sau ingest/xóa khi app đang chạy: gọi `rag.reload_corpus()` (hoặc restart) để BM25 cập nhật.
