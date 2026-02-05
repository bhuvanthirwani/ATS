"use client";

import { createTheme } from "@mui/material/styles";
import { Outfit } from "next/font/google";

const outfit = Outfit({
    weight: ["300", "400", "500", "600", "700"],
    subsets: ["latin"],
    display: "swap",
});

export const theme = createTheme({
    typography: {
        fontFamily: outfit.style.fontFamily,
        h1: { fontSize: "2rem", fontWeight: 700, letterSpacing: "-0.02em" },
        h2: { fontSize: "1.5rem", fontWeight: 600, letterSpacing: "-0.01em" },
        h3: { fontSize: "1.25rem", fontWeight: 600 },
        button: { textTransform: "none", fontWeight: 600 },
        body1: { fontSize: "1rem", lineHeight: 1.6 },
    },
    palette: {
        mode: "light",
        primary: {
            main: "#000000", // Pure Black
            contrastText: "#ffffff",
        },
        secondary: {
            main: "#333333", // Dark Grey
        },
        background: {
            default: "#ffffff", // Pure White
            paper: "#ffffff",
        },
        text: {
            primary: "#000000",
            secondary: "#525252",
        },
        divider: "#e5e5e5",
    },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: "8px",
                    boxShadow: "none",
                    padding: "8px 16px",
                    // DEFAULT HOVER
                    "&:hover": {
                        boxShadow: "none",
                        // Do NOT force color/bg here universally as it breaks variants
                    },
                },
                containedPrimary: {
                    backgroundColor: "#000000",
                    color: "#ffffff",
                    "&:hover": {
                        backgroundColor: "#333333", // Dark Grey
                        color: "#ffffff"
                    },
                },
                outlined: {
                    borderColor: "#e5e5e5",
                    color: "#000000",
                    "&:hover": {
                        borderColor: "#000000",
                        backgroundColor: "#f5f5f5", // Light Grey
                        color: "#000000" // Ensure Black Text
                    },
                },
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: {
                    backgroundImage: "none",
                    borderRadius: "12px",
                    border: "1px solid #e5e5e5",
                    boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)",
                },
            },
        },
        MuiChip: {
            styleOverrides: {
                root: {
                    fontWeight: 500,
                    borderRadius: "6px",
                },
                filled: {
                    backgroundColor: "#f5f5f5",
                    color: "#000000",
                }
            }
        },
        MuiTextField: {
            styleOverrides: {
                root: {
                    "& .MuiOutlinedInput-root": {
                        borderRadius: "8px",
                    }
                }
            }
        }
    },
});
