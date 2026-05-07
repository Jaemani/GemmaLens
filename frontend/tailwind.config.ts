import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#202124",
        surface: "#f8fafd",
        panel: "#ffffff",
        line: "#dadce0",
        accent: "#1a73e8",
        amber: "#f29900"
      },
      boxShadow: {
        material: "0 1px 2px rgba(60, 64, 67, 0.18), 0 1px 3px rgba(60, 64, 67, 0.12)"
      }
    }
  },
  plugins: []
};

export default config;
