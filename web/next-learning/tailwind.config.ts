import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./shared/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eefaf6",
          100: "#d6f2e8",
          500: "#16856f",
          600: "#0f6f5f",
          700: "#105a50",
          900: "#102b28"
        },
        accent: {
          50: "#fff7ed",
          100: "#ffedd5",
          500: "#f97316",
          600: "#ea580c"
        },
        signal: {
          50: "#eff8ff",
          100: "#dff1ff",
          500: "#0ea5e9",
          600: "#0284c7"
        },
        coral: {
          50: "#fff1f2",
          500: "#f43f5e",
          600: "#e11d48"
        },
        ink: {
          900: "#17211f",
          700: "#33413d",
          500: "#66736f"
        }
      }
    }
  },
  plugins: []
} satisfies Config;
