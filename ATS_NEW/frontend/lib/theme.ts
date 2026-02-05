"use client";

import { createTheme } from "@mui/material/styles";
import { Outfit } from "next/font/google";

const outfit = Outfit({
    weight: ["300", "400", "600", "700"],
    subsets: ["latin"],
    display: "swap",
});

export const theme = createTheme({
    typography: {
        fontFamily: outfit.style.fontFamily,
        h1: { fontSize: "1.8rem", fontWeight: 700 },
        h2: { fontSize: "1.4rem", fontWeight: 600 },
        h3: { fontSize: "1.1rem", fontWeight: 600 },
        button: { textTransform: "none", fontWeight: 600 },
    },
    palette: {
        mode: "dark",
        primary: {
            main: "#06b6d4", // Cyan 500
        },
        secondary: {
            main: "#8b5cf6", // Violet 500
        },
        background: {
            default: "#0f172a", // Slate 900
            paper: "#1e293b", // Slate 800
        },
        text: {
            primary: "#f8fafc", // Slate 50
            secondary: "#94a3b8", // Slate 400
        },
    },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: "10px",
                    background: "linear-gradient(135deg, #06b6d4 0%, #8b5cf6 100%)",
                    color: "white",
                    boxShadow: "0 4px 10px rgba(6, 182, 212, 0.15)",
                    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                    "&:hover": {
                        transform: "translateY(-2px)",
                        boxShadow: "0 8px 20px rgba(139, 92, 246, 0.3)",
                    },
                },
                containedSecondary: {
                    background: "transparent",
                    border: "1px solid rgba(255,255,255,0.1)",
                    boxShadow: "none",
                    "&:hover": {
                        background: "rgba(255,255,255,0.05)",
                        boxShadow: "none",
                    },
                },
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: {
                    backgroundImage: "none",
                    backgroundColor: "rgba(30, 41, 59, 0.5)", // Surface with opacity
                    backdropFilter: "blur(16px)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    borderRadius: "16px",
                },
            },
        },
        MuiDrawer: {
            styleOverrides: {
                paper: {
                    backgroundColor: "#0f172a", // Darker for sidebar
                    borderRight: "1px solid rgba(255, 255, 255, 0.05)",
                },
            },
        },
    },
});
