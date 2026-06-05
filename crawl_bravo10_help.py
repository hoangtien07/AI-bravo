"""
crawl_bravo10_help.py — Thu thập bộ hướng dẫn sử dụng BRAVO 10 trên help.bravo.com.vn.

Vì sao cần script riêng (khác crawl_bravo_help.py):
- help.bravo.com.vn là SPA Angular: HTML trả về chỉ là "vỏ", nội dung tải động qua API.
  -> requests + BeautifulSoup KHÔNG đọc được nội dung. Phải render bằng trình duyệt thật.

Nguyên tắc (đạo đức + an toàn):
- CHỈ mở trang CÔNG KHAI bằng trình duyệt headless như một khách truy cập bình thường;
  để chính JS của trang tự tải nội dung. KHÔNG trích/dùng credential, KHÔNG gọi thẳng
  API nội bộ obfuscated, KHÔNG đăng nhập, KHÔNG lấy dữ liệu khách hàng.
- Lịch sự: có delay giữa các trang, giới hạn số trang, chỉ đi trong cùng domain.

Seed: data/bravo10_toc.json (mục lục công khai do người dùng export). Crawler BFS thêm
các link /detail/ phát hiện trong sidebar để phủ hết cây tài liệu.

Chạy:
    .venv/Scripts/python.exe crawl_bravo10_help.py            # crawl mặc định
    .venv/Scripts/python.exe crawl_bravo10_help.py --headful  # hiện trình duyệt (debug)
    .venv/Scripts/python.exe crawl_bravo10_help.py --limit 10 # giới hạn để thử nhanh

Kết quả: data/raw/bravo10_help.jsonl  (mỗi dòng: {"url","title","path","text"})
"""
import json
import re
import sys
import time
from collections import deque
from urllib.parse import urljoin, urlparse, parse_qs

from playwright.sync_api import sync_playwright

import config

_PAGEINFO = re.compile(r"^\d+\s*/\s*\d+\s*Trang$")   # vd "1/2 Trang" (slider footer)


def load_toc():
    """Đọc mục lục seed -> (danh sách URL seed, map url->path để đặt title đẹp)."""
    if not config.HELP_TOC_FILE.exists():
        print(f"[!] Không thấy {config.HELP_TOC_FILE}.")
        sys.exit(1)
    data = json.loads(config.HELP_TOC_FILE.read_text(encoding="utf-8"))
    seeds, path_map = [], {}
    for it in data.get("items", []):
        href = it["href"]
        seeds.append(href)
        path_map[norm_url(href)] = it.get("path", "")
    return seeds, path_map


def norm_url(url: str) -> str:
    """Khoá định danh trang: ưu tiên UUID trong /detail/<id>; nếu không có thì dùng ?command=."""
    p = urlparse(url)
    parts = [seg for seg in p.path.split("/") if seg]
    if len(parts) >= 2 and parts[0] == "detail":
        return f"detail/{parts[1]}"               # /detail/<uuid>
    q = parse_qs(p.query)
    if "command" in q:
        return f"command/{q['command'][0]}"        # /detail?...&command=Login
    return p.path or "/"


# JS: thay mỗi <img> bằng 1 text-node mốc "⟦IMGi⟧" NGAY tại vị trí của nó trong DOM,
# rồi đọc innerText -> mốc ảnh nằm ĐÚNG chỗ xen kẽ với text (giữ định dạng innerText).
# Trả kèm manifest [{i, src, alt}] để Python gán khóa + URL tuyệt đối. (Sửa DOM live là
# thao tác CUỐI trên trang, không ảnh hưởng discover_links/breadcrumb đã đọc trước đó.)
_JS_EXTRACT_WITH_IMG = """
(wrap) => {
  const imgs = Array.from(wrap.querySelectorAll('img'));
  const manifest = imgs.map((img, i) => ({
    i, src: img.getAttribute('src') || img.src || '', alt: img.getAttribute('alt') || ''
  }));
  imgs.forEach((img, i) => {
    const m = document.createTextNode('\\n\\u27E6IMG' + i + '\\u27E7\\n');
    if (img.parentNode) img.parentNode.replaceChild(m, img);
  });
  return { text: wrap.innerText || '', manifest };
}
"""

_IMG_MARK = re.compile(r"⟦IMG(\d+)⟧")   # mốc tạm ⟦IMGi⟧ do JS chèn


