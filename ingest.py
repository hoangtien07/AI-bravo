"""
ingest.py — Cắt chunk structure-aware + tạo embedding (qua provider gateway) + nạp Chroma.

Chạy:   python ingest.py            # nạp HELP BRAVO 10 (bravo10_help.jsonl) nếu có
        python ingest.py --seed     # nạp tài liệu MINH HOẠ từ data/seed/*.md
        python ingest.py --sample   # nạp dữ liệu inline MINH HOẠ (smoke test nhanh)
        python ingest.py --reset     # xoá sạch collection (của embed model hiện tại) rồi nạp lại

Embedding đi qua provider.py: EMBED_PROVIDER = ollama (cần Ollama+bge-m3) | gemini | openai
(cần API key trong .env). Collection được khoá theo embed model -> đổi embedder buộc nạp lại.
"""
import json
import sys

import config
import provider
import store

# Dữ liệu MINH HOẠ (illustrative mock) — KHÔNG phải nội dung help thật của BRAVO.
SAMPLE = [
    {"url": "mock://help_TSCD", "title": "[MINH HOẠ] Khấu hao TSCĐ",
     "text": "Phân hệ Tài sản cố định: khai báo phương pháp khấu hao (đường thẳng hoặc khấu hao nhanh) "
             "tại Danh mục TSCĐ. Chứng từ tính khấu hao chạy cuối kỳ sẽ sinh bút toán "
             "Nợ 627/641/642 / Có 214 tuỳ bộ phận sử dụng."},
    {"url": "mock://help_TT99", "title": "[MINH HOẠ] TT99/2025",
     "text": "Thông tư 99/2025/TT-BTC hiệu lực 01/01/2026 thay thế Thông tư 200, hệ thống 71 tài khoản "
             "cấp 1. Khi nâng cấp cần rà soát ánh xạ tài khoản từ TT200 sang TT99/2025."},
    {"url": "mock://help_congno", "title": "[MINH HOẠ] Công nợ phải thu",
     "text": "Phân hệ công nợ theo dõi công nợ phải thu/phải trả theo từng đối tượng khách hàng/nhà cung cấp. "
             "Báo cáo tuổi nợ giúp phân loại công nợ theo số ngày quá hạn."},
]


import re


