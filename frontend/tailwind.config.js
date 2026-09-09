/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["../templates/**/*.html", "./src/**/*.js"],
  theme: {
    extend: {
      colors: {
        femto: {
          bg: "#0f1115",
          surface: "#171a21",
          border: "#2a2e37",
          text: "#e6e8eb",
          muted: "#9aa1ac",
          accent: "#4f8cff",
        },
      },
    },
  },
  plugins: [],
};
