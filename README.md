# Trợ lý nghiệp vụ BRAVO — ChatAI RAG (cloud-first, pluggable)

Hỏi-đáp tiếng Việt trên **tài liệu help BRAVO công khai**, **có trích nguồn (deep-link)**, **đổi nhà cung cấp LLM bằng config** (OpenAI / Gemini cloud · Ollama self-host). Hướng tới sản phẩm dịch vụ chatAI cho **nội bộ BRAVO** và **khách đăng ký** (multi-tenant — roadmap).

> ⚠️ **Nhãn demo (bắt buộc nói trên slide):** tài liệu là **công khai (help.bravo.com.vn) / minh hoạ** — KHÔNG phải dữ liệu khách hàng. Khi bật cloud, **câu hỏi có thể gửi ra dịch vụ AI bên ngoài** → chỉ dùng cho dữ liệu công khai (tuân thủ Luật 91/2025: xem §6).

---

## 0. Kiến trúc

```
Câu hỏi → [rào chắn PII] → embed (provider) → truy hồi HYBRID (BM25 + vector, hợp nhất RRF)
        → lọc ngưỡng cosine (chống bịa) → LLM (provider) → trả lời + DEEP-LINK NGUỒN → audit log
```

| File | Vai trò |
|---|---|
| `config.py` | Cấu hình tập trung; đọc `.env` (provider, model, ngưỡng, vector store) |
| `provider.py` | **Gateway LLM/embedding pluggable** (OpenAI/Gemini/Ollama) + retry/backoff |
| `store.py` | **Vector store pluggable**: `chroma` (mặc định) hoặc `numpy` (fallback brute-force) |
| `rerank.py` | Rerank tùy chọn (cross-encoder bge-reranker-v2-m3), bật bằng `RERANK_ENABLED=1` |
| `ingest.py` | Chunk structure-aware (theo đoạn + prepend breadcrumb path) + embed + nạp store |
| `rag.py` | Lõi RAG + **6 rào chắn** (xem §5) + hybrid retrieval + citation |
| `app.py` | Giao diện chat Streamlit (nhãn động theo route + feedback 👍/👎) |
| `eval.py` + `eval_questions.yaml` | 53 câu bám corpus thật; đo **đúng nội dung** (keyword) + rào chắn |
| `crawl_bravo10_help.py` | Crawl SPA help.bravo.com.vn (Playwright) → `data/raw/bravo10_help.jsonl` (651 trang) |
| `api.py` | **Cổng HTTP FastAPI** bọc `rag.ask` (lớp mỏng, giữ nguyên 6 rào chắn) — xem §10 |
| `eval_judge.py` | **LLM-as-judge**: chấm `faithfulness` + `answer_relevancy` (thang 1–5) ngoài keyword |
| `analytics.py` | **Báo cáo coverage/observability** từ `audit_log.jsonl`+`feedback.jsonl` (offline, KHÔNG gọi LLM) |
| `suggest.py` | **Câu hỏi liên quan** (follow-up) grounded trên chunk truy hồi, tái dùng rào chắn PII/ngưỡng |
| `generate.py` | **Trợ lý sinh nội dung** (KHÔNG dữ liệu nghiệp vụ): soạn email/JD/kịch bản gọi/phỏng vấn/nội dung/ý tưởng + dịch/soát chính tả/tóm tắt/công thức Excel. PII tự ẩn trước khi gửi cloud |
| `Dockerfile` · `docker-compose.yml` · `docs/deploy.md` | Đóng gói + triển khai (chạy `uvicorn api:app`) |

