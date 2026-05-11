import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: '#0b0d12', soft: '#11141b', muted: '#1a1f2b' },
        accent: { DEFAULT: '#7c5cff', soft: '#5b3df5' },
        ink: { DEFAULT: '#f1f3f8', muted: '#9aa3b2', dim: '#5c6473' },
        line: { DEFAULT: 'rgba(255,255,255,0.08)' },
      },
      borderRadius: { xl: '14px', '2xl': '20px' },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}

export default config
