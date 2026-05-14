/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        graphite: {
          50: "#f6f7f9",
          100: "#e7ebf0",
          500: "#667085",
          700: "#344054",
          900: "#111827",
          950: "#080b12"
        },
        clinical: {
          indigo: "#4f46e5",
          emerald: "#10b981",
          cyan: "#22d3ee"
        }
      },
      boxShadow: {
        clinical: "0 18px 50px rgba(15, 23, 42, 0.08)"
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif"
        ],
        mono: ["JetBrains Mono", "SFMono-Regular", "Consolas", "monospace"]
      }
    }
  },
  plugins: []
};
