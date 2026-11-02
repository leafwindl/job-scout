import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f1420",
        panel: "#171d2b",
        panel2: "#1d2536",
        line: "#29324a",
        accent: "#4f8cff",
        mint: "#39d0a8",
      },
    },
  },
  plugins: [],
};

export default config;
