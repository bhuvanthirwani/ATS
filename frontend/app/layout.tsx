import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import QueryProvider from "@/lib/query-provider";

const outfit = Outfit({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "ATS Resume Tailorer",
    description: "Advanced Resume Optimization System",
};

import ThemeRegistry from "@/components/ThemeRegistry";

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={outfit.className}>
                <QueryProvider>
                    <ThemeRegistry>
                        {children}
                    </ThemeRegistry>
                </QueryProvider>
            </body>
        </html>
    );
}
