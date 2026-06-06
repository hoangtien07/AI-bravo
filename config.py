# config.py — Cấu hình tập trung cho POC "Trợ lý nghiệp vụ BRAVO" (RAG)
# Flagship seminar thử việc: hỏi-đáp tiếng Việt trên tài liệu help, có trích nguồn.
import os
import re
from pathlib import Path

# Nạp .env NGAY ĐẦU (trước khi đọc os.environ) để LLM_PROVIDER/EMBED_PROVIDER/VECTOR_STORE/key
# từ .env có hiệu lực. (provider.py cũng gọi load_dotenv nhưng config import trước nên cần ở đây.)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
SEED_DIR = DATA_DIR / "seed"          # tài liệu MINH HOẠ curated cho demo/eval
REG_DIR = DATA_DIR / "regulations"    # KB quy định CÔNG KHAI (TT200/TT99 — hệ thống tài khoản)
CHROMA_DIR = DATA_DIR / "chroma"
AUDIT_LOG = DATA_DIR / "audit_log.jsonl"
RAW_FILE = RAW_DIR / "pages.jsonl"

# --- Nhà cung cấp model (pluggable: ollama self-host | gemini | openai cloud) ---
# Mặc định CLOUD theo lựa chọn dự án (đã có API key); đặt LLM_PROVIDER=ollama để chạy self-host.
# Key đọc từ biến môi trường trong provider.py (GEMINI_API_KEY / OPENAI_API_KEY).
# Default = openai cho KHỚP store đã ingest (text-embedding-3-large) -> tránh footgun đổi
# embedder làm lệch tên collection. Đổi sang ollama/gemini qua .env khi cần.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").lower()
EMBED_PROVIDER = os.environ.get("EMBED_PROVIDER", "openai").lower()

# Tránh hardcode model có thể bị "sunset" (vd Gemini 2.0 Flash hết hạn 01/06/2026).
LLM_MODELS = {"ollama": "qwen3:8b", "gemini": "gemini-2.5-flash", "openai": "gpt-4.1-mini"}
EMBED_MODELS = {"ollama": "bge-m3", "gemini": "gemini-embedding-001", "openai": "text-embedding-3-large"}
LLM_MODEL = os.environ.get("LLM_MODEL", LLM_MODELS.get(LLM_PROVIDER, "gemini-2.5-flash"))
EMBED_MODEL = os.environ.get("EMBED_MODEL", EMBED_MODELS.get(EMBED_PROVIDER, "gemini-embedding-001"))


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# --- Tham số RAG ---
# Collection KHOÁ theo embed provider+model: đổi embedding => chiều vector khác => KHÔNG trộn
# không gian vector; mỗi embedder có collection riêng, buộc re-ingest khi đổi.
COLLECTION_BASE = "bravo_help"
COLLECTION = f"{COLLECTION_BASE}__{_slug(EMBED_PROVIDER)}__{_slug(EMBED_MODEL)}"

# Vector store: "numpy" (fallback, không cần native) | "chroma" | "qdrant" (Docker, production)
VECTOR_STORE = os.environ.get("VECTOR_STORE", "chroma").lower()
# Qdrant (chạy Docker local: docker run -p 6333:6333 qdrant/qdrant). API key None khi local.
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY") or None
QDRANT_PREFER_GRPC = os.environ.get("QDRANT_PREFER_GRPC", "0") == "1"

TOP_K = 4                    # số đoạn đưa vào ngữ cảnh
RETRIEVE_CANDIDATES = 20     # số ứng viên truy hồi trước khi RRF/rerank

# Ngưỡng cosine cho RÀO CHẮN TỪ CHỐI (guardrail 2). Mỗi embedder có thang cosine khác nhau
# => ngưỡng riêng theo provider; [CẦN TINH CHỈNH bằng eval trên dữ liệu thật].
# 2 tầng (đo trên corpus thật: câu tốt ~0.55–0.66, mơ hồ ~0.50, offtopic <0.40):
#   < SCOPE_FLOOR        -> ngoài phạm vi (từ chối kiểu "chỉ hỗ trợ BRAVO")
#   SCOPE_FLOOR..MIN_SIM -> trong miền nhưng không thấy -> gợi ý nêu rõ phân hệ
#   >= MIN_SIM           -> trả lời.  (Ngưỡng KHÔNG tách được "sai-mà-tự-tin" ~0.50
#   nằm kẹp giữa câu tốt -> dùng kèm INTENT GATE ở rag.py, xem _classify_intent.)
MIN_SIM_BY_EMBED = {"ollama": 0.35, "gemini": 0.55, "openai": 0.42}
MIN_SIM = float(os.environ.get("MIN_SIM", MIN_SIM_BY_EMBED.get(EMBED_PROVIDER, 0.35)))
SCOPE_FLOOR_BY_EMBED = {"ollama": 0.28, "gemini": 0.45, "openai": 0.38}
SCOPE_FLOOR = float(os.environ.get("SCOPE_FLOOR", SCOPE_FLOOR_BY_EMBED.get(EMBED_PROVIDER, 0.30)))

