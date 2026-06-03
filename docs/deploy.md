# Triển khai self-host — Trợ lý nghiệp vụ BRAVO (RAG)

> POC seminar thử việc. Khung này để **chạy thử nội bộ / on-prem**, KHÔNG phải cấu hình
> production hoàn chỉnh. Phần [Checklist còn thiếu](#5-checklist-việc-ngườihạ-tầng-còn-thiếu)
> liệt kê rõ việc người/hạ tầng phải làm thêm trước khi mở cho người dùng thật.

Tài liệu này phục vụ **tầng API** (container chạy `uvicorn api:app`). UI demo Streamlit
(`app.py`) chạy riêng bằng `streamlit run app.py` — không bắt buộc trong triển khai.

> ⚠️ **Phụ thuộc chưa có ở Phase-1:** image chạy `uvicorn api:app` nên cần file `api.py`
> (FastAPI, biến `app`, có endpoint `GET /health` cho HEALTHCHECK) — do **pha build:api**
> tạo. Nếu chưa có `api.py`, container sẽ khởi động lỗi `ModuleNotFoundError: api`.
> Khi đó tạm thời chạy UI: `docker compose run --rm -p 8501:8501 api streamlit run app.py --server.address 0.0.0.0`.

---

## 1. Biến môi trường

Đọc từ `.env` (compose `env_file`) hoặc secret của orchestrator. **KHÔNG commit `.env`,
KHÔNG nhúng key vào image** (đã chặn ở `.gitignore` + `.dockerignore`). Mẫu: `.env.example`.

| Biến | Bắt buộc | Mặc định (codebase) | Ý nghĩa |
|------|----------|---------------------|---------|
| `LLM_PROVIDER`   | có | `gemini` | Nhà cung cấp sinh câu trả lời: `openai` \| `gemini` \| `ollama`. |
| `EMBED_PROVIDER` | có | `gemini` | Nhà cung cấp embedding: `openai` \| `gemini` \| `ollama`. |
| `OPENAI_API_KEY` | nếu dùng OpenAI | — | Key OpenAI. **Secret.** |
| `GEMINI_API_KEY` (hoặc `GOOGLE_API_KEY`) | nếu dùng Gemini | — | Key Gemini. **Secret.** |
| `VECTOR_STORE`   | không | `chroma` | `chroma` (embedded/server) \| `numpy` (fallback). Máy build hiện tại = `numpy`. |
| `LLM_MODEL`      | không | theo provider | Ghi đè model chat (vd `gpt-4.1-mini`). |
| `EMBED_MODEL`    | không | theo provider | Ghi đè model embed (vd `text-embedding-3-large`). Đổi model ⇒ **đổi collection ⇒ phải re-ingest**. |
| `MIN_SIM`        | không | theo embed provider | Ngưỡng cosine của rào chắn từ chối. |
| `HYBRID_ENABLED` | không | `1` | Bật BM25+vector+RRF. |
| `RERANK_ENABLED` | không | `0` | Bật cross-encoder rerank (cần model ~600MB + sentence-transformers). |

> **Ollama (self-host model, không cần key):** đặt `LLM_PROVIDER=ollama` / `EMBED_PROVIDER=ollama`.
> Container cần tới được Ollama host — thêm biến `OLLAMA_HOST=http://<host>:11434` và cho phép
> container truy cập (vd thêm service ollama vào compose hoặc `extra_hosts`). Self-host giữ
> dữ liệu **không rời máy** — đúng yêu cầu chủ quyền dữ liệu VN (Luật 91/2025, NĐ 356/2025).

---

## 2. Cấp key qua secret — KHÔNG nhúng image

Theo mức độ tăng dần:

1. **File `.env` (dev/POC nội bộ):** `cp .env.example .env`, điền key, `docker compose up`.
   File `.env` đã bị `.dockerignore` loại nên **không vào image**; chỉ đọc lúc chạy.
2. **Docker secret (Swarm) / Kubernetes Secret (khuyến nghị production):** lưu key trong
   secret store, mount thành biến môi trường hoặc file, KHÔNG để lộ trong `docker inspect`/log.
   Ví dụ K8s: `envFrom: [{ secretRef: { name: bravo-rag-keys } }]`.
3. **Vault / cloud secret manager:** inject lúc khởi động (sidecar/agent). Không lưu key trên đĩa.

**Bắt buộc:** xoay vòng (rotate) key sau mỗi đợt demo/chia sẻ; KHÔNG log key; KHÔNG đưa key
vào `docker build --build-arg` (build-arg lưu trong lịch sử layer).

> Lưu ý: key đang nằm trong `.env` của máy dev hiện tại **phải được thu hồi/đổi** sau buổi làm việc.

---

## 3. Chọn vector store

| Lựa chọn | Khi nào dùng | Cấu hình |
|----------|--------------|----------|
| **numpy** (brute-force) | POC / corpus nhỏ (≤ vài nghìn chunk như hiện tại 1585) / né segfault Chroma trên Windows | `VECTOR_STORE=numpy`. Không cần service phụ. Dữ liệu ở `data/chroma/numpy__<collection>/`. |
| **chroma embedded** | 1 tiến trình API, có C++ Build Tools | `VECTOR_STORE=chroma`. Dữ liệu persist ở `data/chroma/` (mount volume). |
| **chroma server** | Nhiều replica API dùng chung; tách vòng đời store khỏi app | Bật service `chroma` + sửa `store.py` dùng `HttpClient` (xem dưới + ghi chú trong `docker-compose.yml`). |
| **pgvector / SQL Server 2025 VECTOR** | Production hạ tầng MS của khách BRAVO | Backend tương lai (Phase-3); `store.py` đã chừa interface. SQL Server 2025: kiểu `VECTOR` + `VECTOR_DISTANCE` đã GA; index DiskANN/`VECTOR_SEARCH` còn preview `[cần verify version khách]`. |

**Re-ingest = bắt buộc khi:** đổi `EMBED_PROVIDER`/`EMBED_MODEL` (chiều vector + collection đổi),
hoặc chuyển store. Chạy `python ingest.py` (hoặc `docker compose run --rm api python ingest.py`).

### Bật Chroma chạy SERVER (tuỳ chọn)

1. `docker compose --profile chroma up -d` (khởi động service `chroma`).
2. `.env`: `VECTOR_STORE=chroma`, thêm `CHROMA_HOST=chroma`, `CHROMA_PORT=8000`
   (2 biến **MỚI** — pha Integrate cần cho `config.py` đọc + truyền vào store).
3. `store.py` (`_ChromaStore.__init__`): khi có `CHROMA_HOST` thì dùng `chromadb.HttpClient(...)`
   thay `PersistentClient(...)`. Đoạn mẫu nằm trong comment `docker-compose.yml`.
4. Re-ingest vào server: `docker compose run --rm api python ingest.py`.

---

## 4. Chạy

```bash
cp .env.example .env            # rồi điền key (secret)
# ingest 1 lần để sinh data/ (vector store + bm25). Cần key embed.
docker compose run --rm api python ingest.py
docker compose up -d api        # API tại http://localhost:8000  (đặt SAU reverse proxy)
docker compose logs -f api
```

UI demo (không bắt buộc): `streamlit run app.py` (ngoài container, hoặc override command).

---

## 5. Checklist việc người/hạ tầng còn thiếu

POC **chưa** có các lớp dưới đây — phải bổ sung trước khi mở cho người dùng thật:

- [ ] **`api.py`** (FastAPI bọc `rag.ask`, endpoint `/health`) — pha build:api. Bắt buộc để image chạy.
- [ ] **Domain + TLS:** reverse proxy (nginx/Caddy/Traefik) lo HTTPS; container API chỉ nghe nội bộ, KHÔNG expose 8000 ra Internet trực tiếp.
- [ ] **Auth:** xác thực người dùng (SSO/AD của BRAVO hoặc API key nội bộ). Hiện API **không** có auth.
- [ ] **Rate-limit / quota:** chặn lạm dụng + bảo vệ chi phí token cloud (đặt ở proxy hoặc tầng app).
- [ ] **Monitoring & log:** thu thập stdout, theo dõi `data/audit_log.jsonl`, cảnh báo lỗi/độ trễ/tỷ lệ từ chối; sức khoẻ qua `/health`.
- [ ] **Backup:** sao lưu định kỳ volume `data/` (vector store + audit log + feedback). Có quy trình re-ingest từ corpus công khai để khôi phục.
- [ ] **Billing / cost guard:** đặt hạn mức chi tiêu provider cloud; cảnh báo ngưỡng; cân nhắc self-host (Ollama) để bỏ chi phí token và giữ dữ liệu trong nước. `[chi phí token + GPU self-host cần ước lượng, chưa chốt]`.
- [ ] **Chủ quyền dữ liệu:** nếu provider = cloud (OpenAI/Gemini) ⇒ câu hỏi rời VN. CHỈ dùng cho tài liệu CÔNG KHAI; dữ liệu kế toán/PII phải chuyển sang self-host (Luật 91/2025, NĐ 356/2025). Rào chắn PII ở `rag.py` chỉ **giảm thiểu**, không miễn trừ.
- [ ] **Resource limits:** đặt `cpus`/`mem_limit` cho container; nếu bật rerank cần thêm RAM/GPU.
- [ ] **Multi-tenant:** hiện chỉ 1 tenant (`tenant_id='bravo_internal'`, `data_class='public_help'`). Mở nhiều khách cần cô lập dữ liệu theo tenant (regression-critical) — chưa làm.
- [ ] **Cập nhật corpus:** lịch crawl lại tài liệu help công khai + re-ingest khi BRAVO 10 đổi tài liệu.

---

## 6. Phụ thuộc / biến mới sinh ra ở pha Build (cho pha Integrate)

- **Dependency mới (KHÔNG có trong `requirements.txt`):** `fastapi>=0.111`, `uvicorn[standard]>=0.30`
  — hiện cài tường minh trong `Dockerfile` (vì pha Build không sửa `requirements.txt`).
  Pha Integrate cân nhắc đưa vào `requirements.txt`.
- **Biến môi trường mới (tuỳ chọn, mới được tham chiếu, CHƯA đọc trong `config.py`):**
  `CHROMA_HOST`, `CHROMA_PORT`, `OLLAMA_HOST` — chỉ dùng cho Chroma-server / Ollama-remote.
  Pha Integrate thêm xử lý nếu kích hoạt các kịch bản đó.
- **File phụ thuộc:** `api.py` (pha build:api) phải tồn tại để `CMD uvicorn api:app` chạy.
