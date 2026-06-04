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
    if backend == "numpy":
        return _NumpyStore(collection)
    if backend == "qdrant":
        return _QdrantStore(collection)
    return _ChromaStore(collection)


# ----------------------------- Qdrant (production, Docker) -----------------------------
# Namespace cố định để map id chuỗi BRAVO ('tenant__dX__cY') -> UUIDv5 (Qdrant chỉ nhận int/UUID).
_QDRANT_NS = __import__("uuid").UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


class _QdrantStore:
    def __init__(self, collection):
        from qdrant_client import QdrantClient
        self.collection = collection
        self._client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY,
                                    prefer_grpc=config.QDRANT_PREFER_GRPC)
        self._ready = self._client.collection_exists(collection)

    def _ensure(self, dim):
        from qdrant_client import models
        if self._client.collection_exists(self.collection):
            self._ready = True
            return
        self._client.create_collection(
            self.collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
        # Payload index cho field lọc nóng (tenant/category/...) — rẻ, đặt sẵn cho multi-tenant.
        for f in ("tenant_id", "data_class", "category", "file_group", "version"):
            try:
                self._client.create_payload_index(self.collection, field_name=f,
                                                  field_schema=models.PayloadSchemaType.KEYWORD)
            except Exception:
                pass
        self._ready = True

    @staticmethod
    def _pid(str_id):
        import uuid
        return str(uuid.uuid5(_QDRANT_NS, str_id))

    def reset(self):
        try:
            self._client.delete_collection(self.collection)
        except Exception:
            pass
        self._ready = False

    def upsert(self, ids, embeddings, documents, metadatas):
        from qdrant_client import models
        emb = [list(map(float, e)) for e in embeddings]
        if emb:
            self._ensure(len(emb[0]))                 # DIM lấy từ vector thật (tránh hardcode sai)
        points = []
        for i, v, doc, meta in zip(ids, emb, documents, metadatas):
            payload = dict(meta or {}); payload["_id"] = i; payload["document"] = doc
            points.append(models.PointStruct(id=self._pid(i), vector=v, payload=payload))
        for s in range(0, len(points), 256):           # batch tránh payload quá lớn
            self._client.upsert(self.collection, points=points[s:s + 256], wait=True)

    def count(self):
        if not self._ready:
            return 0
        return self._client.count(self.collection, exact=True).count

    def all(self):
        if not self._ready:
            return [], [], []
        ids, docs, metas, offset = [], [], [], None
        while True:
            pts, offset = self._client.scroll(self.collection, limit=512, offset=offset,
                                              with_payload=True, with_vectors=False)
            for p in pts:
                pl = p.payload or {}
                ids.append(pl.get("_id"))
                docs.append(pl.get("document", ""))
                metas.append({k: v for k, v in pl.items() if k not in ("_id", "document")})
            if offset is None:
                break
        return ids, docs, metas

    def query(self, vector, k, where=None):
        from qdrant_client import models
        if not self._ready:
            return []
        qfilter = None
        if where:
            qfilter = models.Filter(must=[
                models.FieldCondition(key=kk, match=models.MatchValue(value=vv))
                for kk, vv in where.items()])
        res = self._client.query_points(self.collection, query=list(map(float, vector)),
                                        limit=k, query_filter=qfilter, with_payload=True)
        out = []
        for p in res.points:
            pl = p.payload or {}
            meta = {kk: vv for kk, vv in pl.items() if kk not in ("_id", "document")}
            out.append((pl.get("_id"), pl.get("document", ""), meta, float(p.score)))  # COSINE: cao=tốt
        return out

    def delete(self, where):
        """Xóa theo metadata (vd {'category': 'phong_X'}) — vòng đời tri thức."""
        from qdrant_client import models
        if not where:
            return
        self._client.delete(self.collection, points_selector=models.FilterSelector(
            filter=models.Filter(must=[
                models.FieldCondition(key=kk, match=models.MatchValue(value=vv))
                for kk, vv in where.items()])))


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

    def delete(self, where):
        if where:
            self._col.delete(where=where)

    def all(self):
        got = self._col.get(include=["documents", "metadatas"])
        return got["ids"], got["documents"], got["metadatas"]

    def query(self, vector, k, where=None):
        # where (tùy chọn, OPT-IN): lọc metadata phía Chroma. None = không lọc (mặc định).
        kw = {"where": where} if where else {}
        res = self._col.query(query_embeddings=[list(vector)], n_results=k,
                              include=["documents", "metadatas", "distances"], **kw)
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

    def delete(self, where):
        """Xóa item có metadata khớp đủ where (equality). Trả số chunk đã xóa. Ghi lại đĩa."""
        self._load()
        if not where or not self._ids:
            return 0
        keep = [k for k, m in enumerate(self._metas)
                if not all((m or {}).get(kk) == vv for kk, vv in where.items())]
        removed = len(self._ids) - len(keep)
        if not removed:
            return 0
        self._ids = [self._ids[k] for k in keep]
        self._docs = [self._docs[k] for k in keep]
        self._metas = [self._metas[k] for k in keep]
        self._mat = self._mat[keep] if keep else np.zeros((0, 1), dtype="float32")
        self.dir.mkdir(parents=True, exist_ok=True)
        np.save(self.vp, self._mat)
        with open(self.mp, "w", encoding="utf-8") as f:
            for i, d, m in zip(self._ids, self._docs, self._metas):
                f.write(json.dumps({"id": i, "doc": d, "meta": m}, ensure_ascii=False) + "\n")
        return removed

    def all(self):
        self._load(); return self._ids, self._docs, self._metas

    def query(self, vector, k, where=None):
        self._load()
        if not self._ids:
            return []
        q = np.asarray(vector, dtype="float32")
        q = q / (np.linalg.norm(q) or 1.0)
        sims = self._normalize(self._mat) @ q
        order = np.argsort(-sims)
        # where (tùy chọn, OPT-IN): chỉ giữ item có metadata khớp đủ mọi cặp key/value trong dict.
        # None = không lọc (mặc định) -> giữ nguyên hành vi cũ. So khớp bằng == (equality).
        if where:
            def _match(meta):
                meta = meta or {}
                return all(meta.get(key) == val for key, val in where.items())
            order = [i for i in order if _match(self._metas[i])]
        order = order[:k]
        return [(self._ids[i], self._docs[i], self._metas[i], float(sims[i])) for i in order]
