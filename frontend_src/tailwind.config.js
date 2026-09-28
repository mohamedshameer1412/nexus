/** Colours come from CSS variables (app/globals.css), so every component shares one palette. */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}", "./lib/**/*.{js,jsx,ts,tsx}"],
  theme: {
    container: { center: true, padding: "1rem" },
    extend: {
      colors: {
        background: v("background"),
        surface:    v("surface"),
        "surface-2": v("surface-2"),
        border:     v("border"),
        foreground: v("foreground"),
        muted:      v("muted"),
        brand: {
          DEFAULT: v("brand"),
          deep:    v("brand-deep"),
          ink:     v("brand-ink"),
          soft:    v("brand-soft"),
          wash:    v("brand-wash"),
        },
        primary: { DEFAULT: v("brand"), hover: v("brand-deep"), foreground: "rgb(255 255 255 / <alpha-value>)" },
        link:    v("brand-deep"),
        accent:  v("brand-soft"),
        ring:    v("brand"),
        strong:  { DEFAULT: v("strong"), bg: v("strong-bg") },
        mid:     { DEFAULT: v("mid"),    bg: v("mid-bg") },
        weak:    { DEFAULT: v("weak"),   bg: v("weak-bg") },
        success: { DEFAULT: v("strong"), bg: v("strong-bg") },
        warning: { DEFAULT: v("mid"),    bg: v("mid-bg") },
        danger:  { DEFAULT: v("weak"),   bg: v("weak-bg") },
        navy: { 900: "#0B2A5B", 800: "#0D3470", 700: "#0F3F85" },
      },
      fontFamily: {
        sans:    ["Inter", "'IBM Plex Sans'", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ["Inter", "'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono:    ["'JetBrains Mono'", "'Fira Code'", "monospace"],
      },
      boxShadow: {
        card: "var(--shadow-card)",
        lift: "var(--shadow-lift)",
        glow: "var(--shadow-glow)",
        pop:  "var(--shadow-pop)",
      },
      borderRadius: { xl: "14px", "2xl": "18px", "3xl": "24px", lg: "10px", md: "8px", sm: "6px" },
      spacing: { safe: "env(safe-area-inset-bottom, 0px)" },
      keyframes: {
        "fade-in":    { from: { opacity: 0 },              to: { opacity: 1 } },
        "slide-up":   { from: { opacity: 0, transform: "translateY(12px)" }, to: { opacity: 1, transform: "translateY(0)" } },
        "slide-in":   { from: { opacity: 0, transform: "translateX(-12px)" }, to: { opacity: 1, transform: "translateX(0)" } },
        shimmer:      { from: { backgroundPosition: "200% 0" }, to: { backgroundPosition: "-200% 0" } },
        "spin-slow":  { from: { transform: "rotate(0deg)" }, to: { transform: "rotate(360deg)" } },
      },
      animation: {
        "fade-in":  "fade-in .2s ease-out",
        "slide-up": "slide-up .3s ease-out",
        "slide-in": "slide-in .25s ease-out",
        shimmer:    "shimmer 1.6s linear infinite",
        "spin-slow": "spin-slow 3s linear infinite",
      },
      backgroundImage: {
        "nexus-header": "linear-gradient(95deg, #0B2A5B 0%, #1464E8 100%)",
        "nexus-splash": "linear-gradient(160deg, #F7FAFE 0%, #EAF4FF 50%, #CCDEFF 100%)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
