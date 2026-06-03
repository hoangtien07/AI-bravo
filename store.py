"""
store.py — Lớp vector store pluggable (mặc định Chroma; fallback numpy).

    config.VECTOR_STORE = "chroma"  (mặc định, theo lựa chọn dự án)
                        | "numpy"   (fallback brute-force cosine — không cần native/build)

Interface chung (Phase-3 có thể thêm backend pgvector / SQL Server 2025 VECTOR):
    Store(collection).upsert(ids, embeddings, documents, metadatas)
    Store(collection).query(vector, k) -> [(id, doc, meta, cosine_sim), ...]   # sim giảm dần
    Store(collection).all() -> (ids, docs, metas)
    Store(collection).reset()

GHI CHÚ NỀN TẢNG (Windows): chromadb 1.x (Rust) có thể segfault; bản 0.5.x ổn định nhưng cần
C++ Build Tools để biên dịch chroma-hnswlib. Nếu Chroma chưa chạy được, đặt VECTOR_STORE=numpy.
"""
import json
import shutil

import numpy as np

import config


def Store(collection):
    backend = getattr(config, "VECTOR_STORE", "chroma").lower()
    return _NumpyStore(collection) if backend == "numpy" else _ChromaStore(collection)


# ----------------------------- Chroma (mặc định) -----------------------------
class _ChromaStore:
    def __init__(self, collection):
        import chromadb
        self.collection = collection
        self._client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        self._col = self._client.get_or_create_collection(
            collection, metadata={"hnsw:space": "cosine"})

    def reset(self):
        try:
            self._client.delete_collection(self.collection)
        except Exception:
            pass
        self._col = self._client.get_or_create_collection(
            self.collection, metadata={"hnsw:space": "cosine"})

    def upsert(self, ids, embeddings, documents, metadatas):
        self._col.upsert(ids=ids, embeddings=embeddings,
                         documents=documents, metadatas=metadatas)

    def count(self):
        return self._col.count()

    def all(self):
        got = self._col.get(include=["documents", "metadatas"])
        return got["ids"], got["documents"], got["metadatas"]

    def query(self, vector, k):
        res = self._col.query(query_embeddings=[list(vector)], n_results=k,
                              include=["documents", "metadatas", "distances"])
        out = []
        for i, doc, meta, dist in zip(res["ids"][0], res["documents"][0],
                                      res["metadatas"][0], res["distances"][0]):
            out.append((i, doc, meta, 1.0 - float(dist)))   # cosine space: sim = 1 - distance
        return out


# ----------------------------- numpy (fallback) -----------------------------
class _NumpyStore:
    def __init__(self, collection):
        self.collection = collection
        self.dir = config.CHROMA_DIR / ("numpy__" + collection)
        self.vp = self.dir / "vectors.npy"
        self.mp = self.dir / "items.jsonl"
        self._ids = self._docs = self._metas = self._mat = None

    def reset(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        self._ids = self._docs = self._metas = self._mat = None

    def _load(self):
        if self._ids is not None:
            return
        if self.vp.exists() and self.mp.exists():
            self._mat = np.load(self.vp).astype("float32")
            ids, docs, metas = [], [], []
            for line in open(self.mp, encoding="utf-8"):
                o = json.loads(line)
                ids.append(o["id"]); docs.append(o["doc"]); metas.append(o["meta"])
            self._ids, self._docs, self._metas = ids, docs, metas
        else:
            self._ids, self._docs, self._metas = [], [], []
            self._mat = np.zeros((0, 1), dtype="float32")

    @staticmethod
    def _normalize(mat):
        n = np.linalg.norm(mat, axis=1, keepdims=True)
        n[n == 0] = 1.0
        return mat / n

    def upsert(self, ids, embeddings, documents, metadatas):
        self._load()
        cur = {i: (self._docs[k], self._metas[k], self._mat[k])
               for k, i in enumerate(self._ids)}
        emb = np.asarray(embeddings, dtype="float32")
        for j, i in enumerate(ids):
            cur[i] = (documents[j], metadatas[j], emb[j])
        ids2 = list(cur.keys())
        mat2 = np.vstack([cur[i][2] for i in ids2]).astype("float32")
        docs2 = [cur[i][0] for i in ids2]
        metas2 = [cur[i][1] for i in ids2]
        self.dir.mkdir(parents=True, exist_ok=True)
        np.save(self.vp, mat2)
        with open(self.mp, "w", encoding="utf-8") as f:
            for i, d, m in zip(ids2, docs2, metas2):
                f.write(json.dumps({"id": i, "doc": d, "meta": m}, ensure_ascii=False) + "\n")
        self._ids, self._docs, self._metas, self._mat = ids2, docs2, metas2, mat2

    def count(self):
        self._load(); return len(self._ids)

    def all(self):
        self._load(); return self._ids, self._docs, self._metas

    def query(self, vector, k):
        self._load()
        if not self._ids:
            return []
        q = np.asarray(vector, dtype="float32")
        q = q / (np.linalg.norm(q) or 1.0)
        sims = self._normalize(self._mat) @ q
        order = np.argsort(-sims)[:k]
        return [(self._ids[i], self._docs[i], self._metas[i], float(sims[i])) for i in order]
