/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        ink: {
          700: "var(--ink-700)",
          800: "var(--ink-800)",
          900: "var(--ink-900)",
        },
        sand: {
          50: "var(--sand-50)",
          100: "var(--sand-100)",
          300: "var(--sand-300)",
        },
        terra: {
          500: "var(--terra-500)",
          600: "var(--terra-600)",
        },
        ochre: {
          400: "var(--ochre-400)",
        },
        leaf: {
          500: "var(--leaf-500)",
        },
        info: {
          500: "var(--info-500)",
        },
        danger: {
          500: "var(--danger-500)",
        },
      },
      borderRadius: {
        sm: "var(--r-sm)",
        md: "var(--r-md)",
        pill: "var(--r-pill)",
      },
      spacing: {
        1: "var(--s-1)",
        2: "var(--s-2)",
        3: "var(--s-3)",
        4: "var(--s-4)",
        6: "var(--s-6)",
        8: "var(--s-8)",
      },
      transitionDuration: {
        fast: "var(--t-fast)",
        DEFAULT: "var(--t-base)",
      },
      fontFamily: {
        title: ['"Bricolage Grotesque"', "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
