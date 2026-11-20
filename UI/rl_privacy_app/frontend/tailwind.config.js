/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"] },
      colors: {
        brand: { 50: "#eef4ff", 100: "#dbe6fe", 200: "#bfd3fe", 400: "#7c9cf8", 500: "#5b7bf0", 600: "#4459e3", 700: "#3846c9", 800: "#2f3aa3", 900: "#1e255f" },
      },
      boxShadow: { card: "0 1px 2px rgba(16,24,40,.04), 0 8px 24px -8px rgba(16,24,40,.12)" },
    },
  },
  plugins: [],
};
