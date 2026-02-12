"use client";

import { api } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

export default function FilesPage() {
    const queryClient = useQueryClient();
    const [uploading, setUploading] = useState(false);

    // Queries
    const templates = useQuery({ queryKey: ["templates"], queryFn: async () => (await api.get("/files/templates")).data });
    const profiles = useQuery({ queryKey: ["profiles"], queryFn: async () => (await api.get("/files/profiles")).data });

    // Mutations
    const uploadMutation = useMutation({
        mutationFn: async ({ file, type }: { file: File; type: "template" | "profile" }) => {
            const formData = new FormData();
            formData.append("file", file);
            const endpoint = type === "template" ? "/files/templates" : "/files/profiles";
            return api.post(endpoint, formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["templates"] });
            queryClient.invalidateQueries({ queryKey: ["profiles"] });
            setUploading(false);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: async ({ filename, type }: { filename: str; type: "template" | "profile" }) => {
            const endpoint = type === "template" ? `/files/templates/${filename}` : `/files/profiles/${filename}`;
            return api.delete(endpoint);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["templates"] });
            queryClient.invalidateQueries({ queryKey: ["profiles"] });
        }
    })

    const handleUpload = (e: React.ChangeEvent<HTMLInputElement>, type: "template" | "profile") => {
        if (e.target.files?.[0]) {
            setUploading(true);
            uploadMutation.mutate({ file: e.target.files[0], type });
        }
    };

    return (
        <div className="space-y-8 max-w-6xl mx-auto">
            <h1 className="text-3xl font-bold">📂 File Management</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

                {/* TEMPLATES CARD */}
                <div className="card bg-base-200/50 border border-white/5 p-6 backdrop-blur">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-xl font-semibold">Resume Templates (.tex)</h2>
                        <div className="tooltip" data-tip="Upload .tex file">
                            <label className={`btn btn-sm btn-primary ${uploading ? 'loading' : ''}`}>
                                📤 Upload
                                <input type="file" accept=".tex,.txt" className="hidden" onChange={(e) => handleUpload(e, "template")} />
                            </label>
                        </div>
                    </div>

                    <div className="space-y-2">
                        {!templates.data?.length && <p className="text-gray-500 text-sm">No templates found.</p>}
                        {templates.data?.map((file: string) => (
                            <div key={file} className="flex justify-between items-center bg-base-100 p-3 rounded-lg border border-white/5">
                                <span className="font-mono text-sm">📄 {file}</span>
                                <button
                                    onClick={() => deleteMutation.mutate({ filename: file, type: "template" })}
                                    className="btn btn-ghost btn-xs text-error">🗑️</button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* PROFILES CARD */}
                <div className="card bg-base-200/50 border border-white/5 p-6 backdrop-blur">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-xl font-semibold">LinkedIn Profiles (.pdf)</h2>
                        <div className="tooltip" data-tip="Upload .pdf file">
                            <label className={`btn btn-sm btn-secondary ${uploading ? 'loading' : ''}`}>
                                📤 Upload
                                <input type="file" accept=".pdf" className="hidden" onChange={(e) => handleUpload(e, "profile")} />
                            </label>
                        </div>
                    </div>

                    <div className="space-y-2">
                        {!profiles.data?.length && <p className="text-gray-500 text-sm">No profiles found.</p>}
                        {profiles.data?.map((file: string) => (
                            <div key={file} className="flex justify-between items-center bg-base-100 p-3 rounded-lg border border-white/5">
                                <span className="font-mono text-sm">🔗 {file}</span>
                                <button
                                    onClick={() => deleteMutation.mutate({ filename: file, type: "profile" })}
                                    className="btn btn-ghost btn-xs text-error">🗑️</button>
                            </div>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    );
}
