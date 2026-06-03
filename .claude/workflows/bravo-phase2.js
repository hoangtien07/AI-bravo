export const meta = {
  name: 'bravo-phase2',
  description: 'Build Phase-2 ChatAI BRAVO tự động (FastAPI, eval-judge, analytics, gợi ý, tenant seam, deploy) + review + verify eval',
  phases: [
    { title: 'Build', detail: '5 sub-agent dựng file MỚI song song (distinct files)' },
    { title: 'Tenant seam', detail: 'thêm filter tenant_id (tuần tự, sửa store/rag)' },
    { title: 'Integrate+Verify', detail: 'cập nhật deps/README, smoke import, chạy eval thật' },
    { title: 'Review', detail: 'phản biện đối kháng + verdict hồi quy' },
  ],
}

const CTX = `
SẢN PHẨM: ChatAI RAG hỏi-đáp tiếng Việt trên tài liệu help BRAVO 10 CÔNG KHAI (651 trang -> 1585 chunk).
Stack Phase-1 (đã chạy LIVE, eval 55/56): config.py (đọc .env đầu file), provider.py (gateway openai|gemini|ollama + backoff), store.py (chroma|numpy; máy này VECTOR_STORE=numpy vì chromadb segfault Windows), rag.py (hybrid BM25+vector+RRF + 6 rào chắn + ask()->{answer,sources,hits,refused,route,max_sim}), ingest.py (chunk theo đoạn + prepend breadcrumb path; metadata gồm tenant_id='bravo_internal', data_class='public_help'), rerank.py (tùy chọn), app.py (Streamlit), eval.py + eval_questions.yaml (53 câu, đo keyword coverage + refuse). Provider hiện tại = OpenAI (gpt-4.1-mini + text-embedding-3-large) qua .env.

RÀNG BUỘC CỨNG (mọi agent phải giữ):
- KHÔNG phá 6 rào chắn / không đổi ngữ nghĩa rag.ask. Chỉ dữ liệu CÔNG KHAI. Không hardcode/commit key.
- Tiếng Việt cho nội dung/UI, English cho code identifier. Tối giản, comment tiếng Việt, KHÔNG kéo LangChain.
- KHÔNG bịa số liệu/ROI/nội dung ERP. eval/LLM thật tốn token OpenAI -> chạy gọn, 1 lần.
- Pha Build: CHỈ tạo file MỚI được giao, KHÔNG sửa config.py/requirements.txt/.env, KHÔNG pip install, KHÔNG chạy (tránh xung đột). Báo dep/biến mới trong kết quả để pha Integrate xử lý.
- Mỗi agent đóng vai chuyên gia tương ứng (backend / eval-observability / retrieval-quality / devops / multitenant / reviewer) và tuân thủ mọi ràng buộc trên. Dùng Read/Write/Edit/Bash trong thư mục d:\\Tien\\bravo.
`

// ---------- Phase A: build các file MỚI (song song, distinct files) ----------
phase('Build')
const BUILD = [
  { label: 'build:api', agentType: 'general-purpose',
    task: `Tạo MỚI api.py (FastAPI): GET /healthz (trả {status, provider, embed, store, route}); POST /ask body {question, k?, min_sim?, tenant_id?} -> trả NGUYÊN dict rag.ask (answer, sources, hits, refused, route, max_sim); POST /feedback body {question, rating} -> ghi data/feedback.jsonl (tái dùng cách redact của rag._redact). Chạy bằng: uvicorn api:app. KHÔNG sửa rag.py. Báo dep mới (fastapi, uvicorn[standard], pydantic).` },
  { label: 'build:judge+analytics', agentType: 'general-purpose',
    task: `Tạo MỚI 2 file: (1) eval_judge.py — LLM-as-judge dùng provider.chat chấm faithfulness (câu trả lời có được ngữ cảnh hỗ trợ không) + answer_relevancy cho các câu expect=answer trong eval_questions.yaml; có --limit để giới hạn số câu (mặc định 10) nhằm tiết kiệm token; in điểm trung bình + ngày chạy + model. (2) analytics.py — đọc data/audit_log.jsonl + data/feedback.jsonl, in coverage report: tổng truy vấn, tỷ lệ refused, top câu bị từ chối, tỷ lệ 👎, phân bố theo route/provider. KHÔNG gọi LLM trong analytics.py. KHÔNG sửa eval.py.` },
  { label: 'build:suggest', agentType: 'general-purpose',
    task: `Tạo MỚI suggest.py — tính năng "câu hỏi liên quan": hàm related_questions(question) dùng rag.retrieve lấy chunk rồi provider.chat sinh 3-5 câu hỏi follow-up GROUNDED chỉ dựa trên nội dung chunk (không bịa ngoài tài liệu); trả list[str]; có __main__ demo. KHÔNG sửa rag.py (chỉ import dùng). Đây là tính năng net-new (BRAVO chưa có) nhưng phải bám tài liệu công khai.` },
  { label: 'build:deploy', agentType: 'general-purpose',
    task: `Tạo MỚI: Dockerfile (python:3.12-slim, cài requirements, chạy uvicorn api:app --host 0.0.0.0 --port 8000), docker-compose.yml (service "api" đọc .env; service "chroma" tùy chọn dùng image chromadb chạy SERVER + ghi chú đổi VECTOR_STORE/HttpClient), docs/deploy.md (biến môi trường, cấp key qua secret KHÔNG nhúng image, chọn vector store, checklist việc người/hạ tầng còn thiếu: domain/TLS/auth/rate-limit/monitoring/backup/billing). KHÔNG nhúng key.` },
]
const built = await parallel(BUILD.map(b => () =>
  agent(`${CTX}\n\nNHIỆM VỤ (${b.label}):\n${b.task}`,
    { label: b.label, phase: 'Build', agentType: b.agentType })))
