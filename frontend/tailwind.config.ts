import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "#0d0d0d",
        surface: "#1a1a19",
        raised: "#232322",
        line: "#2c2c2a",
        axis: "#383835",
        ink: "#f0efec",
        ink2: "#c3c2b7",
        muted: "#898781",
        accent: "#3987e5",
        good: "#0ca30c",
        warn: "#fab219",
        serious: "#ec835a",
        critical: "#d03b3b",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
