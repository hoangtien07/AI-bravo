# Deploy bản DÙNG THỬ NỘI BỘ (C1 nhẹ) lên VPS — ChatAI BRAVO

Mục tiêu: đồng nghiệp truy cập qua **HTTPS + Basic Auth**, dùng **cloud LLM (OpenAI)**, **chỉ tài liệu CÔNG KHAI**. Trial ~2 tháng rồi đánh giá. LLM cloud nên **KHÔNG cần GPU**.

## 0. Chọn host
- **#1 free (khuyến nghị): Oracle Cloud Always Free — ARM Ampere A1** (4 OCPU/24GB, không hết hạn). Cần thẻ verify; chọn region còn quota ARM. Image dùng **arm64** (python:3.12-slim, qdrant/qdrant, caddy đều có arm64 ✓).
- **#2 rẻ chắc: VPS ~€2–4/tháng** (Hetzner CX22, hoặc DO/Vultr ~$5) — 2 tháng ≈ €8, uptime đảm bảo.
- Yêu cầu tối thiểu: 2 vCPU / 2GB RAM / 10GB đĩa, Ubuntu 22.04/24.04, mở cổng 80+443.

## 1. Cài Docker trên VPS
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # đăng nhập lại
```

## 2. Lấy mã + cấu hình
```bash
git clone https://github.com/hoangtien07/AI-bravo.git && cd AI-bravo
cp .env.example .env
```
Sửa `.env`:
```
LLM_PROVIDER=openai
EMBED_PROVIDER=openai
OPENAI_API_KEY=sk-...            # KEY MỚI (đã thu hồi key cũ lộ trong chat)
VECTOR_STORE=qdrant
QDRANT_URL=http://qdrant:6333    # tên service trong compose
SITE_ADDRESS=chatai.<domain>     # hoặc ":80" / IP công khai nếu chưa có domain
BASIC_AUTH_USER=bravo
BASIC_AUTH_HASH=<bcrypt>          # sinh ở bước 3
```

## 3. Sinh mật khẩu Basic Auth
```bash
docker run --rm caddy caddy hash-password --plaintext 'MAT_KHAU_NOI_BO'
# copy hash vào BASIC_AUTH_HASH trong .env
```

## 4. Ingest corpus (1 lần, cần OpenAI key — re-embed ~1622 chunk, ~$0.1–0.2)
```bash
docker compose --profile deploy up -d qdrant       # bật Qdrant trước
docker compose run --rm ui python ingest.py --reset # nạp help + KB quy định vào Qdrant
```

## 5. Khởi động bản dùng thử
```bash
docker compose --profile deploy up -d               # qdrant + ui (Streamlit) + caddy (HTTPS+auth)
docker compose logs -f caddy ui
```
Truy cập **https://<SITE_ADDRESS>** → đăng nhập Basic Auth. (Có domain → Caddy tự xin Let's Encrypt; chỉ IP → chứng chỉ tự ký, trình duyệt cảnh báo, chấp nhận cho nội bộ.)

## 6. Bảo vệ chi phí & dữ liệu (BẮT BUỘC)
- **Đặt hạn mức chi tiêu OpenAI** (Billing → Usage limits) phòng lạm dụng. Ước tính trial: ~$10–25/2 tháng `[cần đo qua usage]`.
- Nhãn UI đã ghi "dữ liệu CÔNG KHAI, không nhập dữ liệu cá nhân/khách" — nhắc người dùng thử.
- KHÔNG commit `.env`; trên VPS chỉ chmod 600 `.env`.
- Backup volume: `docker run --rm -v aibravo_qdrant_data:/d -v $PWD:/b alpine tar czf /b/qdrant_backup.tgz /d` (định kỳ).

## 7. Vận hành
- Sức khoẻ: `GET https://<site>/healthz` (sau auth) hoặc `docker compose ps`.
- Coverage/feedback: `docker compose run --rm ui python analytics.py` + `benchmark.py`.
- Cập nhật tài liệu: `ingest.py --reset` (re-embed) hoặc `--delete-category X` rồi nạp lô mới.

## Còn thiếu cho production (Mốc C2 — gated)
Self-host LLM (Ollama, cần GPU) cho dữ liệu nhạy cảm · tài liệu nội bộ + pháp chế duyệt · monitoring/alert · secrets manager (thay `.env`) · multi-tenant nếu mở nhiều phòng. Xem `docs/deploy.md` §5.
