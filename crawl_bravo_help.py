"""
crawl_bravo_help.py — Thu thập tài liệu CÔNG KHAI trên bravo.com.vn cho POC RAG.

Nguyên tắc (đạo đức + an toàn):
- CHỈ crawl trang công khai trên cùng domain, theo path cho phép (config.CRAWL_ALLOW_PREFIXES).
- TÔN TRỌNG robots.txt, có delay giữa các request, giới hạn số trang.
- KHÔNG đăng nhập, KHÔNG lấy dữ liệu khách hàng / kế toán.

Chạy:   python crawl_bravo_help.py
Kết quả: data/raw/pages.jsonl   (mỗi dòng: {"url","title","text"})
"""
import json
import sys
import time
from collections import deque
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import config


def allowed_path(path: str) -> bool:
    return any(path.startswith(p) for p in config.CRAWL_ALLOW_PREFIXES)


def clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()
    node = None
    for sel in ["article", "main", "div.entry-content", "div.post-content",
                "div.td-post-content", "div.content"]:
        node = soup.select_one(sel)
        if node:
            break
    node = node or soup.body
    if node is None:
        return ""
    lines = [ln.strip() for ln in node.get_text(separator="\n").splitlines()]
    return "\n".join(ln for ln in lines if ln)


def get_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else ""


def main():
    rp = robotparser.RobotFileParser()
    robots_url = f"https://{config.CRAWL_DOMAIN}/robots.txt"
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception:
        print(f"[!] Không đọc được {robots_url}; vẫn crawl thận trọng.")
        rp = None

    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT})

    seen, results = set(), []
    queue = deque(config.CRAWL_SEEDS)
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)

    while queue and len(results) < config.CRAWL_MAX_PAGES:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)

        parsed = urlparse(url)
        if parsed.netloc != config.CRAWL_DOMAIN:
            continue
        if rp is not None and not rp.can_fetch(config.USER_AGENT, url):
            print(f"[robots] bỏ qua {url}")
            continue

        try:
            r = session.get(url, timeout=config.CRAWL_TIMEOUT)
            if r.status_code != 200 or "text/html" not in r.headers.get("Content-Type", ""):
                continue
        except Exception as e:
            print(f"[!] lỗi tải {url}: {e}")
            continue

        soup = BeautifulSoup(r.text, "lxml")
        text = clean_text(soup)
        if len(text) >= config.MIN_PAGE_CHARS:
            title = get_title(soup)
            results.append({"url": url, "title": title, "text": text})
            print(f"[{len(results):>3}] {title[:70]}")

        for a in soup.find_all("a", href=True):
            nxt = urljoin(url, a["href"]).split("#")[0]
            p = urlparse(nxt)
            if p.netloc == config.CRAWL_DOMAIN and allowed_path(p.path) and nxt not in seen:
                queue.append(nxt)

        time.sleep(config.CRAWL_DELAY_SEC)

    with open(config.RAW_FILE, "w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nXong: {len(results)} trang -> {config.RAW_FILE}")
    if not results:
        print("[!] Không lấy được trang nào. Kiểm tra mạng / cấu hình CRAWL_SEEDS / robots.txt.")
        sys.exit(1)


if __name__ == "__main__":
    main()
