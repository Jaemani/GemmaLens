import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        surface: "#F7F8FA",
        panel: "#ffffff",
        line: "#E5E7EB",
        "strong-line": "#CBD5E1",
        subtle: "#F1F5F9",
        accent: "#2563EB",
        "accent-hover": "#1D4ED8",
        "accent-soft": "#EFF6FF",
        "accent-subtle": "#DBEAFE",
        secondary: "#4B5563",
        muted: "#9CA3AF",
        amber: "#f29900"
      },
      boxShadow: {
        material: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.08)",
        "material-md": "0 4px 12px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.06)"
      }
    }
  },
  plugins: []
};

export default config;
