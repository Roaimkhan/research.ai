import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: 'var(--color-ink)',
        'ink-raised': 'var(--color-ink-raised)',
        hairline: 'var(--color-hairline)',
        parchment: 'var(--color-parchment)',
        text: 'var(--color-text)',
        'text-muted': 'var(--color-text-muted)',
        signal: 'var(--color-signal)',
        episodic: 'var(--color-episodic)',
        semantic: 'var(--color-semantic)',
        procedural: 'var(--color-procedural)',
        danger: 'var(--color-danger)',
      },
      fontFamily: {
        display: ['Fraunces', 'serif'],
        sans: ['IBM Plex Sans', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      borderRadius: {
        panel: '14px',
        pill: '9999px',
        gauge: '2px',
      },
      boxShadow: {
        'glow-signal': '0 0 28px rgba(111, 255, 192, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
        'glow-episodic': '0 0 28px rgba(140, 124, 240, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
        'glow-semantic': '0 0 28px rgba(232, 163, 61, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
        'glow-procedural': '0 0 28px rgba(201, 162, 39, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
        panel: '0 16px 48px rgba(1, 4, 10, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.05), inset 0 -1px 0 rgba(0, 0, 0, 0.3)',
      },
    },
  },
  plugins: [],
} satisfies Config;
