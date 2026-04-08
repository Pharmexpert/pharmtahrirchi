/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Warm cream palette matching existing CSS variables
        cream: {
          50:  '#FFF8F0',
          100: '#FFEFDC',
          200: '#FDE3C5',
          300: '#F7D2A6',
          400: '#E8B97F',
          500: '#B48C64',
          600: '#8B5E3C',
          700: '#5C3A22',
          800: '#3D2B1F',
        },
        accent: {
          DEFAULT: '#B48C64',
          dark: '#8B5E3C',
        },
      },
      borderRadius: {
        'xl2': '20px',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