### Tính năng AN TOÀN (cloud, KHÔNG chạm dữ liệu nhạy cảm) — 3 tab trên Streamlit
- **💬 Hỏi-đáp & Tra cứu**: RAG grounded trên help công khai (trích nguồn deep-link) + câu hỏi liên quan.
- **✍️ Soạn nháp** (Sales/HR/Marketing): email · JD · kịch bản gọi · câu hỏi phỏng vấn · dàn ý nội dung/SEO · gợi ý ý tưởng — từ yêu cầu người dùng.
- **🧰 Tiện ích**: dịch · soát chính tả/văn phong · tóm tắt văn bản dán · trợ lý công thức Excel.
> Mọi đầu ra sinh nội dung là **BẢN NHÁP** để người duyệt; đầu vào chứa PII (SĐT/email/MST/CCCD) được **tự động ẩn** trước khi gửi cloud (`generate.py` tái dùng `rag._redact`). Các tính năng chạm **số liệu thật** (phân tích báo cáo, đối chiếu, dự báo) thuộc **roadmap self-host** — chưa làm vì chưa có phần cứng.
> CLI thử nhanh: `python generate.py soan_email "nhắc công nợ…"` · `python generate.py excel "SUMIF…"` · `python generate.py dich "…"`.

---

## 1. Yêu cầu

- **Python 3.12** (`py -3.12`). 3.14 thiếu wheel cho vài thư viện.
- **API key** cho provider cloud (mặc định) — hoặc **Ollama** nếu chạy self-host.

## 2. Cài đặt (trong `D:\Tien\bravo`)

```bash
py -3.12 -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env          # rồi điền GEMINI_API_KEY hoặc OPENAI_API_KEY
```

`.env` (xem `.env.example`):
```
LLM_PROVIDER=openai           # openai | gemini | ollama
EMBED_PROVIDER=openai
VECTOR_STORE=numpy            # numpy (chạy mọi nơi) | chroma (xem §7)
OPENAI_API_KEY=...            # hoặc GEMINI_API_KEY=...
```
> Self-host (không cần key, không gửi dữ liệu ra ngoài): đặt `LLM_PROVIDER=ollama`, `EMBED_PROVIDER=ollama`, rồi `ollama pull qwen3:8b && ollama pull bge-m3`.

## 3. Chạy

```bash
python ingest.py --reset                 # nạp 651 trang help vào store (qua embedding provider)
python rag.py "BRAVO 10 có những tính năng AI nào?"
python eval.py                           # 53 câu: đo đúng nội dung + rào chắn
streamlit run app.py                     # giao diện chat
```
Đổi provider/embedder ⇒ phải `ingest.py --reset` lại (mỗi embedder có store riêng theo số chiều vector).

---

## 4. Kết quả đo (LIVE, OpenAI `gpt-4.1-mini` + `text-embedding-3-large`, 651 trang / 1585 chunk)

- **answer: 40/41 pass · keyword coverage TB 92%**
- **refuse: 15/15 pass** (out-of-domain · PII khách · thời sự — đều bị chặn/từ chối)
- **Tổng: 55/56 (98%)**. Câu trượt do keyword khắt khe (đáp đúng, diễn đạt khác) → cần mentor duyệt keyword.

> Số liệu cập nhật theo lần chạy gần nhất; chạy lại `python eval.py` để tái tạo.

## 5. Sáu rào chắn an toàn

1. **Grounding** — prompt buộc chỉ trả lời từ ngữ cảnh (`SYSTEM` trong `rag.py`).
2. **Ngưỡng cosine (`MIN_SIM`)** — dưới ngưỡng → từ chối, không gọi LLM. (Có "soft refusal": LLM tự trả câu từ chối khi ngữ cảnh không đủ.)
3. **Trích nguồn bắt buộc** — deep-link tới đúng trang help.
4. **Audit log** — `data/audit_log.jsonl` (câu hỏi đã redact PII, nguồn, provider/route/model).
5. **PII pre-check** — chặn câu hỏi chứa SĐT/email/MST/CCCD trước khi gửi ra cloud *(giảm thiểu, không miễn trừ)*.
6. **Chống prompt-injection gián tiếp** — nội dung tài liệu được đóng khung là DỮ LIỆU, không phải lệnh.

## 6. Pháp lý dữ liệu (tóm tắt — xem kế hoạch chi tiết)

