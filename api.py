"""
api.py — Cổng HTTP (FastAPI) bọc lõi RAG để tích hợp/automation.

Chạy:  uvicorn api:app            (mặc định http://127.0.0.1:8000, tài liệu /docs)

Thiết kế: lớp MỎNG, KHÔNG đụng rag.py. Mọi rào chắn an toàn (PII, ngưỡng cosine,
trích nguồn, audit, anti prompt-injection) vẫn nằm trong rag.ask() — endpoint chỉ
chuyển tiếp và trả NGUYÊN dict kết quả.

Endpoint:
    GET  /healthz   -> tình trạng + cấu hình provider/embed/store/route (probe nhẹ, không gọi LLM)
    GET  /health    -> alias của /healthz (Dockerfile HEALTHCHECK dùng tên này)
    POST /ask       -> {question, k?, min_sim?, tenant_id?} => nguyên dict rag.ask
    POST /feedback  -> {question, rating} => ghi data/feedback.jsonl (đã redact PII)

GHI CHÚ tenant_id: Phase-1 chạy đơn tenant ('bravo_internal'). Trường tenant_id ở đây
được CHẤP NHẬN để tương thích phía gọi nhưng KHÔNG được forward vào rag.ask và KHÔNG
echo lại — /ask trả NGUYÊN dict rag.ask (không thêm field) để giữ đúng ngữ nghĩa lõi.
Isolation đa tenant để Phase sau (cần đổi rag/store, ngoài scope api).
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
import generate as gen
import memory
import provider
import rag
import suggest

app = FastAPI(
    title="Trợ lý nghiệp vụ BRAVO — RAG API",
    description="Cổng HTTP bọc lõi RAG (hỏi-đáp tài liệu help BRAVO công khai, có trích nguồn).",
    version="0.1",
)

# CORS: cho frontend dev (Vite :5173) gọi API :8000. Production phục vụ static cùng origin
# nên không cần — danh sách origin để mặc định cho localhost dev, chỉnh qua ALLOW_ORIGINS nếu cần.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------- Schemas -----------------------------
class AskRequest(BaseModel):
    question: str = Field(..., description="Câu hỏi nghiệp vụ/cấu hình BRAVO.")
    k: Optional[int] = Field(None, description="Số đoạn truy hồi (mặc định config.TOP_K).")
    min_sim: Optional[float] = Field(None, description="Ngưỡng cosine từ chối (mặc định config.MIN_SIM).")
    tenant_id: Optional[str] = Field(None, description="Định danh tenant (Phase-1: chỉ echo lại).")
    chapter: Optional[str] = Field(None, description="Lọc nguồn theo phân hệ/chương (tham số rag.ask).")
    history: Optional[list] = Field(None, description="Lịch sử hội thoại [{role,content}] để viết lại câu follow-up (memory đa lượt, lớp gọi).")
    session_id: Optional[str] = Field(None, description="Định danh phiên (tuỳ chọn, cho client tự quản lý lịch sử).")


class SuggestRequest(BaseModel):
    question: str = Field(..., description="Câu hỏi để sinh câu hỏi liên quan (grounded).")
    k: Optional[int] = Field(None, description="Số đoạn truy hồi (mặc định config.TOP_K).")
    min_sim: Optional[float] = Field(None, description="Ngưỡng cosine (mặc định config.MIN_SIM).")


class GenerateRequest(BaseModel):
    task: str = Field(..., description="Mã tác vụ soạn nháp/tiện ích (xem GET /tasks).")
    input: str = Field(..., description="Yêu cầu / văn bản người dùng nhập.")


class FeedbackRequest(BaseModel):
    question: str = Field(..., description="Câu hỏi liên quan tới phản hồi.")
    rating: str = Field(..., description="Đánh giá, vd 'up' / 'down'.")


# ----------------------------- Endpoints -----------------------------
@app.get("/healthz")
@app.get("/health")
def healthz():
    """Probe nhẹ — KHÔNG gọi LLM/embedding (tránh tốn token), chỉ báo cấu hình hiện hành.
    Đăng ký cả /healthz và /health (Dockerfile HEALTHCHECK dùng /health)."""
    return {
        "status": "ok",
        "provider": f"{config.LLM_PROVIDER}/{config.LLM_MODEL}",
        "embed": f"{config.EMBED_PROVIDER}/{config.EMBED_MODEL}",
        "store": config.VECTOR_STORE,
        "route": provider.route_label(),
    }


@app.post("/ask")
def ask(req: AskRequest):
    """Chuyển tiếp tới rag.ask() và trả NGUYÊN dict kết quả (answer/sources/hits/refused/route/max_sim).
    Nếu có history -> viết lại câu follow-up thành câu độc lập (memory.condense, lớp gọi, có PII pre-check)
    rồi mới truy hồi. Mọi rào chắn an toàn vẫn do rag.ask() đảm nhiệm."""
    q = memory.condense_question(req.history, req.question) if req.history else req.question
    return rag.ask(q, k=req.k, min_sim=req.min_sim, chapter=req.chapter)


@app.post("/suggest")
def suggest_related(req: SuggestRequest):
    """Sinh câu hỏi liên quan GROUNDED (tái dùng suggest.related_questions, có PII pre-check).
    Trả {questions: [...]} — rỗng khi PII chặn / dưới ngưỡng / lỗi (an toàn > số lượng)."""
    return {"questions": suggest.related_questions(req.question, k=req.k, min_sim=req.min_sim)}


@app.post("/generate")
def generate_draft(req: GenerateRequest):
    """Soạn nháp / tiện ích văn phòng (generate.generate). KHÔNG dùng dữ liệu nghiệp vụ —
    chỉ văn bản người dùng nhập; có rào chắn PII trước khi gửi cloud. Trả nguyên dict generate."""
    try:
        return gen.generate(req.task, req.input)
    except ValueError as e:
        return {"error": True, "output": str(e), "task": req.task, "redacted": False, "pii": []}


@app.get("/tasks")
def tasks():
    """Danh mục tác vụ soạn nháp/tiện ích cho frontend dựng menu (nhãn hiển thị + nhóm)."""
    draft = ["soan_email", "jd", "call_script", "interview", "content", "idea"]
    util = ["dich", "grammar", "tom_tat", "excel"]
    return {
        "draft": [{"key": t, "label": gen.TASKS[t][0]} for t in draft],
        "util": [{"key": t, "label": gen.TASKS[t][0]} for t in util],
    }


@app.get("/scoreboard")
def scoreboard():
    """Bảng điểm độ tin cậy (đọc data/eval_results.json nếu có) — biến rào chắn thành hữu hình.
    Trả {available: bool, help?, accounting?} để frontend hiện thẻ điểm hoặc gợi ý chạy eval."""
    rf = config.DATA_DIR / "eval_results.json"
    if not rf.exists():
        return {"available": False}
    try:
        er = json.loads(rf.read_text(encoding="utf-8"))
        return {"available": True, "help": er.get("help"), "accounting": er.get("accounting")}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """Ghi phản hồi vào data/feedback.jsonl. Câu hỏi được REDACT PII bằng rag._redact
    (tái dùng đúng cách của app.py — KHÔNG lưu PII nguyên văn)."""
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.DATA_DIR / "feedback.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "q": rag._redact(req.question),
                "rating": req.rating,
            }, ensure_ascii=False) + "\n")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ----------------------------- Static frontend (SPA) -----------------------------
# Production: phục vụ bản build Vite (frontend/dist) cùng origin → không cần CORS.
# Mount SAU mọi route API để /ask, /docs… không bị nuốt. Bỏ qua nếu chưa build.
_DIST = Path(__file__).parent / "frontend" / "dist"
if _DIST.exists():
    @app.get("/")
    def _index():
        return FileResponse(_DIST / "index.html")

    # assets/ và file tĩnh khác; html=True để mọi path lạ rơi về index.html (SPA fallback).
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")
