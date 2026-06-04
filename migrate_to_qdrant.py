"""
migrate_to_qdrant.py — Chuyển store numpy SẴN CÓ sang Qdrant mà KHÔNG re-embed (0 token).

Đọc thẳng data/chroma/numpy__<collection>/{vectors.npy, items.jsonl} -> upsert vào Qdrant.
Nhân tiện BƠM metadata vòng đời (category, file_group) vào chunk cũ (vốn thiếu) để hỗ trợ
xóa-theo-category. An toàn: chỉ ĐỌC numpy (giữ nguyên), chỉ GHI sang Qdrant.

Chạy:  VECTOR_STORE=qdrant .venv/Scripts/python.exe migrate_to_qdrant.py
"""
import json
import os
import sys

os.environ["VECTOR_STORE"] = "qdrant"          # đảm bảo Store() trả _QdrantStore (set TRƯỚC import config)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

import config
import store


def _category(meta):
    if meta.get("category"):
        return meta["category"]
    dc = meta.get("data_class", "")
    if dc == "public_regulation":
        return "quy_dinh"
    if "seed://" in str(meta.get("url", "")):
        return "minh_hoa"
    return "help"


def main():
    col = config.COLLECTION
    ndir = config.CHROMA_DIR / ("numpy__" + col)
    vp, mp = ndir / "vectors.npy", ndir / "items.jsonl"
    if not (vp.exists() and mp.exists()):
        print(f"[!] Không thấy numpy store tại {ndir}. Chạy ingest numpy trước.")
        sys.exit(1)

    mat = np.load(vp)
    ids, docs, metas = [], [], []
    for line in open(mp, encoding="utf-8"):
        o = json.loads(line)
        m = o.get("meta") or {}
        m.setdefault("category", _category(m))                       # bơm vòng đời
        m.setdefault("file_group", m.get("url") or m.get("source") or m.get("path") or "?")
        ids.append(o["id"]); docs.append(o["doc"]); metas.append(m)
    assert len(ids) == mat.shape[0], f"lệch: {len(ids)} items vs {mat.shape[0]} vectors"
    print(f"Đọc {len(ids)} chunk × {mat.shape[1]} dims từ numpy -> Qdrant '{col}' ({config.QDRANT_URL})")

    qs = store.Store(col)
    qs.reset()
    qs.upsert(ids, [mat[i].tolist() for i in range(len(ids))], docs, metas)
    print(f"Đã migrate. Qdrant count = {qs.count()} (kỳ vọng {len(ids)}).")


if __name__ == "__main__":
    main()
