# Dockerfile — đóng gói API "Trợ lý nghiệp vụ BRAVO" (RAG) để self-host.
# KHÔNG nhúng API key / .env / dữ liệu khách vào image. Key cấp lúc chạy qua biến môi
# trường (env_file / secret), corpus đã ingest mount vào /app/data (xem docs/deploy.md).
#
# Image này phục vụ tầng API (uvicorn api:app). Streamlit (app.py) là UI demo riêng,
# không bắt buộc trong production — nếu cần, chạy bằng lệnh override (xem docs/deploy.md).

FROM python:3.12-slim

# - PYTHONUNBUFFERED: log ra stdout ngay (tiện theo dõi container/k8s).
# - PIP_NO_CACHE_DIR: image gọn hơn.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build tools cho gói native (chroma-hnswlib khi VECTOR_STORE=chroma embedded; rank-bm25 thuần Python).
# Để image nhẹ: cài rồi gỡ trong cùng layer. Nếu chỉ dùng VECTOR_STORE=numpy hoặc chroma SERVER
# (HttpClient) thì có thể bỏ khối này — xem ghi chú docs/deploy.md.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cài dependency trước (tận dụng cache layer khi chỉ đổi code).
COPY requirements.txt .
# uvicorn + fastapi cho tầng API (api.py do pha build:api tạo; KHÔNG có trong requirements.txt
# Phase-1 nên khai báo tường minh ở đây để tránh sửa requirements.txt theo ràng buộc pha Build).
RUN pip install -r requirements.txt \
    && pip install "fastapi>=0.111" "uvicorn[standard]>=0.30" \
    && apt-get purge -y --auto-remove build-essential 2>/dev/null || true

# Chạy bằng user thường (không root) cho an toàn.
RUN useradd --create-home --uid 10001 appuser

# Copy mã nguồn. .dockerignore loại .env, data/, .venv… (xem .dockerignore) để KHÔNG
# nhúng key/dữ liệu vào image. Corpus đã ingest sẽ mount vào /app/data lúc chạy.
COPY . .

# Thư mục dữ liệu runtime (vector store numpy/chroma-embedded + audit log) — mount volume vào đây.
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck nhẹ: gọi endpoint /health của api (api.py cần expose GET /health).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200 else 1)" || exit 1

# api:app = đối tượng FastAPI tên `app` trong api.py (pha build:api tạo).
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
