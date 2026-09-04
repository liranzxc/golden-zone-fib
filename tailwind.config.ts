import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0e14",
        panel: "#12151d",
        border: "#232838",
        up: "#22c55e",
        down: "#ef4444",
        accent: "#3b82f6",
      },
    },
  },
  plugins: [],
};
export default config;
