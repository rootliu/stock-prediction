/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'stock-up': '#f5222d',
        'stock-down': '#52c41a',
      }
    },
  },
  plugins: [],
}