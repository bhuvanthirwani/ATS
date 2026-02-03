"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearAuth, getUsername } from "@/lib/api";
import { useEffect, useState } from "react";

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [workspaceId, setWorkspaceId] = useState<string | null>(null);
    const [username, setUsername] = useState<string | null>(null);

    useEffect(() => {
        setWorkspaceId(getUsername());
        setUsername(getUsername());
    }, []);

    const handleLogout = () => {
        clearAuth();
        router.push("/");
    };

    const navItems = [
        { name: "📊 Dashboard", path: "/dashboard" },
        { name: "📂 Files", path: "/files" },
        { name: "⚙️ Settings", path: "/settings" },
    ];

    return (
        <div className="w-64 min-h-screen bg-base-200/50 backdrop-blur-md border-r border-white/5 flex flex-col p-4">
            <div className="mb-8">
                <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">
                    ATS PRO
                </h1>
                {username && (
                    <p className="text-xs text-gray-400 mt-2">Logged in as: <span className="font-mono text-primary">{username}</span></p>
                )}
            </div>

            <nav className="flex-1 space-y-2">
                {navItems.map((item) => (
                    <Link
                        key={item.path}
                        href={item.path}
                        className={`flex items-center px-4 py-3 rounded-xl transition-all duration-200 ${pathname === item.path
                            ? "bg-primary text-white shadow-lg shadow-primary/20"
                            : "hover:bg-white/5 text-gray-300 hover:text-white"
                            }`}
                    >
                        {item.name}
                    </Link>
                ))}
            </nav>

            <button
                onClick={handleLogout}
                className="btn btn-ghost w-full justify-start text-red-400 hover:bg-red-500/10 mt-auto"
            >
                🚪 Logout
            </button>
        </div>
    );
}
