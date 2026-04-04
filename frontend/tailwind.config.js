/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111111",
        panel: "#191919",
        "panel-soft": "#232323",
        paper: "#f5f1e8",
        muted: "#9f998d",
        accent: "#d7ff64",
        "accent-soft": "#b6d94d",
      },
      fontFamily: {
        display: ["IBM Plex Sans", "Noto Sans SC", "sans-serif"],
      },
    },
  },
  plugins: [],
};
