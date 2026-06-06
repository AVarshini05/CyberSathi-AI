/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gov: {
          navy: '#0f172a',     // Slate 900 (Main theme)
          indigo: '#1e3a8a',   // Indigo 900 (Primary buttons & headers)
          orange: '#ea580c',   // Orange 600 (Accents and alerts)
          slate: '#475569',    // Slate 600 (Labels and description text)
          light: '#f8fafc',    // Slate 50 (Background container highlights)
          border: '#cbd5e1'    // Slate 300 (Input boundaries)
        }
      },
      fontFamily: {
        sans: ['Inter', 'Roboto', 'Outfit', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
