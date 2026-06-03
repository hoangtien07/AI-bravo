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
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

import config
import provider
import rag

app = FastAPI(
    title="Trợ lý nghiệp vụ BRAVO — RAG API",
    description="Cổng HTTP bọc lõi RAG (hỏi-đáp tài liệu help BRAVO công khai, có trích nguồn).",
    version="0.1",
)


# ----------------------------- Schemas -----------------------------
class AskRequest(BaseModel):
    question: str = Field(..., description="Câu hỏi nghiệp vụ/cấu hình BRAVO.")
    k: Optional[int] = Field(None, description="Số đoạn truy hồi (mặc định config.TOP_K).")
    min_sim: Optional[float] = Field(None, description="Ngưỡng cosine từ chối (mặc định config.MIN_SIM).")
    tenant_id: Optional[str] = Field(None, description="Định danh tenant (Phase-1: chỉ echo lại).")


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
    Mọi rào chắn an toàn do rag.ask() đảm nhiệm — endpoint không can thiệp ngữ nghĩa."""
    return rag.ask(req.question, k=req.k, min_sim=req.min_sim)


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
