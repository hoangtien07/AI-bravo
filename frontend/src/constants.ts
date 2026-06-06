// Phân hệ (chapter) để lọc nguồn — đồng bộ với CHAPTERS trong app.py (Streamlit).
export const CHAPTERS = [
  "Tất cả phân hệ",
  "Quản lý tài chính kế toán",
  "Quản lý mua hàng",
  "Quản lý bán hàng",
  "Quản lý hàng tồn kho",
  "Quản lý sản xuất",
  "Quản lý nguồn nhân lực",
  "Quản lý quan hệ khách hàng",
  "Các chức năng hệ thống",
  "Các quy tắc cơ bản",
] as const;

export type TabKey = "qa" | "draft" | "util";

export const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: "qa", label: "Hỏi-đáp & Tra cứu", icon: "💬" },
  { key: "draft", label: "Soạn nháp", icon: "✍️" },
  { key: "util", label: "Tiện ích", icon: "🧰" },
];