def _split_paragraphs(text: str):
    """Tách theo ranh giới đoạn (dòng trống). Crawler lưu inner_text nên không còn heading
    HTML đáng tin -> cắt theo đoạn là tín hiệu cấu trúc tốt nhất còn lại."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paras or ([text.strip()] if text.strip() else [])


def chunk_doc(text: str, path: str, max_chars: int, overlap: int):
    """Structure-aware: gộp các đoạn tới ~max_chars; đoạn quá dài thì cắt cửa sổ trượt.
    Prepend breadcrumb `path` vào đầu mỗi chunk (contextual retrieval rẻ tiền)."""
    chunks, cur = [], ""
    for p in _split_paragraphs(text):
        if len(p) > max_chars:                      # đoạn dài bất thường -> cắt trượt
            if cur:
                chunks.append(cur); cur = ""
            step = max(1, max_chars - overlap)
            for s in range(0, len(p), step):
                chunks.append(p[s:s + max_chars])
        elif cur and len(cur) + 2 + len(p) > max_chars:
            chunks.append(cur); cur = p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    prefix = f"[{path}]\n" if path else ""           # ngữ cảnh breadcrumb cho mỗi chunk
    return [prefix + c for c in chunks]


# Tương thích ngược (eval/test cũ có thể gọi): cửa sổ trượt theo ký tự.
def chunk_text(text: str, size: int, overlap: int):
    text = " ".join(text.split())
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks, start, step = [], 0, max(1, size - overlap)
    while start < len(text):
        chunks.append(text[start:start + size]); start += step
    return chunks


def load_seed():
    """Đọc tài liệu MINH HOẠ curated từ data/seed/*.md."""
    rows = []
    if not config.SEED_DIR.exists():
        return rows
    for p in sorted(config.SEED_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        title = next((ln.lstrip("# ").strip() for ln in text.splitlines()
                      if ln.startswith("#")), p.stem)
        rows.append({"url": f"seed://{p.name}", "title": title, "text": text})
    return rows


def main():
    if "--sample" in sys.argv:
        rows = SAMPLE
        print("Nguồn: dữ liệu inline MINH HOẠ (--sample).")
    elif "--seed" in sys.argv:
        rows = load_seed()
        print(f"Nguồn: seed {config.SEED_DIR} ({len(rows)} tài liệu MINH HOẠ).")
        if not rows:
            print(f"[!] Không có file .md trong {config.SEED_DIR}.")
            sys.exit(1)
    elif config.HELP_RAW_FILE.exists():
        rows = [json.loads(line) for line in open(config.HELP_RAW_FILE, encoding="utf-8")]
        print(f"Nguồn: help BRAVO 10 {config.HELP_RAW_FILE} ({len(rows)} trang).")
    elif config.RAW_FILE.exists():
        rows = [json.loads(line) for line in open(config.RAW_FILE, encoding="utf-8")]
        print(f"Nguồn: tài liệu đã crawl {config.RAW_FILE} ({len(rows)} trang).")
    else:
        rows = load_seed()
        if rows:
            print(f"Nguồn (mặc định): seed {config.SEED_DIR} ({len(rows)} tài liệu MINH HOẠ). "
                  "Crawl web thật bằng `python crawl_bravo_help.py`.")
        else:
            print("[!] Chưa có dữ liệu. Chạy `python crawl_bravo_help.py`, "
                  "hoặc `python ingest.py --seed`, hoặc `--sample`.")
            sys.exit(1)

    print(f"Embedding qua: {config.EMBED_PROVIDER} / {config.EMBED_MODEL}  "
          f"-> collection '{config.COLLECTION}'")

    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    col = store.Store(config.COLLECTION)              # vector store cục bộ (numpy cosine)
    if "--reset" in sys.argv:                         # chỉ xoá store CỦA embed model này
        col.reset()
        print(f"[reset] đã xoá store '{config.COLLECTION}'.")

    # Cắt chunk + dựng metadata (chưa embed)
    tenant_id, data_class = "bravo_internal", "public_help"
    ids, docs, metas = [], [], []
    for di, row in enumerate(rows):
        path = row.get("path") or row.get("title") or ""
        chapter = (path.split(" > ")[0].strip() if path
                   else row.get("title", "").split(" > ")[0].strip())
        for ci, ch in enumerate(chunk_doc(row["text"], path,
                                          config.CHUNK_MAX_CHARS, config.CHUNK_OVERLAP)):
            ids.append(f"{tenant_id}__d{di}__c{ci}")   # id ổn định -> upsert không trùng
            docs.append(ch)
            metas.append({
                "source": row.get("title") or row.get("url") or path or "?",
                "title": row.get("title", ""), "path": path, "chapter": chapter,
                "url": row.get("url", ""), "chunk_index": ci,
                "tenant_id": tenant_id, "data_class": data_class,
                "embed_model": config.EMBED_MODEL,
            })

    if not ids:
        print("[!] Không có chunk nào để nạp.")
        sys.exit(1)

    # Embed theo batch (giảm số lời gọi API/round-trip)
    batch = 64
    embs = []
    for i in range(0, len(docs), batch):
        embs.extend(provider.embed_texts(docs[i:i + batch], task="document"))
        print(f"  embed {min(i + batch, len(docs))}/{len(docs)} chunk…", flush=True)

    col.upsert(ids=ids, embeddings=embs, documents=docs, metadatas=metas)
    print(f"Đã nạp {len(ids)} chunk từ {len(rows)} tài liệu vào '{config.COLLECTION}'.")


if __name__ == "__main__":
    main()
