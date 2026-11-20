import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#0B2545',
          light: '#123B63',
          darker: '#071A31',
        },
        teal: {
          DEFAULT: '#0E9384',
          light: '#E6F4F2',
          dark: '#0A6E63',
        },
        success: {
          DEFAULT: '#16803C',
          light: '#E8F5EC',
        },
        warning: {
          DEFAULT: '#D97706',
          light: '#FEF3E2',
        },
        critical: {
          DEFAULT: '#C0392B',
          light: '#FCECEA',
        },
        canvas: '#F4F7FA',
        ink: '#1E293B',
        line: '#E2E8F0',
      },
      fontFamily: {
        sans: [
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
      boxShadow: {
        card: '0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.03)',
        drawer: '-8px 0 28px rgba(11, 37, 69, 0.12)',
      },
      borderRadius: {
        lg: '0.625rem',
      },
    },
  },
  plugins: [],
};

export default config;
