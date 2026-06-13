import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          300: "#6ee7b7",
          500: "#0f8a68",
          600: "#0b6b4f",
          700: "#0a5944",
          900: "#0d2724"
        },
        surface: {
          canvas: "#f6f4ef",
          subtle: "#f8fafc"
        },
        signal: {
          50: "#eff6ff",
          100: "#dbeafe",
          600: "#2563eb",
          700: "#1d4ed8"
        },
        accent: {
          50: "#fffbeb",
          100: "#fef3c7",
          600: "#d97706",
          700: "#b45309"
        }
      }
    }
  },
  plugins: []
} satisfies Config;
