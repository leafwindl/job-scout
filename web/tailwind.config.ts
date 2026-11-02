import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0a0e16",
        panel: "#111826",
        panel2: "#182130",
        panel3: "#202b3d",
        line: "#243044",
        "line-soft": "#1a2333",
        accent: "#4f8cff",
        mint: "#39d0a8",
        fg: "#e8edf5",
        fg2: "#9ba7bc",
        fg3: "#7e8aa0",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          '"PingFang SC"',
          '"Hiragino Sans GB"',
          '"Microsoft YaHei"',
          "system-ui",
          "sans-serif",
        ],
        mono: [
          '"SFMono-Regular"',
          "Consolas",
          '"Liberation Mono"',
          "Menlo",
          "monospace",
        ],
      },
      fontSize: {
        "2xs": ["11px", "16px"],
        "3xs": ["10px", "14px"],
      },
      borderRadius: {
        lg: "8px",
        xl: "12px",
        "2xl": "16px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,.24)",
        pop: "0 12px 32px -12px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,.02)",
      },
      keyframes: {
        rise: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        fade: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        blink: {
          "0%, 45%": { opacity: "1" },
          "50%, 95%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
      animation: {
        rise: "rise .3s cubic-bezier(.16,1,.3,1) both",
        fade: "fade .25s ease-out both",
        blink: "blink 1.1s steps(1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
