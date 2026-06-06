/** @type {import('tailwindcss').Config} */
// Token đồng bộ với DESIGN.md (mục 1–2). Map sang CSS var ở index.css → 1 nguồn sự thật.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "var(--brand-50)",
          500: "var(--brand-500)",
          600: "var(--brand-600)",
          700: "var(--brand-700)",
        },
        ink: {
          900: "var(--ink-900)",
          600: "var(--ink-600)",
          400: "var(--ink-400)",
        },
        line: "var(--line)",
        surface: "var(--surface)",
        canvas: "var(--canvas)",
        trust: "var(--trust)",
        warn: "var(--warn)",
        danger: "var(--danger)",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        xs: ["12px", "1.5"],
        sm: ["13px", "1.6"],
        base: ["14px", "1.6"],
        md: ["16px", "1.6"],
        lg: ["20px", "1.4"],
        xl: ["24px", "1.3"],
        "2xl": ["30px", "1.25"],
      },
      maxWidth: { content: "960px", prose: "72ch" },
      borderRadius: { card: "12px", btn: "8px" },
    },
  },
  plugins: [],
};
