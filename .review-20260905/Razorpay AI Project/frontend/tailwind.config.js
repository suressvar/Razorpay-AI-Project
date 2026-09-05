/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        fintech: {
          dark: '#0B132B',
          card: '#1C2541',
          cardBorder: '#3A506B',
          accent: '#0080FF',
          accentHover: '#0066CC',
          cyan: '#5BC0BE',
          success: '#10B981',
          warning: '#F59E0B',
          danger: '#EF4444',
          muted: '#94A3B8',
        }
      }
    },
  },
  plugins: [],
}
