import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17201b",
        surface: "#f8faf7",
        panel: "#ffffff",
        line: "#d8ded6",
        accent: "#1d6f5f",
        amber: "#a7651a"
      },
      boxShadow: {
        material: "0 1px 2px rgba(23, 32, 27, 0.08), 0 2px 6px rgba(23, 32, 27, 0.06)"
      }
    }
  },
  plugins: []
};

export default config;
