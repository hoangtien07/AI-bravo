"""
provider.py — Lớp gateway LLM/embedding pluggable (điểm chèn DUY NHẤT cho pivot cloud).

Đổi nhà cung cấp bằng config/biến môi trường, KHÔNG sửa rag.py/ingest.py:
    LLM_PROVIDER   = ollama | gemini | openai      (sinh câu trả lời)
    EMBED_PROVIDER = ollama | gemini | openai      (tạo embedding)
API key đọc từ biến môi trường (.env) — KHÔNG hardcode, KHÔNG commit:
    GEMINI_API_KEY (hoặc GOOGLE_API_KEY) · OPENAI_API_KEY

Hai hàm công khai:
    embed_texts(texts, task="document"|"query") -> list[vector]
    chat(system, user) -> str

LƯU Ý CHỦ QUYỀN DỮ LIỆU: provider cloud (gemini/openai) GỬI nội dung ra nước ngoài —
cả ở bước embed lẫn chat. Chỉ dùng cho dữ liệu CÔNG KHAI; câu hỏi đi qua rào chắn PII
ở rag.py trước khi tới đây.
"""
import functools
import os
import time

import config


def _with_retry(fn, tries=6, base=2.0):
    """Gọi fn() với backoff khi gặp 429/RESOURCE_EXHAUSTED/quota (free tier hay dính)."""
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:
            msg = str(e).lower()
            transient = any(s in msg for s in
                            ("429", "resource_exhausted", "rate", "quota", "exhausted", "503", "overloaded"))
            if not transient or attempt == tries - 1:
                raise
            wait = base * (2 ** attempt)
            # tôn trọng retryDelay nếu API gợi ý
            import re as _re
            m = _re.search(r"retry.{0,15}?(\d+(?:\.\d+)?)s", msg)
            if m:
                wait = max(wait, float(m.group(1)) + 1)
            time.sleep(min(wait, 60))

try:                       # nạp .env nếu có (không bắt buộc)
    from dotenv import load_dotenv
    load_dotenv(config.BASE_DIR / ".env")
except Exception:
    pass

CLOUD_PROVIDERS = {"gemini", "openai"}


def is_cloud() -> bool:
    """True nếu BẤT KỲ bước nào (embed hoặc chat) đi ra cloud -> câu hỏi rời máy."""
    return (config.LLM_PROVIDER in CLOUD_PROVIDERS
            or config.EMBED_PROVIDER in CLOUD_PROVIDERS)


def route_label() -> str:
    return "cloud" if is_cloud() else "self_host"


# ----------------------- clients (lazy, cache) -----------------------
@functools.lru_cache(maxsize=1)
def _gemini():
    from google import genai
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("Thiếu GEMINI_API_KEY/GOOGLE_API_KEY trong môi trường (.env).")
    return genai.Client(api_key=key)


@functools.lru_cache(maxsize=1)
def _openai():
    from openai import OpenAI
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Thiếu OPENAI_API_KEY trong môi trường (.env).")
    return OpenAI(api_key=key)


# ----------------------- embeddings -----------------------
def embed_texts(texts, task="document"):
    """task: 'query' cho câu hỏi, 'document' cho chunk khi ingest (ảnh hưởng chất lượng Gemini)."""
    provider = config.EMBED_PROVIDER
    model = config.EMBED_MODEL

    if provider == "ollama":
        import ollama
        return [ollama.embeddings(model=model, prompt=t)["embedding"] for t in texts]

    if provider == "gemini":
        from google.genai import types
        tt = "RETRIEVAL_QUERY" if task == "query" else "RETRIEVAL_DOCUMENT"
        res = _with_retry(lambda: _gemini().models.embed_content(
            model=model, contents=list(texts),
            config=types.EmbedContentConfig(task_type=tt)))
        return [list(e.values) for e in res.embeddings]

    if provider == "openai":
        res = _with_retry(lambda: _openai().embeddings.create(model=model, input=list(texts)))
        return [d.embedding for d in res.data]

    raise ValueError(f"EMBED_PROVIDER không hỗ trợ: {provider}")


# ----------------------- chat / generation -----------------------
def chat(system: str, user: str) -> str:
    provider = config.LLM_PROVIDER
    model = config.LLM_MODEL

    if provider == "ollama":
        import ollama
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try:
            out = ollama.chat(model=model, messages=msgs, think=False)
        except TypeError:                      # bản ollama cũ chưa có tham số think
            out = ollama.chat(model=model, messages=msgs)
        return out["message"]["content"]

    if provider == "gemini":
        from google.genai import types
        out = _with_retry(lambda: _gemini().models.generate_content(
            model=model, contents=user,
            config=types.GenerateContentConfig(system_instruction=system, temperature=0.2)))
        return out.text or ""

    if provider == "openai":
        out = _with_retry(lambda: _openai().chat.completions.create(
            model=model, temperature=0.2,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}]))
        return out.choices[0].message.content or ""

    raise ValueError(f"LLM_PROVIDER không hỗ trợ: {provider}")


def chat_stream(system: str, user: str):
    """Như chat() nhưng STREAM từng đoạn text (yield str) -> UI hiện chữ chạy dần, giảm
    cảm giác chờ (phản hồi khách: chậm 4–11s). Nếu provider/SDK lỗi stream -> fallback chat()
    1 lần (yield trọn câu) để không vỡ luồng."""
    provider = config.LLM_PROVIDER
    model = config.LLM_MODEL
    try:
        if provider == "openai":
            stream = _openai().chat.completions.create(
                model=model, temperature=0.2, stream=True,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}])
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
            return

        if provider == "gemini":
            from google.genai import types
            for chunk in _gemini().models.generate_content_stream(
                    model=model, contents=user,
                    config=types.GenerateContentConfig(system_instruction=system, temperature=0.2)):
                if getattr(chunk, "text", None):
                    yield chunk.text
            return

        if provider == "ollama":
            import ollama
            msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            try:
                stream = ollama.chat(model=model, messages=msgs, think=False, stream=True)
            except TypeError:
                stream = ollama.chat(model=model, messages=msgs, stream=True)
            for part in stream:
                piece = (part.get("message") or {}).get("content")
                if piece:
                    yield piece
            return
    except Exception:
        pass
    # Fallback: không stream được -> trả nguyên câu (vẫn chạy, chỉ mất hiệu ứng chữ chạy).
    yield chat(system, user)
