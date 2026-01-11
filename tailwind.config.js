/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.{html,js}',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [    
      {
        light: {
          "base-100": "rgb(217 211 199)",
          "base-200": "oklch(0.956 0.000 0.0)",
          "base-300": "oklch(95% 0 0)",
          "base-content": "oklch(21% 0.006 285.885)",

          "primary": "rgb(172 38 24)",
          "primary-content": "oklch(93% 0.034 272.788)",

          "secondary": "rgb(2 11 60)",
          "secondary-content": "oklch(94% 0.028 342.258)",

          "accent": "oklch(77% 0.152 181.912)",
          "accent-content": "oklch(38% 0.063 188.416)",

          "neutral": "oklch(14% 0.005 285.823)",
          "neutral-content": "oklch(92% 0.004 286.32)",

          "info": "oklch(74% 0.16 232.661)",
          "info-content": "oklch(29% 0.066 243.157)",

          "success": "oklch(76% 0.177 163.223)",
          "success-content": "oklch(37% 0.077 168.94)",

          "warning": "oklch(82% 0.189 84.429)",
          "warning-content": "oklch(41% 0.112 45.904)",

          "error": "oklch(71% 0.194 13.428)",
          "error-content": "oklch(27% 0.105 12.094)",
        },
      },
    'dark'],
  },
};
