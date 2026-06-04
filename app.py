"""
app.py — Giao diện demo ChatAI BRAVO (Streamlit), 3 tab theo nhóm tính năng AN TOÀN.
Chạy:  streamlit run app.py

Tab 1 — Hỏi-đáp & Tra cứu: RAG grounded trên help công khai + câu hỏi liên quan + trích nguồn.
Tab 2 — Soạn nháp: email / JD / kịch bản gọi / phỏng vấn / nội dung / ý tưởng (input người dùng).
Tab 3 — Tiện ích: dịch / soát chính tả / tóm tắt / công thức Excel.
Mọi tính năng chỉ dùng tài liệu CÔNG KHAI hoặc văn bản người dùng tự nhập — KHÔNG dữ liệu nghiệp vụ.
"""
import json
from datetime import datetime

import streamlit as st

import config
import generate
import provider
import rag
import suggest

st.set_page_config(page_title="ChatAI BRAVO", page_icon="🤖", layout="wide")
st.title("🤖 ChatAI BRAVO — Trợ lý nghiệp vụ & năng suất")

if provider.is_cloud():
    st.caption(f"⚠️ Đang dùng AI **cloud** (`{config.LLM_PROVIDER}`). Nội dung **có thể gửi ra dịch vụ "
               "bên ngoài** — chỉ dùng tài liệu CÔNG KHAI / văn bản không chứa dữ liệu cá nhân–khách hàng. "
               "Câu hỏi/đầu vào có PII (SĐT/email/MST/CCCD) sẽ tự động được ẩn trước khi gửi.")
else:
    st.caption("🔒 Đang chạy **self-host** — không gửi dữ liệu ra ngoài.")

with st.sidebar:
    st.subheader("Cấu hình")
    st.write(f"LLM: `{config.LLM_PROVIDER}` → `{config.LLM_MODEL}`")
    st.write(f"Embedding: `{config.EMBED_PROVIDER}` → `{config.EMBED_MODEL}`")
    st.write(f"Vector store: `{config.VECTOR_STORE}` · Hybrid: "
             f"`{'BM25+vector' if config.HYBRID_ENABLED else 'vector'}"
             f"{'+rerank' if config.RERANK_ENABLED else ''}`")
    k = st.slider("Số đoạn truy hồi (k)", 1, 8, config.TOP_K)
    min_sim = st.slider("Ngưỡng tương đồng (chống bịa)", 0.0, 1.0, config.MIN_SIM, 0.05)
    st.caption("Dưới ngưỡng → trợ lý từ chối thay vì đoán.")
    st.divider()
    st.caption("Mọi đầu ra của 'Soạn nháp'/'Tiện ích' là **BẢN NHÁP** — người dùng kiểm tra & "
               "phê duyệt trước khi sử dụng.")


def _log_feedback(question, rating):
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.DATA_DIR / "feedback.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"),
                                "q": rag._redact(question), "rating": rating},
                               ensure_ascii=False) + "\n")
    except Exception:
        pass


def _redact_notice(r):
    if r.get("redacted"):
        st.warning(f"Đã ẩn PII trong đầu vào ({', '.join(r['pii'])}) trước khi gửi cloud — "
                   "bản nháp dùng placeholder dạng [PHONE]/[EMAIL]…, anh/chị tự điền lại tại máy.")


tab_qa, tab_draft, tab_util = st.tabs(
    ["💬 Hỏi-đáp & Tra cứu", "✍️ Soạn nháp", "🧰 Tiện ích"])

# Phân hệ (chapter) để lọc — "demo rộng theo phòng ban" dạng nhẹ (1 selectbox, không 5 tab).
CHAPTERS = ["Tất cả phân hệ", "Quản lý tài chính kế toán", "Quản lý mua hàng", "Quản lý bán hàng",
            "Quản lý hàng tồn kho", "Quản lý sản xuất", "Quản lý nguồn nhân lực",
            "Quản lý quan hệ khách hàng", "Các chức năng hệ thống", "Các quy tắc cơ bản"]


def _trust_strip(r):
    """Bằng chứng tin cậy hiển thị (biến rào chắn vô hình thành hữu hình — định vị đo lường)."""
    bits = [f"độ khớp nguồn (max_sim): **{r.get('max_sim')}**",
            f"route: **{r.get('route')}**"]
    ut, uref = r.get("ungrounded_tk") or [], r.get("ungrounded_refs") or []
    if ut or uref:
        bits.append("⚠️ cờ chưa-có-trong-nguồn: " + ", ".join(ut + [f"TT/Điều {x}" for x in uref]))
    else:
        bits.append("✅ mọi mã TK/văn bản trích đều có trong nguồn")
    st.caption(" · ".join(bits))


