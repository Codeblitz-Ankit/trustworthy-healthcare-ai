/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'clinical-green': '#4f8a70',
        'clinical-amber': '#b8873b',
        'clinical-red': '#b95f5f',
      },
    },
  },
  plugins: [],
}

