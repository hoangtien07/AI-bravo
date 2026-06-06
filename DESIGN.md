# DESIGN.md — Hiến pháp phong cách ChatAI BRAVO

> "Style constitution" cho UI web (frontend/). Mọi màn hình PHẢI bám file này.
> Cảm hứng cấu trúc 9-mục từ open-design (nexu-io/open-design) — nhưng đây là bản
> **BRAVO-hoá**, dùng cho design + **design-critic pass** (đối chiếu mục 9 Anti-patterns).
>
> ⚠️ Mã hex là **[cần verify]** với brand guide nội bộ BRAVO. Web công khai chỉ xác nhận
> tông: **xanh dương + nền trắng + xám**, giọng enterprise/ISO đáng tin. Khi có brand guide
> thật, chỉ cần sửa token ở mục 1–2; phần còn lại không đổi.

---

## 1. Color — Bảng màu

Định vị seminar = **đo lường độ tin cậy + tuân thủ dữ liệu** (kiểu legal-AI). Màu phải nói
"đáng tin, điềm tĩnh, doanh nghiệp" — KHÔNG lòe loẹt, KHÔNG gradient marketing.

| Token | Hex `[cần verify]` | Dùng cho |
|---|---|---|
| `--brand-700` | `#0B4F8A` | Nhấn mạnh, heading thương hiệu |
| `--brand-600` | `#1565C0` | **Primary** — nút chính, link, tab active |
| `--brand-500` | `#1E78D2` | Hover primary |
| `--brand-50`  | `#EAF2FB` | Nền nhấn nhẹ, bubble trợ lý |
| `--ink-900`   | `#0F172A` | Chữ chính |
| `--ink-600`   | `#475569` | Chữ phụ, caption |
| `--ink-400`   | `#94A3B8` | Placeholder, chữ mờ |
| `--line`      | `#E2E8F0` | Viền, divider |
| `--surface`   | `#FFFFFF` | Nền thẻ |
| `--canvas`    | `#F7F9FC` | Nền trang |

**Màu ngữ nghĩa (semantic) — dùng cho RÀO CHẮN, đây là điểm nhận diện của sản phẩm:**

| Token | Hex | Ý nghĩa |
|---|---|---|
| `--trust`  | `#0E7C5A` | ✅ Grounded — mọi mã TK/văn bản đều có trong nguồn |
| `--warn`   | `#B45309` | ⚠️ Cờ ungrounded / PII đã ẩn / bản nháp cần duyệt |
| `--danger` | `#B42318` | ⛔ Bị chặn (PII), lỗi |

Quy tắc: **trust/warn KHÔNG bao giờ chỉ dùng màu để truyền tin** — luôn kèm icon + chữ
(người mù màu + hội đồng đọc nhanh). Tỉ lệ tương phản chữ/nền ≥ 4.5:1 (WCAG AA).

## 2. Typography — Chữ

- **Font:** `Inter` (UI) — fallback `system-ui, "Segoe UI", Roboto, sans-serif`. Tiếng Việt
  đủ dấu. KHÔNG dùng font marketing. Mã/route/TK dùng `"JetBrains Mono", ui-monospace`.
- **Thang (type scale):** 12 / 13 / 14 (base) / 16 / 20 / 24 / 30. Dòng cao 1.6 cho body
  (tiếng Việt nhiều dấu → cần thoáng).
- **Cân nặng:** 400 body · 500 nhãn/caption nhấn · 600 heading. KHÔNG 700+ (quá đậm, mất tinh tế).
- Câu trả lời RAG (markdown) là nội dung chính → đọc thoải mái: max-width ~72ch, không tràn.

## 3. Spacing — Khoảng cách

- Thang 4px (Tailwind spacing): `4 8 12 16 24 32 48`; nửa bước `6 10 14` chỉ khi tinh chỉnh
  nhỏ (gap chip, padding nút). KHÔNG dùng số tuỳ tiện ngoài lưới này.
- Padding thẻ: 16–24. Khoảng giữa khối: 24. Section: 32–48.
- Vùng thở (whitespace) là tính năng, không phải lãng phí — enterprise = thoáng, không nhồi.

## 4. Layout — Bố cục

- **Khung:** Sidebar trái cố định (cấu hình + bảng điểm tin cậy) + vùng nội dung chính.
  Trên mobile: sidebar gập thành drawer/section trên cùng.
