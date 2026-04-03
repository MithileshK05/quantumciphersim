/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'quantum-void': '#030508',
        'quantum-surface': '#0B101A',
        'quantum-surface-hover': '#141C2B',
        'quantum-border': '#1A2639',
        'neon-cyan': '#00F0FF',
        'neon-red': '#FF003C',
        'neon-purple': '#B026FF',
        'text-main': '#E2E8F0',
        'text-muted': '#64748B',
      },
      fontFamily: {
        sans: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      }
    },
  },
  plugins: [],
}
