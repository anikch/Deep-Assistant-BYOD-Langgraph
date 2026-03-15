import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sidebar: {
          DEFAULT: "#1a1a2e",
          hover: "#16213e",
          border: "#0f3460",
        },
        primary: {
          DEFAULT: "#4f46e5",
          hover: "#4338ca",
          light: "#e0e7ff",
        },
        surface: {
          DEFAULT: "#ffffff",
          secondary: "#f8fafc",
          tertiary: "#f1f5f9",
        },
      },
    },
  },
  plugins: [],
};

export default config;
