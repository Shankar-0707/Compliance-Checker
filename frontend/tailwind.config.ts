import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        nutri: {
          a: "#038141",
          b: "#85bb2f",
          c: "#fecb02",
          d: "#ee8100",
          e: "#e63e11",
        }
      },
    },
  },
  plugins: [],
};
export default config;
