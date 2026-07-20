/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0B0E13',
        'ink-raised': '#12161D',
        hairline: '#232A33',
        parchment: '#F4EFE3',
        text: '#EDEFF2',
        'text-muted': '#8A93A0',
        signal: '#6FFFC0',
        episodic: '#8C7CF0',
        semantic: '#E8A33D',
        procedural: '#C9A227',
        danger: '#D9694F',
      },
      fontFamily: {
        display: ['Fraunces', 'serif'],
        sans: ['IBM Plex Sans', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      borderRadius: {
        panel: '14px',
        pill: '9999px',
        readout: '2px',
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(111, 255, 192, 0.12), 0 0 24px rgba(111, 255, 192, 0.12)',
      },
    },
  },
  plugins: [],
};