# ----------------------------- TAB 1: Hỏi-đáp grounded (đa lượt) -----------------------------
with tab_qa:
    st.markdown("Hỏi về **nghiệp vụ / cấu hình BRAVO** — trả lời CÓ TRÍCH NGUỒN, từ chối khi "
                "không có trong tài liệu. (Hệ THAM CHIẾU có cảnh báo — không thay kế toán.)")
    chapter_sel = st.selectbox("Phân hệ (lọc nguồn)", CHAPTERS, key="qa_chapter")
    chapter = None if chapter_sel == CHAPTERS[0] else chapter_sel

    if "chat" not in st.session_state:
        st.session_state.chat = []
    for m in st.session_state.chat:                       # lịch sử đa lượt
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # st.chat_input KHÔNG dùng được trong st.tabs -> dùng text_input + button (đa lượt qua session).
    q = st.text_input("Câu hỏi", key="qa_q",
                      placeholder="Hỏi nghiệp vụ / định khoản / cấu hình BRAVO…")
    if st.button("Hỏi", key="qa_btn", type="primary") and q.strip():
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("Đang tra cứu…"):
                r = rag.ask(q, k=k, min_sim=min_sim, chapter=chapter)
                sug = suggest.related_questions(q, k=k, min_sim=min_sim)
            st.markdown(r["answer"])
            _trust_strip(r)                                # trust strip = rào chắn hữu hình
            if r.get("sources"):
                st.markdown("**Nguồn (deep-link tới help, kèm đoạn):**")
                for c in r["sources"]:
                    ci = c.get("chunk_index")
                    seg = f" — đoạn #{ci}" if ci is not None else ""
                    st.markdown(f"- [{c['source']}]({c['url']}){seg}" if c.get("url")
                                else f"- {c['source']}{seg}")
            if sug:
                st.markdown("**Câu hỏi liên quan:** " + " · ".join(sug))
            with st.expander("Đoạn tài liệu đã truy hồi (audit)"):
                for h in r.get("hits", []):
                    st.markdown(f"**{h['source']}** (sim={h.get('sim')}, đoạn #{h.get('chunk_index')}) "
                                f"— {h.get('url', '')}")
                    st.text(h["text"][:500])
            c1, c2, _ = st.columns([1, 1, 8])
            if c1.button("👍", key=f"up_{len(st.session_state.chat)}"):
                _log_feedback(q, "up"); st.toast("Cảm ơn phản hồi!")
            if c2.button("👎", key=f"down_{len(st.session_state.chat)}"):
                _log_feedback(q, "down"); st.toast("Đã ghi nhận.")
        st.session_state.chat.append({"role": "assistant", "content": r["answer"]})

# ----------------------------- TAB 2: Soạn nháp -----------------------------
DRAFT_TASKS = ["soan_email", "jd", "call_script", "interview", "content", "idea"]
with tab_draft:
    st.markdown("Sinh **bản nháp** từ yêu cầu của anh/chị (không dùng dữ liệu nghiệp vụ BRAVO).")
    label2key = {generate.TASKS[t][0]: t for t in DRAFT_TASKS}
    choice = st.selectbox("Loại", list(label2key), key="draft_type")
    inp = st.text_area("Yêu cầu / nội dung", key="draft_in", height=140,
                       placeholder="VD: nhắc công nợ quá hạn 30 ngày, giọng lịch sự, có hạn thanh toán mới")
    if st.button("Soạn nháp", key="draft_btn", type="primary") and inp.strip():
        with st.spinner("Đang soạn…"):
            st.session_state["draft_r"] = generate.generate(label2key[choice], inp)
    dr = st.session_state.get("draft_r")
    if dr:
        _redact_notice(dr)
        st.markdown(f"### {dr['label']} (bản nháp)")
        st.markdown(dr["output"])

# ----------------------------- TAB 3: Tiện ích -----------------------------
UTIL_TASKS = ["dich", "grammar", "tom_tat", "excel"]
with tab_util:
    st.markdown("Tiện ích văn phòng trên **văn bản anh/chị dán vào**.")
    label2key_u = {generate.TASKS[t][0]: t for t in UTIL_TASKS}
    choice_u = st.selectbox("Tiện ích", list(label2key_u), key="util_type")
    inp_u = st.text_area("Văn bản", key="util_in", height=140,
                        placeholder="Dán văn bản cần dịch / soát / tóm tắt, hoặc mô tả nhu cầu công thức Excel…")
    if st.button("Thực hiện", key="util_btn", type="primary") and inp_u.strip():
        with st.spinner("Đang xử lý…"):
            st.session_state["util_r"] = generate.generate(label2key_u[choice_u], inp_u)
    ur = st.session_state.get("util_r")
    if ur:
        _redact_notice(ur)
        st.markdown(f"### {ur['label']}")
        st.markdown(ur["output"])