Tài liệu help **công khai** → gửi qua cloud về cơ bản không vi phạm chuyển dữ liệu cá nhân (Luật 91/2025 + NĐ 356/2025). Rủi ro chỉ ở câu hỏi chứa PII (→ rào chắn 5) hoặc khi mở rộng sang **dữ liệu riêng của khách** (→ bắt buộc self-host + nghĩa vụ TIA/DPA). **Bản thương mại** cần xác nhận quyền dùng nội dung help với BRAVO/pháp chế.

## 7. Vector store trên Windows (lưu ý quan trọng)

- **chromadb 1.5.9** (mới nhất, có advisory bảo mật → nên là bản mới) **segfault native** khi `PersistentClient` ghi trên máy Windows này (lỗi nền tảng, không sửa được từ Python). **0.5.x** thì cũ + dính advisory + cần C++ Build Tools.
- Vì vậy **mặc định trên máy này: `VECTOR_STORE=numpy`** (brute-force cosine, tức thời ở quy mô ~1585 vector, chạy mọi nơi).
- **Để dùng chroma production:** chạy **chroma server** (`chroma run` / Docker) rồi `HttpClient` (tránh crash in-process), hoặc đổi sang **Qdrant / pgvector / SQL Server 2025 VECTOR** (khớp stack SQL Server + .NET của BRAVO). `store.py` đã pluggable để thay backend.

## 8. Xử lý lỗi thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| `429 RESOURCE_EXHAUSTED` (Gemini) | Key free-tier hết quota → dùng `OPENAI_*` hoặc chờ; provider đã có backoff |
| `Thiếu GEMINI_API_KEY/OPENAI_API_KEY` | Điền key vào `.env` |
| chromadb segfault | Đặt `VECTOR_STORE=numpy` trong `.env` (xem §7) |
| Đổi embedder mà kết quả lạ | Phải `python ingest.py --reset` (store khoá theo số chiều embedding) |

---

## 10. API HTTP + công cụ vận hành (mới)

```bash
uvicorn api:app                          # http://127.0.0.1:8000 — tài liệu /docs
python eval_judge.py --limit 6           # LLM-as-judge (tốn token): faithfulness + answer_relevancy
python analytics.py                      # báo cáo coverage từ log (offline, miễn phí)
python suggest.py "Khai báo khấu hao TSCĐ ở đâu?"   # gợi ý câu hỏi liên quan
```

**Endpoint** (lớp mỏng quanh `rag.ask`, KHÔNG đổi 6 rào chắn):

| Method | Path | Body | Trả về |
|---|---|---|---|
| GET | `/healthz` (và `/health`) | — | `{status, provider, embed, store, route}` — probe nhẹ, **không gọi LLM** (0 token) |
| POST | `/ask` | `{question, k?, min_sim?, tenant_id?}` | **nguyên dict** `rag.ask`: `{answer, sources, hits, refused, route, max_sim}` |
| POST | `/feedback` | `{question, rating}` | `{ok}` — ghi `data/feedback.jsonl` (câu hỏi đã redact PII) |

> `tenant_id` được chấp nhận để tương thích phía gọi nhưng **chưa** dùng (Phase-1 đơn tenant `bravo_internal`); isolation đa tenant ở phase sau (đổi `rag`/`store`).
> Docker: `docker compose up` (đọc key từ `.env`, mount `./data`). Chi tiết biến môi trường + cấp key an toàn: `docs/deploy.md`.

## 9. Liên hệ kế hoạch & dữ liệu
- Kế hoạch tái cấu trúc đầy đủ (phase 1→3, scope, chi phí, pháp lý): `C:\Users\<user>\.claude\plans\...`.
- `CLAUDE.md` / `docs/seminar-context.md` — thesis, ràng buộc, sự thật đã kiểm chứng.
- **Cần hỏi mentor:** phạm vi **BravoGen** (định vị không trùng) · duyệt keyword bộ eval · quyền dùng nội dung help cho bản tính phí.
