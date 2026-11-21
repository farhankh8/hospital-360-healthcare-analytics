import type { Config } from 'tailwindcss';

const withAlpha = (variable: string) => `rgb(var(${variable}) / <alpha-value>)`;

const config: Config = {
  darkMode: 'class',
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: withAlpha('--color-navy'),
          light: withAlpha('--color-navy-light'),
          darker: '#071A31',
        },
        teal: {
          DEFAULT: withAlpha('--color-teal'),
          light: withAlpha('--color-teal-soft'),
          dark: withAlpha('--color-teal-dark'),
        },
        success: {
          DEFAULT: withAlpha('--color-success'),
          light: withAlpha('--color-success-soft'),
        },
        warning: {
          DEFAULT: withAlpha('--color-warning'),
          light: withAlpha('--color-warning-soft'),
        },
        critical: {
          DEFAULT: withAlpha('--color-critical'),
          light: withAlpha('--color-critical-soft'),
        },
        info: {
          DEFAULT: withAlpha('--color-info'),
          light: withAlpha('--color-info-soft'),
        },
        canvas: withAlpha('--color-canvas'),
        surface: {
          DEFAULT: withAlpha('--color-surface'),
          alt: withAlpha('--color-surface-alt'),
          hover: withAlpha('--color-surface-hover'),
        },
        ink: {
          DEFAULT: withAlpha('--color-ink'),
          strong: withAlpha('--color-ink-strong'),
        },
        muted: {
          DEFAULT: withAlpha('--color-muted'),
          soft: withAlpha('--color-muted-soft'),
        },
        line: {
          DEFAULT: withAlpha('--color-line'),
          strong: withAlpha('--color-line-strong'),
        },
      },
      fontFamily: {
        sans: [
          'var(--font-inter)',
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
      },
      fontSize: {
        kpi: ['30px', { lineHeight: '1.15', fontWeight: '700', letterSpacing: '-0.02em' }],
        'kpi-sm': ['24px', { lineHeight: '1.2', fontWeight: '650', letterSpacing: '-0.01em' }],
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        pop: 'var(--shadow-pop)',
      },
      borderRadius: {
        DEFAULT: '8px',
        sm: '6px',
        md: '10px',
        lg: '14px',
      },
      zIndex: {
        dropdown: '30',
        sticky: '40',
        overlay: '50',
        modal: '60',
        toast: '70',
      },
    },
  },
  plugins: [],
};

export default config;
