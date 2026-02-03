import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: "#06b6d4",
                secondary: "#8b5cf6",
            },
        },
    },
    plugins: [require("daisyui")],
    daisyui: {
        themes: ["corporate"], // Light theme
    },
};
export default config;
