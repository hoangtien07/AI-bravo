# ChatAI BRAVO — Web UI (frontend)

SPA (Vite + React + TypeScript + Tailwind) gọi FastAPI [`api.py`](../api.py). Thiết kế bám
[`DESIGN.md`](../DESIGN.md) — "hiến pháp phong cách" BRAVO (màu, chữ, rào chắn hữu hình,
checklist anti-patterns để kiểm duyệt).

## Chạy

**Cần backend chạy trước** (cùng venv 3.12 của dự án):

```bash
# terminal 1 — API
uvicorn api:app --port 8000        # cần đã `ingest.py` để có dữ liệu

# terminal 2 — frontend dev (proxy /ask… sang :8000, hot-reload)
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

## Build production (cùng origin, không cần CORS)

```bash
cd frontend && npm run build       # sinh frontend/dist
uvicorn api:app --port 8000        # api.py tự phục vụ dist tại http://localhost:8000
```

## Bản đồ

- `src/api.ts` — client typed (đường dẫn tương đối: dev qua proxy Vite, prod cùng origin).
- `src/types.ts` — shape khớp `rag.ask` / `generate` / `suggest`.
- `src/components/ChatView.tsx` — Hỏi-đáp đa lượt + trust strip + citation + minh hoạ ảnh + gợi ý.
- `src/components/GenerateView.tsx` — Soạn nháp / Tiện ích (badge "BẢN NHÁP").
- `src/components/{TrustStrip,Sources,Illustrated}.tsx` — lớp bằng chứng tin cậy (rào chắn hữu hình).
- `tailwind.config.js` + `src/index.css` — token đồng bộ `DESIGN.md`.

## Lưu ý

- KHÔNG hardcode host API — luôn đường dẫn tương đối. Đổi cổng backend thì sửa proxy ở `vite.config.ts`.
- Streamlit cũ ([`app.py`](../app.py)) vẫn chạy được song song; web này là bản redesign thay thế.