def extract(page, url, page_key):
    """Trả (title, text, breadcrumb, images) từ DOM đã render.

    Dùng container phổ quát `.article-main-wrapper` (bao cả trang "giàu" nhiều mục con
    lẫn trang "lá" một bài). Bóc breadcrumb đầu + cắt footer "Bài viết liên quan".
    Ảnh: giữ vị trí bằng token `⟦IMG:<key>⟧` xen trong text + trả manifest [{key,url,alt}].
    Ảnh lưu dưới dạng LINK (URL gốc help.bravo.com.vn) — không tải về.
    """
    wrap = page.query_selector(config.HELP_CONTENT_SELECTOR)
    if not wrap:
        return "", "", [], []
    res = page.eval_on_selector(config.HELP_CONTENT_SELECTOR, _JS_EXTRACT_WITH_IMG) or {}
    full = (res.get("text") or "").strip()
    raw_manifest = res.get("manifest") or []
    bc = page.eval_on_selector_all(
        ".breadcrumb-item", "els => els.map(e => e.innerText.trim()).filter(Boolean)") or []
    bc_set = set(bc)

    lines = full.split("\n")
    # Bỏ các dòng breadcrumb (kể cả tiêu đề lặp) + dòng trống ở đầu.
    i = 0
    while i < len(lines) and (not lines[i].strip() or lines[i].strip() in bc_set):
        i += 1
    body = lines[i:]
    # Cắt footer "Bài viết liên quan" trở đi.
    out = []
    for ln in body:
        if ln.strip() == "Bài viết liên quan":
            break
        out.append(ln)
    # Lọc dòng nhiễu UI (nút thu gọn, phân trang slider) + gộp dòng trống liên tiếp.
    text_lines, blank = [], False
    for ln in out:
        s = ln.strip()
        if s in ("Đọc thêm", "Thu gọn", "Đọc tiếp") or _PAGEINFO.match(s):
            continue
        if s:
            text_lines.append(s); blank = False
        elif not blank:
            text_lines.append(""); blank = True
    text = "\n".join(text_lines).strip()
    title = bc[-1] if bc else ""

    # Gán khóa ổn định cho ảnh: <page_key>_<i> (page_key = norm_url, "/" -> "_").
    # Chỉ giữ ảnh có token thực sự còn trong text sau khi lọc nhiễu/cắt footer.
    slug = page_key.replace("/", "_")
    by_i = {m["i"]: m for m in raw_manifest}
    images, used = [], set()

    def _sub(mo):
        i = int(mo.group(1))
        m = by_i.get(i)
        src = (m or {}).get("src", "")
        # Bỏ icon/chrome UI (nút "Đọc thêm", mũi tên thu gọn… = .svg ở assets/icons),
        # chỉ giữ screenshot nội dung thật (PNG/JPG, thường ở gw-help /pub/HtmlTool).
        if not m or not src or "assets/icons" in src or src.lower().split("?")[0].endswith(".svg"):
            return ""                                   # ảnh không xác định/icon -> bỏ token
        key = f"{slug}_{i}"
        if i not in used:
            used.add(i)
            images.append({"key": key, "url": urljoin(url, m["src"]), "alt": m.get("alt", "")})
        return f"⟦IMG:{key}⟧"

    text = _IMG_MARK.sub(_sub, text)
    return title, text, bc, images


def discover_links(page, base_url):
    """Các link /detail/ trong sidebar/nội dung để BFS tiếp."""
    hrefs = page.eval_on_selector_all(
        "a[href*='/detail']", "els => els.map(e => e.getAttribute('href'))")
    out = []
    for h in hrefs or []:
        if not h:
            continue
        full = urljoin(base_url, h)
        if urlparse(full).netloc == config.HELP_DOMAIN:
            out.append(full.split("#")[0])
    return out


