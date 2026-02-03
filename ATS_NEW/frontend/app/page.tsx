"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setAuthToken } from "@/lib/api";

export default function Home() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<"login" | "register">("login");
    const [formData, setFormData] = useState({
        username: "",
        email: "",
        password: ""
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            if (activeTab === "register") {
                const res = await api.post("/auth/register", formData);
                setAuthToken(res.data.access_token, res.data.username);
                router.push("/dashboard");
            } else {
                // Login
                const res = await api.post("/auth/login", {
                    username: formData.username,
                    password: formData.password
                });
                setAuthToken(res.data.access_token, res.data.username);
                router.push("/dashboard");
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || "Authentication failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-4 relative overflow-hidden">
            {/* Background blobs */}
            <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-primary/20 rounded-full blur-[100px]" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-secondary/20 rounded-full blur-[100px]" />

            <div className="z-10 text-center mb-8">
                <h1 className="text-6xl font-black mb-2 bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">
                    ATS PRO
                </h1>
                <p className="text-xl opacity-80">AI-Powered Resume Architecture</p>
            </div>

            <div className="card w-full max-w-md bg-base-100 shadow-2xl border border-white/10 backdrop-blur-md">
                <div className="card-body">

                    {/* TABS */}
                    <div className="tabs tabs-boxed mb-6 bg-base-200">
                        <a className={`tab flex-1 ${activeTab === 'login' ? 'tab-active' : ''}`} onClick={() => setActiveTab('login')}>Login</a>
                        <a className={`tab flex-1 ${activeTab === 'register' ? 'tab-active' : ''}`} onClick={() => setActiveTab('register')}>Register</a>
                    </div>

                    <h2 className="card-title justify-center mb-4">
                        {activeTab === 'login' ? 'Welcome Back' : 'Create Account'}
                    </h2>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="form-control">
                            <label className="label">
                                <span className="label-text">Username</span>
                            </label>
                            <input
                                type="text"
                                placeholder="Unique username"
                                className="input input-bordered"
                                value={formData.username}
                                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                required
                            />
                        </div>

                        {activeTab === 'register' && (
                            <div className="form-control animate-in fade-in slide-in-from-top-2">
                                <label className="label">
                                    <span className="label-text">Email</span>
                                </label>
                                <input
                                    type="email"
                                    placeholder="name@example.com"
                                    className="input input-bordered"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    required
                                />
                            </div>
                        )}

                        <div className="form-control">
                            <label className="label">
                                <span className="label-text">Password</span>
                            </label>
                            <input
                                type="password"
                                placeholder="••••••••"
                                className="input input-bordered"
                                value={formData.password}
                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                required
                            />
                        </div>

                        {error && <div className="text-error text-sm text-center">{error}</div>}

                        <div className="form-control mt-6">
                            <button className="btn btn-primary" type="submit" disabled={loading}>
                                {loading ? <span className="loading loading-spinner"></span> : (activeTab === 'login' ? 'Login' : 'Register')}
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <div className="mt-8 text-sm opacity-50">
                Safe. Secure. Private.
            </div>
        </main>
    );
}
