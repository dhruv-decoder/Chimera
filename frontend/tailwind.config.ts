import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#07080b",
          900: "#0a0c11",
          850: "#0e1016",
          800: "#12151c",
          700: "#1a1e28",
          600: "#252b38",
        },
        mist: {
          100: "#e8eaf0",
          200: "#cbd0db",
          300: "#aeb4c2",
          400: "#8a909f",
          500: "#6b7280",
          600: "#4b5261",
        },
        // Domain-semantic accents: red = attack, teal = defense, violet = agentic.
        threat: "#ff5c49",
        defense: "#2ed6a6",
        agentic: "#8b8cf0",
        warn: "#f5b544",
        signal: "#5ea0ff",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        "display-lg": ["clamp(2.6rem, 6vw, 4.6rem)", { lineHeight: "1.02", letterSpacing: "-0.03em" }],
        "display": ["clamp(2rem, 4.4vw, 3.2rem)", { lineHeight: "1.06", letterSpacing: "-0.025em" }],
        "display-sm": ["clamp(1.5rem, 3vw, 2.1rem)", { lineHeight: "1.12", letterSpacing: "-0.02em" }],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 24px 64px -28px rgba(0,0,0,0.7)",
        glow: "0 0 0 1px rgba(46,214,166,0.22), 0 0 40px -8px rgba(46,214,166,0.35)",
        lift: "0 30px 80px -40px rgba(0,0,0,0.85)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        sweep: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(320%)" },
        },
        pulseSoft: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.4" } },
        blink: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.25" } },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        dash: { to: { strokeDashoffset: "-24" } },
        drift: {
          "0%,100%": { transform: "translate3d(0,0,0)" },
          "50%": { transform: "translate3d(0,-2%,0)" },
        },
        ticker: { "0%": { transform: "translateX(0)" }, "100%": { transform: "translateX(-50%)" } },
      },
      animation: {
        rise: "rise 0.6s cubic-bezier(0.22,1,0.36,1) both",
        sweep: "sweep 2s ease-in-out infinite",
        pulseSoft: "pulseSoft 2.4s ease-in-out infinite",
        blink: "blink 1.4s steps(2, jump-none) infinite",
        float: "float 6s ease-in-out infinite",
        dash: "dash 1s linear infinite",
        drift: "drift 14s ease-in-out infinite",
        ticker: "ticker 40s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;
