"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useMutation } from "@tanstack/react-query";

interface ChatProps {
    baseFilename: string;
    jobDescription: string;
    initialScore: number;
}

interface ChatMessage {
    role: "user" | "assistant";
    content: string;
    version?: string;
    score?: number;
    summary?: string;
}

export default function ChatInterface({ baseFilename, jobDescription, initialScore }: ChatProps) {
    // History starts with the base optimized version
    const [messages, setMessages] = useState<ChatMessage[]>([{
        role: "assistant",
        content: `I've created the initial optimized resume (v1). It has a predicted score of ${initialScore}%. How would you like to refine it?`,
        version: "v1",
        score: initialScore
    }]);

    const [input, setInput] = useState("");
    const [currentVersion, setCurrentVersion] = useState("v1");
    const [versions, setVersions] = useState<string[]>(["v1"]);

    const refineMutation = useMutation({
        mutationFn: async (userReq: string) => {
            const nextVer = `v${versions.length + 1}`;
            const currentFilename = `${baseFilename}_${currentVersion}.tex`;
            const outputFilename = `${baseFilename}_${nextVer}`;

            // Special case for v1 if the file was just "Optimized_Resume.tex" (base)
            // Ideally backend handles clean naming, but assuming we standardized on base_vX
            // If current is v1, we might need to look for just baseFilename if v1 doesn't exist?
            // For simplicity, let's assume the Dashboard saves the first one as baseFilename_v1 OR we handle it here.

            // Safe bet: Pass the actual filename of the current version being viewed
            const actualCurrentFilename = currentVersion === "v1" ? baseFilename : `${baseFilename}_${currentVersion}`;

            return await api.post("/actions/refine", {
                current_tex_filename: actualCurrentFilename,
                user_request: userReq,
                output_filename: outputFilename,
                job_description: jobDescription
            });
        },
        onSuccess: (res, userReq) => {
            const data = res.data;
            const nextVer = `v${versions.length + 1}`;

            const newMsg: ChatMessage = {
                role: "assistant",
                content: `I've updated the resume based on your request: "${data.refinement.summary}".`,
                version: nextVer,
                score: data.analysis?.ats_score,
                summary: data.refinement.summary
            };

            setMessages(prev => [...prev, newMsg]);
            setVersions(prev => [...prev, nextVer]);
            setCurrentVersion(nextVer);
        },
        onError: (err) => {
            setMessages(prev => [...prev, { role: "assistant", content: `Error: ${err.message}` }]);
        }
    });

    const handleSend = () => {
        if (!input.trim() || refineMutation.isPending) return;

        const userMsg: ChatMessage = { role: "user", content: input };
        setMessages(prev => [...prev, userMsg]);
        refineMutation.mutate(input);
        setInput("");
    };

    return (
        <div className="card bg-base-100 border border-base-300 shadow-xl h-[800px] flex flex-col">
            <div className="p-4 border-b border-base-300 flex justify-between items-center bg-base-200/50">
                <h3 className="font-bold text-lg">💬 Refinement Chat</h3>
                <div className="tabs tabs-boxed tabs-sm">
                    {versions.map(v => (
                        <a key={v} className={`tab ${currentVersion === v ? 'tab-active' : ''}`} onClick={() => setCurrentVersion(v)}>{v}</a>
                    ))}
                </div>
            </div>

            <div className="flex-1 overflow-hidden flex">
                {/* PDF PREVIEW PANEL */}
                <div className="w-1/2 bg-base-200 p-2 flex flex-col">
                    <div className="flex justify-between items-center mb-2 px-2">
                        <span className="text-xs font-mono opacity-50">
                            Viewing: {currentVersion === "v1" ? baseFilename : `${baseFilename}_${currentVersion}`}.pdf
                        </span>

                        {/* Download Links */}
                        <div className="join">
                            <a
                                href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/files/output/${currentVersion === "v1" ? baseFilename : `${baseFilename}_${currentVersion}`}.pdf`}
                                target="_blank"
                                className="btn btn-xs join-item"
                            >
                                PDF
                            </a>
                            <a
                                href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/files/output/${currentVersion === "v1" ? baseFilename : `${baseFilename}_${currentVersion}`}.tex`}
                                target="_blank"
                                className="btn btn-xs join-item"
                            >
                                TeX
                            </a>
                        </div>
                    </div>

                    {/* IFRAME PDF PREVIEW */}
                    {/* Note: We need a way to serve static files. Currently backend runs on 8000 but nginx is on 80. 
                        We don't have a dedicated static file server for /data unless we add a route. 
                        Wait, we don't have a GET /files/download endpoint in the plan yet, 
                        only list. We need to add one or use Nginx to serve /data/users/... 
                        For now, let's assume we can add a simple download endpoint to FilesController.
                        Actually, let's just make sure the user can download. Visual preview might fail without a blob link.
                    */}
                    <div className="flex-1 flex items-center justify-center bg-white/5 rounded">
                        <p className="text-sm opacity-50">PDF Preview (Download to view)</p>
                    </div>
                </div>

                {/* CHAT PANEL */}
                <div className="w-1/2 flex flex-col border-l border-base-300">
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {messages.map((m, i) => (
                            <div key={i} className={`chat ${m.role === 'user' ? 'chat-end' : 'chat-start'}`}>
                                <div className={`chat-bubble ${m.role === 'user' ? 'chat-bubble-primary' : 'chat-bubble-secondary'}`}>
                                    {m.content}
                                    {m.score && (
                                        <div className="mt-2 pt-2 border-t border-white/20 text-xs">
                                            ATS Score: {m.score}%
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        {refineMutation.isPending && <div className="loading loading-dots loading-sm ml-4"></div>}
                    </div>

                    <div className="p-4 border-t border-base-300 bg-base-100">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                className="input input-bordered flex-1"
                                placeholder="E.g., Make the summary more punchy..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            />
                            <button className="btn btn-primary" onClick={handleSend} disabled={refineMutation.isPending}>
                                Send
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
