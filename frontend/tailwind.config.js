/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'system-ui', 'sans-serif'],
      },
      colors: {
        accent: {
          DEFAULT: '#5B9DB8',
          light: '#8BBFD4',
          dark: '#3D7A96',
          muted: 'rgba(91,157,184,0.15)',
        },
        glass: {
          bg: 'rgba(255,255,255,0.55)',
          border: 'rgba(255,255,255,0.7)',
          shadow: 'rgba(31,38,135,0.08)',
        },
        surface: '#F4F6F9',
        blob: {
          blue: 'rgba(91,157,184,0.18)',
          mint: 'rgba(134,193,173,0.15)',
          sand: 'rgba(228,210,179,0.2)',
        },
      },
      borderRadius: {
        '2xl': '1.25rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      backdropBlur: {
        glass: '24px',
      },
      boxShadow: {
        glass: '0 8px 32px rgba(31,38,135,0.08)',
        'glass-lg': '0 16px 48px rgba(31,38,135,0.12)',
        'glass-sm': '0 4px 16px rgba(31,38,135,0.06)',
        float: '0 20px 60px rgba(31,38,135,0.15)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.35s ease-out',
        'scale-in': 'scaleIn 0.3s ease-out',
        blob: 'blob 8s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        blob: {
          '0%, 100%': { transform: 'translate(0,0) scale(1)' },
          '33%': { transform: 'translate(30px,-20px) scale(1.05)' },
          '66%': { transform: 'translate(-20px,10px) scale(0.97)' },
        },
      },
    },
  },
  plugins: [],
}