log('Phase A xong: ' + built.filter(Boolean).length + '/4 nhóm file mới.')

// ---------- Phase B: tenant seam (tuần tự, sửa file có sẵn cẩn thận) ----------
phase('Tenant seam')
const tenant = await agent(
  `${CTX}\n\nNHIỆM VỤ: Thêm seam đa khách OPT-IN, mặc định KHÔNG đổi hành vi.
- store.py: thêm tham số optional where=None cho query() ở CẢ _ChromaStore lẫn _NumpyStore (numpy lọc theo metadata khớp dict where; chroma truyền where). Mặc định None = không lọc.
- rag.py: retrieve() và ask() nhận optional tenant_id=None, data_class=None; nếu có thì build where={'tenant_id':...}/{'data_class':...} và truyền xuống store.query. Mặc định None -> hành vi y hệt cũ. KHÔNG đụng 6 rào chắn.
Sau khi sửa, KHÔNG chạy eval (để pha Integrate chạy). Báo chính xác đã sửa gì + vì sao không phá default.`,
  { label: 'tenant:seam', phase: 'Tenant seam', agentType: 'general-purpose' })

// ---------- Phase C: integrate + verify (chạy eval thật 1 lần) ----------
phase('Integrate+Verify')
const buildNotes = built.filter(Boolean).map((t, i) => `[${BUILD[i].label}]\n${t}`).join('\n\n')
const integrate = await agent(
  `${CTX}\n\nKết quả pha Build (dep/biến mới do các agent báo):\n${buildNotes}\n\nKết quả pha Tenant:\n${tenant}\n\nNHIỆM VỤ INTEGRATE + VERIFY:
1. Cập nhật requirements.txt: thêm fastapi, "uvicorn[standard]", pydantic (và dep khác các agent báo). Cập nhật .env.example nếu có biến mới. Thêm 1 mục ngắn vào README.md liệt kê file/endpoint mới + cách chạy api (uvicorn api:app).
2. Cài dep mới: .venv/Scripts/python.exe -m pip install fastapi "uvicorn[standard]" pydantic (và dep mới khác).
3. Smoke import OFFLINE (không cần API): PYTHONUTF8=1 .venv/Scripts/python.exe -c "import api, eval_judge, analytics, suggest, rag, store, provider, ingest, config" — sửa lỗi import nếu có.
4. CHẠY EVAL THẬT 1 LẦN để chứng minh KHÔNG regression: PYTHONUTF8=1 .venv/Scripts/python.exe eval.py  (tốn token OpenAI, chấp nhận). Ghi lại con số answer/refuse/tổng.
5. (Tùy chọn, nếu nhanh) PYTHONUTF8=1 .venv/Scripts/python.exe eval_judge.py --limit 6 để có điểm faithfulness mẫu.
Báo: con số eval trước (55/56) vs sau, file/endpoint mới, dep đã cài, lỗi đã sửa, rủi ro còn lại.`,
  { label: 'integrate:verify', phase: 'Integrate+Verify', agentType: 'general-purpose' })

// ---------- Phase D: review đối kháng ----------
phase('Review')
const review = await agent(
  `${CTX}\n\nTÓM TẮT THAY ĐỔI:\nBUILD:\n${buildNotes}\n\nTENANT:\n${tenant}\n\nINTEGRATE:\n${integrate}\n\nNHIỆM VỤ: Phản biện đối kháng + kiểm hồi quy (CHỈ ĐỌC, chạy import/kiểm tra, KHÔNG sửa). Xác nhận: 6 rào chắn còn nguyên, rag.ask không đổi ngữ nghĩa, không rò rỉ tenant/PII ra cloud, không hardcode key, .gitignore đủ (api/.env), eval không regression. Trả verdict PASS/FAIL hồi quy + danh sách phát hiện theo mức + top fix.`,
  { label: 'review:adversarial', phase: 'Review', agentType: 'Explore' })

return { built, tenant, integrate, review }