def main():
    headful = "--headful" in sys.argv
    resume = "--resume" in sys.argv
    no_discover = "--no-discover" in sys.argv        # chỉ crawl seed, không BFS (bản thử 1 chương)
    limit = config.HELP_MAX_PAGES
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    out_file = config.HELP_RAW_FILE
    if "--out" in sys.argv:                           # ghi ra file riêng (không đụng corpus 651 trang)
        from pathlib import Path
        out_file = Path(sys.argv[sys.argv.index("--out") + 1])
    seed_chapter = None
    if "--chapter" in sys.argv:                       # lọc seed theo chương (path bắt đầu bằng chuỗi này)
        seed_chapter = sys.argv[sys.argv.index("--chapter") + 1]

    seeds, path_map = load_toc()
    if seed_chapter:
        seeds = [h for h in seeds if path_map.get(norm_url(h), "").startswith(seed_chapter)]
        print(f"[chapter] lọc seed theo '{seed_chapter}': còn {len(seeds)} seed.", flush=True)
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)

    seen, results = set(), []
    # --resume: nạp các trang đã crawl, chỉ đi tiếp những trang lá CHƯA có (không crawl lại).
    # Ta vẫn ghé lại các "root" trong TOC để đọc sidebar và phát hiện link mới, nhưng
    # không ghi đè/ghi trùng trang đã có; mọi link đã thu thập đều bị loại khỏi hàng đợi.
    collected = set()
    if resume and out_file.exists():
        for line in open(out_file, encoding="utf-8"):
            row = json.loads(line)
            results.append(row)
            collected.add(norm_url(row["url"]))
        print(f"[resume] đã có {len(collected)} trang; chỉ crawl phần còn thiếu.", flush=True)
    out_f = open(out_file, "a" if resume else "w", encoding="utf-8")
    base_count = len(results)
    limit += base_count          # khi resume: cap tính trên tổng (đã có + mới)
    queue = deque(seeds)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)
        page = browser.new_page(user_agent=config.USER_AGENT)
        page.set_default_navigation_timeout(config.HELP_NAV_TIMEOUT_MS)

        while queue and len(results) < limit:
            url = queue.popleft()
            key = norm_url(url)
            if key in seen:
                continue
            seen.add(key)
            if urlparse(url).netloc != config.HELP_DOMAIN:
                continue

            try:
                # domcontentloaded + poll ngắn cho khối nội dung; KHÔNG dùng networkidle
                # (SPA có analytics giữ kết nối -> networkidle treo) và KHÔNG chờ selector
                # 60s (vài trang render chậm/khác cấu trúc sẽ làm treo cả crawl).
                page.goto(url, wait_until="domcontentloaded")
                waited = 0
                while waited < config.HELP_SELECTOR_TIMEOUT_MS:
                    el = page.query_selector(config.HELP_CONTENT_SELECTOR)
                    # chờ tới khi vùng bài viết có nội dung thật (body tải sau qua API),
                    # không chỉ là cái khung breadcrumb rỗng.
                    if el and len((el.inner_text() or "").strip()) > 150:
                        break
                    page.wait_for_timeout(500)
                    waited += 500
                page.wait_for_timeout(config.HELP_RENDER_WAIT_MS)
            except Exception as e:
                print(f"[!] lỗi tải {url}: {str(e)[:80]}", flush=True)
                continue

            # Phát hiện link mới TRƯỚC khi quyết định bỏ qua (để root đã có vẫn mở rộng cây).
            if not no_discover:
                for nxt in discover_links(page, url):
                    k = norm_url(nxt)
                    if k not in seen and k not in collected:
                        queue.append(nxt)

            if key in collected:        # --resume: đã có trang này -> không ghi lại
                continue

            title, text, bc, images = extract(page, url, key)
            # Title ưu tiên: path từ TOC (đẹp, có cấp) > breadcrumb ghép > breadcrumb cuối.
            path = path_map.get(key, "")
            display_title = path or (" > ".join(bc[1:]) if len(bc) > 1 else title) or key
            if len(text) >= config.HELP_MIN_CHARS:
                row = {"url": url, "title": display_title,
                       "path": path or " > ".join(bc[1:]), "text": text, "images": images}
                results.append(row)
                collected.add(key)
                out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                out_f.flush()
                print(f"[+{len(results) - base_count:>3} | {len(results)}] {display_title[:55]}  "
                      f"({len(text)} ký tự, {len(images)} ảnh)", flush=True)
            else:
                print(f"[skip] ngắn ({len(text)} ký tự): {display_title[:55]}", flush=True)

            time.sleep(config.HELP_DELAY_SEC)

        browser.close()
    out_f.close()

    print(f"\nXong: {len(results)} trang -> {out_file}")
    if not results:
        print("[!] Không lấy được trang nào. Kiểm tra mạng / selector / TOC.")
        sys.exit(1)


if __name__ == "__main__":
    main()
