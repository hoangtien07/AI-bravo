"""
rerank.py — Rerank tùy chọn bằng cross-encoder (mặc định bge-reranker-v2-m3).

Bật bằng RERANK_ENABLED=1 (cần `pip install sentence-transformers` + tải model ~600MB).
Lazy + an toàn: nếu thiếu model/thư viện, rag.py sẽ bỏ qua và dùng thứ tự RRF.
"""
import functools

import config


@functools.lru_cache(maxsize=1)
def _model():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(config.RERANK_MODEL)


def rerank(query, ids, info):
    """Sắp xếp lại danh sách id theo điểm liên quan cross-encoder (giảm dần)."""
    model = _model()
    pairs = [(query, (info.get(i, ("", {}))[0] or "")) for i in ids]
    scores = model.predict(pairs)
    return [i for i, _ in sorted(zip(ids, scores), key=lambda kv: -float(kv[1]))]