# Hybrid retrieval (ưu tiên chất lượng): BM25 (sparse) + vector (dense) hợp nhất bằng RRF.
HYBRID_ENABLED = os.environ.get("HYBRID_ENABLED", "1") == "1"
RRF_K = 60
# Rerank tùy chọn (cross-encoder); cần model + sentence-transformers, mặc định TẮT (bật khi sẵn sàng).
RERANK_ENABLED = os.environ.get("RERANK_ENABLED", "0") == "1"
RERANK_MODEL = os.environ.get("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_CANDIDATES = 30

# Chunk structure-aware: trang ngắn = 1 chunk nguyên; trang dài cắt theo đoạn.
CHUNK_MAX_CHARS = 1200
CHUNK_OVERLAP = 150
CHUNK_SIZE = 1000           # (giữ cho tương thích cũ)

# Câu từ chối phân hoá theo tình huống (phản hồi khách: 1 câu "một cỡ" đọc vô duyên).
REFUSAL = ("Em chưa tìm thấy nội dung này trong tài liệu hướng dẫn BRAVO. "
           "Anh/chị thử nêu rõ phân hệ/chức năng hoặc từ khoá khác giúp em "
           "(vd: công nợ, định khoản, lập hoá đơn, tồn kho…).")
REFUSAL_SCOPE = ("Dạ em là trợ lý nghiệp vụ BRAVO, chỉ hỗ trợ tra cứu và hướng dẫn "
                 "trong phần mềm BRAVO nên chưa hỗ trợ nội dung này được ạ.")
GREETING_MSG = ("Dạ em chào anh/chị! Em là trợ lý nghiệp vụ BRAVO, hỗ trợ tra cứu hướng dẫn "
                "và nghiệp vụ trong phần mềm. Anh/chị đang cần hỏi về phân hệ nào ạ — "
                "bán hàng, mua hàng, kho, công nợ, kế toán…?")
COMPLAINT_MSG = ("Dạ để hỗ trợ đúng, anh/chị cho em biết thêm: (1) đang gặp trục trặc ở "
                 "phân hệ/chức năng nào (vd: bán hàng, nhập chứng từ, in báo cáo…)? "
                 "(2) thông báo lỗi hiện trên màn hình là gì ạ? Em sẽ tra đúng phần hướng dẫn xử lý.")

# --- Crawl (CHỈ tài liệu CÔNG KHAI trên bravo.com.vn — KHÔNG đăng nhập, KHÔNG dữ liệu khách) ---
CRAWL_DOMAIN = "www.bravo.com.vn"
CRAWL_SEEDS = [
    "https://www.bravo.com.vn/kien-thuc/",
    "https://www.bravo.com.vn/bravo/bravo-erp-vn/",
]
# chỉ đi theo link có path bắt đầu bằng một trong các prefix này
CRAWL_ALLOW_PREFIXES = ("/kien-thuc/", "/bravo/")
CRAWL_MAX_PAGES = 80
CRAWL_DELAY_SEC = 1.0        # lịch sự với server: nghỉ giữa các request
CRAWL_TIMEOUT = 15
USER_AGENT = "BravoRAG-POC/0.1 (internal probation seminar demo)"
MIN_PAGE_CHARS = 400         # bỏ trang quá ngắn (menu/landing)

# --- Crawl help BRAVO 10 (help.bravo.com.vn — SPA Angular, render bằng Playwright) ---
# Trang là SPA: nội dung tải qua JS. Ta KHÔNG trích/dùng credential thủ công — chỉ mở
# trang công khai bằng trình duyệt thật (headless) như một khách bình thường rồi đọc DOM
# đã render. TOC seed lấy từ data/bravo10_toc.json (do người dùng export công khai).
HELP_DOMAIN = "help.bravo.com.vn"
HELP_TOC_FILE = DATA_DIR / "bravo10_toc.json"
HELP_RAW_FILE = RAW_DIR / "bravo10_help.jsonl"   # mỗi dòng: {"url","title","path","text"}
HELP_CONTENT_SELECTOR = ".article-main-wrapper"   # vùng bài viết (cả trang giàu lẫn trang lá)
HELP_MIN_CHARS = 120                               # trang help có thể rất ngắn (vd "Giới thiệu chung")
HELP_MAX_PAGES = 600                               # đủ rộng để BFS rút cạn toàn bộ cây tài liệu
HELP_DELAY_SEC = 1.0
HELP_NAV_TIMEOUT_MS = 45000
HELP_SELECTOR_TIMEOUT_MS = 15000                   # poll tối đa cho .article-content
HELP_RENDER_WAIT_MS = 1500                         # chờ thêm để các khối còn lại render