- **Điều hướng:** 3 view = `💬 Hỏi-đáp` · `✍️ Soạn nháp` · `🧰 Tiện ích` — tab ngang, rõ active.
- Nội dung chính: 1 cột, căn giữa, max-width ~`960px`. Chat luôn cuộn xuống tin mới nhất.
- Sidebar nêu rõ **route** (cloud/self-host) + **bảng điểm eval** — biến rào chắn vô hình thành hữu hình.

## 5. Components — Thành phần

- **Nút:** bo `8px`, primary nền `--brand-600` chữ trắng; secondary viền `--line` nền trắng;
  ghost trong suốt. Cao 40px. Trạng thái loading có spinner + chữ "Đang…", disable khi trống.
- **Ô nhập:** viền `--line` 1px, focus viền `--brand-600` + ring mờ; bo `8px`; placeholder `--ink-400`.
- **Bubble chat:** user nền `--brand-50` căn phải; trợ lý nền `--surface` viền `--line` căn trái.
- **Trust strip** (đặc trưng sản phẩm): hàng chip dưới mỗi câu trả lời — `max_sim`, `route`, và
  chip **✅ grounded** (xanh trust) hoặc **⚠️ cờ ungrounded** (warn) liệt kê mã TK/điều luật.
- **Citation:** danh sách nguồn deep-link, hiện "đoạn #" trung thực (help SPA không có trang thật).
- **Card bảng điểm:** số lớn (answer pass / refuse / định khoản) + caption "không hứa 0 sai".
- **Banner route:** dải mỏng đầu trang — vàng warn khi cloud ("có thể gửi ra ngoài, PII tự ẩn"),
  xanh trust khi self-host ("không gửi ra ngoài").
- **Badge nháp:** mọi đầu ra Soạn/Tiện ích gắn nhãn **"BẢN NHÁP — người dùng duyệt"**.

## 6. Motion — Chuyển động

- Tinh tế, phục vụ chức năng: fade/slide 120–180ms, ease-out. Spinner khi chờ LLM.
- KHÔNG bounce, KHÔNG parallax, KHÔNG animation trang trí. Tôn trọng `prefers-reduced-motion`.

## 7. Voice — Giọng

- Tiếng Việt, chuyên nghiệp, điềm tĩnh, **trung thực**. Xưng hô trung tính ("anh/chị").
- KHÔNG hype ("AI thần kỳ", "0 sai"). Đóng khung: "hệ THAM CHIẾU có cảnh báo, người kế toán duyệt".
- Nhãn ngắn, động từ rõ: "Hỏi", "Soạn nháp", "Thực hiện". Lỗi nói thật + cách xử lý.

## 8. Brand — Thương hiệu

- ChatAI BRAVO = lớp trợ lý có dẫn chứng trên hệ sinh thái BRAVO. Tông: ERP nghiêm túc,
  ISO/đáng tin, không phải chatbot tiêu dùng. Logo/wordmark để chỗ trang trọng, không nhại.
- Điểm nhận diện thị giác = **lớp bằng chứng tin cậy** (trust strip + citation + bảng điểm),
  KHÔNG phải hiệu ứng. Đối thủ khoe "trả lời nhanh"; ta khoe "trả lời **đo được & truy nguồn được**".

## 9. Anti-patterns — Checklist KIỂM DUYỆT (design-critic pass đối chiếu mục này)

Mỗi màn hình phải PASS hết. ❌ = vi phạm phải sửa.

- ❌ Gradient sặc sỡ / màu marketing / hơn 1 màu primary.
- ❌ Truyền trạng thái rào chắn **chỉ bằng màu** (thiếu icon/chữ).
- ❌ Giấu trust strip / citation / cờ ungrounded để "cho đẹp" — đây là lõi, phải luôn hiện.
- ❌ Hứa hẹn "0 sai", "chính xác tuyệt đối", bỏ nhãn "bản nháp / cần duyệt".
- ❌ Nhồi nhét, thiếu whitespace; **body/nội dung** < 13px (caption/micro-label 12px được),
  body line-height < 1.5.
- ❌ Tương phản chữ/nền < 4.5:1; chữ trắng trên nền nhạt.
- ❌ Animation trang trí, bounce, tự chạy; bỏ qua `prefers-reduced-motion`.
- ❌ Font > 600 weight tràn lan; mix nhiều họ font.
- ❌ Số đo tuỳ tiện ngoài thang spacing Tailwind (mục 3) / type scale mục 2.
- ❌ Bịa nhãn dữ liệu thật; quên banner cảnh báo route cloud.
- ❌ Mất trạng thái loading/disabled/empty; nút bấm được khi input trống.
