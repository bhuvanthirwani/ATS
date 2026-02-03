"use client";

import { api } from "@/lib/api";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import ChatInterface from "@/components/features/ChatInterface";

export default function Dashboard() {
    const [jobDescription, setJobDescription] = useState("");
    const [selectedTemplate, setSelectedTemplate] = useState("");
    const [selectedProfile, setSelectedProfile] = useState("");
    const [analysisResult, setAnalysisResult] = useState<any>(null);

    // Keyword Filtering State
    const [ignoredKeywords, setIgnoredKeywords] = useState<Set<string>>(new Set());

    const [optimizationResult, setOptimizationResult] = useState<any>(null);
    const [customFilename, setCustomFilename] = useState("Optimized_Resume");

    // Data Loading
    const templates = useQuery({ queryKey: ["templates"], queryFn: async () => (await api.get("/files/templates")).data });
    const profiles = useQuery({ queryKey: ["profiles"], queryFn: async () => (await api.get("/files/profiles")).data });

    // Actions
    const analyzeMutation = useMutation({
        mutationFn: async () => {
            const res = await api.post("/actions/analyze", {
                template_filename: selectedTemplate,
                job_description: jobDescription
            });
            return res.data;
        },
        onSuccess: (data) => setAnalysisResult(data)
    });

    const optimizeMutation = useMutation({
        mutationFn: async (variables: { ignored_keywords: string[] }) => {
            const res = await api.post("/actions/optimize", {
                template_filename: selectedTemplate,
                profile_filename: selectedProfile,
                job_description: jobDescription,
                analysis_result: analysisResult,
                output_filename: customFilename,
                ignored_keywords: variables.ignored_keywords || []
            });
            return res.data;
        },
        onSuccess: (data) => setOptimizationResult(data)
    });

    const toggleKeyword = (keyword: string) => {
        const next = new Set(ignoredKeywords);
        if (next.has(keyword)) next.delete(keyword);
        else next.add(keyword);
        setIgnoredKeywords(next);
    }

    const handleOptimization = () => {
        optimizeMutation.mutate({
            ignored_keywords: Array.from(ignoredKeywords)
        });
    }

    return (
        <div className="space-y-8 max-w-6xl mx-auto">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold">🚀 Resume Studio</h1>
            </div>

            {/* STEP 1: INPUTS */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="card bg-base-200 p-6 border border-white/5 space-y-4">
                    <h2 className="text-xl font-semibold">1. Configuration</h2>

                    {/* Template Select */}
                    <div className="form-control">
                        <label className="label">
                            <span className="label-text">Select Template (.tex)</span>
                        </label>
                        <select
                            className="select select-bordered w-full"
                            value={selectedTemplate}
                            onChange={(e) => setSelectedTemplate(e.target.value)}
                        >
                            <option value="" disabled>Choose a template...</option>
                            {templates.data?.map((t: string) => <option key={t} value={t}>{t}</option>)}
                        </select>
                    </div>

                    {/* Profile Select */}
                    <div className="form-control">
                        <label className="label">
                            <span className="label-text">Select Profile (.pdf)</span>
                        </label>
                        <select
                            className="select select-bordered w-full"
                            value={selectedProfile}
                            onChange={(e) => setSelectedProfile(e.target.value)}
                        >
                            <option value="" disabled>Choose a LinkedIn Profile...</option>
                            {profiles.data?.map((p: string) => <option key={p} value={p}>{p}</option>)}
                        </select>
                    </div>

                    {/* Filename */}
                    <div className="form-control">
                        <label className="label">
                            <span className="label-text">Output Filename</span>
                        </label>
                        <input
                            type="text"
                            className="input input-bordered w-full"
                            value={customFilename}
                            onChange={(e) => setCustomFilename(e.target.value)}
                        />
                    </div>
                </div>

                <div className="card bg-base-200 p-6 border border-white/5 flex flex-col h-full">
                    <h2 className="text-xl font-semibold mb-4">2. Job Description</h2>
                    <textarea
                        className="textarea textarea-bordered flex-1 w-full text-base"
                        placeholder="Paste the Job Description here including title, responsibilities, and requirements..."
                        value={jobDescription}
                        onChange={(e) => setJobDescription(e.target.value)}
                    ></textarea>
                </div>
            </div>

            {/* STEP 2: ACTIONS */}
            <div className="flex gap-4">
                <button
                    className="btn btn-primary flex-1"
                    disabled={!selectedTemplate || !jobDescription || analyzeMutation.isPending}
                    onClick={() => analyzeMutation.mutate()}
                >
                    {analyzeMutation.isPending ? "Analyzing..." : "🔍 Phase 1: Analyze Match"}
                </button>

                <button
                    className="btn btn-secondary flex-1"
                    disabled={!analysisResult || !selectedProfile || optimizeMutation.isPending}
                    onClick={handleOptimization}
                >
                    {optimizeMutation.isPending ? "Optimizing..." : "✨ Phase 2: Optimize & Generate"}
                </button>
            </div>

            {/* RESULTS AREA */}
            {(analysisResult || optimizeMutation.error) && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">

                    {/* Analysis Card */}
                    <div className="card bg-base-300 border border-primary/20 p-6">
                        <h3 className="text-lg font-bold mb-4">📊 Analysis Report</h3>
                        {analyzeMutation.error && <p className="text-error">Error: {JSON.stringify(analyzeMutation.error)}</p>}

                        {analysisResult && (
                            <div className="space-y-4">
                                <div className="stats shadow w-full bg-base-100">
                                    <div className="stat place-items-center">
                                        <div className="stat-title">ATS Match Score</div>
                                        <div className="stat-value text-primary">{analysisResult.ats_score}%</div>
                                        <div className="stat-desc">Target: 80%+</div>
                                    </div>
                                </div>

                                <div>
                                    <span className="font-bold text-success">✅ Matched: </span>
                                    <span className="text-sm opacity-80">{analysisResult.matched_keywords.join(", ")}</span>
                                </div>
                                <div>
                                    <span className="font-bold text-error">❌ Missing (Select to Ignore): </span>
                                    <div className="flex flex-wrap gap-2 mt-2">
                                        {analysisResult.missing_keywords.map((k: string) => (
                                            <button
                                                key={k}
                                                onClick={() => toggleKeyword(k)}
                                                className={`badge ${ignoredKeywords.has(k) ? 'badge-ghost opacity-50 line-through' : 'badge-error'} cursor-pointer gap-2 p-3`}
                                            >
                                                {k}
                                                {ignoredKeywords.has(k) && <span>✕</span>}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="collapse collapse-arrow bg-base-200 mt-2">
                                    <input type="checkbox" />
                                    <div className="collapse-title font-medium">
                                        See Detailed Justification
                                    </div>
                                    <div className="collapse-content text-sm">
                                        <p><strong>Role Fit:</strong> {analysisResult.justification.role_fit}</p>
                                        <p className="mt-2"><strong>Skill Depth:</strong> {analysisResult.justification.skill_depth}</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Optimization Results */}
                    <div className="card bg-base-300 border border-secondary/20 p-6">
                        <h3 className="text-lg font-bold mb-4">🚀 Optimization Result</h3>

                        {!optimizationResult && !optimizeMutation.isPending && (
                            <div className="flex items-center justify-center h-48 opacity-50 text-center">
                                Waiting for Phase 2...
                            </div>
                        )}

                        {optimizeMutation.isPending && (
                            <div className="flex items-center justify-center h-48">
                                <span className="loading loading-bars loading-lg text-secondary"></span>
                            </div>
                        )}

                        {optimizationResult && (
                            <div className="space-y-4">
                                <div className="stats shadow w-full bg-base-100">
                                    <div className="stat place-items-center">
                                        <div className="stat-title">New Predicted Score</div>
                                        <div className="stat-value text-secondary">{optimizationResult.optimization.final_score}%</div>
                                    </div>
                                </div>

                                <div className="alert alert-success text-sm">
                                    <span>✅ PDF Generated Successfully at <strong>/output/{customFilename}.pdf</strong></span>
                                </div>

                                <div className="collapse collapse-arrow bg-base-200">
                                    <input type="checkbox" />
                                    <div className="collapse-title font-medium">
                                        View Applied Changes
                                    </div>
                                    <div className="collapse-content text-sm">
                                        <ul className="list-disc pl-4">
                                            {optimizationResult.optimization.summary.map((s: string, i: number) => (
                                                <li key={i}>{s}</li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* STEP 3: Chat Iteration */}
            {optimizationResult && (
                <div className="animate-in fade-in slide-in-from-bottom-8 duration-700">
                    <ChatInterface
                        baseFilename={customFilename}
                        jobDescription={jobDescription}
                        initialScore={optimizationResult.optimization.final_score}
                    />
                </div>
            )}

        </div>
    );
}
