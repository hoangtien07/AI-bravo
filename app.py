"""
app.py — Giao diện chat demo (Streamlit).
Chạy:  streamlit run app.py
"""
import json
from datetime import datetime

import streamlit as st

import config
import provider
import rag

st.set_page_config(page_title="Trợ lý nghiệp vụ BRAVO", page_icon="🤖")

st.title("🤖 Trợ lý nghiệp vụ BRAVO")

# Nhãn ĐỘNG & TRUNG THỰC theo route (cloud thì câu hỏi rời máy -> nói rõ).
if provider.is_cloud():
    st.caption(f"⚠️ Đang dùng AI **cloud** (`{config.LLM_PROVIDER}`). Câu hỏi **có thể được gửi "
               "ra dịch vụ bên ngoài** — chỉ dùng cho tài liệu CÔNG KHAI, không nhập dữ liệu "
               "cá nhân/khách hàng. Tài liệu nguồn là help BRAVO công khai/minh hoạ.")
else:
    st.caption("🔒 Đang chạy **self-host** — không gửi dữ liệu ra ngoài. Tài liệu nguồn là "
               "help BRAVO công khai/minh hoạ.")

with st.sidebar:
    st.subheader("Cấu hình")
    st.write(f"LLM: `{config.LLM_PROVIDER}` → `{config.LLM_MODEL}`")
    st.write(f"Embedding: `{config.EMBED_PROVIDER}` → `{config.EMBED_MODEL}`")
    st.write(f"Hybrid: `{'BM25+vector' if config.HYBRID_ENABLED else 'vector'}`"
             f"{' +rerank' if config.RERANK_ENABLED else ''}")
    k = st.slider("Số đoạn truy hồi (k)", 1, 8, config.TOP_K)
    min_sim = st.slider("Ngưỡng tương đồng (chống bịa)", 0.0, 1.0, config.MIN_SIM, 0.05)
    st.caption("Dưới ngưỡng → trợ lý từ chối thay vì đoán.")


def _log_feedback(question, rating):
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.DATA_DIR / "feedback.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"),
                                "q": rag._redact(question), "rating": rating},
                               ensure_ascii=False) + "\n")
    except Exception:
        pass


if "history" not in st.session_state:
    st.session_state.history = []

for h in st.session_state.history:
    with st.chat_message(h["role"]):
        st.markdown(h["content"])

q = st.chat_input("Hỏi về nghiệp vụ / cấu hình BRAVO…")
if q:
    st.session_state.history.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        with st.spinner("Đang tra cứu…"):
            r = rag.ask(q, k=k, min_sim=min_sim)
        st.markdown(r["answer"])

        if r.get("sources"):
            st.markdown("**Nguồn:**")
            for c in r["sources"]:                      # rào chắn (3): trích nguồn deep-link
                if c.get("url"):
                    st.markdown(f"- [{c['source']}]({c['url']})")
                else:
                    st.markdown(f"- {c['source']}")

        with st.expander("Đoạn tài liệu đã truy hồi (audit)"):
            for h in r.get("hits", []):
                sim = h.get("sim")
                st.markdown(f"**{h['source']}** "
                            f"(sim={sim if sim is not None else '—'}) — {h.get('url', '')}")
                st.text(h["text"][:500])

        # Feedback 👍/👎 (ghi feedback.jsonl để phân tích coverage)
        c1, c2, _ = st.columns([1, 1, 8])
        if c1.button("👍", key=f"up_{len(st.session_state.history)}"):
            _log_feedback(q, "up"); st.toast("Cảm ơn phản hồi!")
        if c2.button("👎", key=f"down_{len(st.session_state.history)}"):
            _log_feedback(q, "down"); st.toast("Đã ghi nhận để cải thiện.")

    st.session_state.history.append({"role": "assistant", "content": r["answer"]})
