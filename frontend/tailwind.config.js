/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#0f1117',
          card: '#1a1d27',
          muted: '#252836',
        },
        border: {
          DEFAULT: '#2a2d3e',
        },
        status: {
          normal: '#22c55e',
          warning: '#f59e0b',
          critical: '#ef4444',
          water: '#06b6d4',
          electric: '#3b82f6',
          offline: '#6b7280',
        },
        text: {
          primary: '#f1f5f9',
          muted: '#94a3b8',
          dim: '#64748b',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
