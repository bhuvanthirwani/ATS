"use client";

import { useState, useEffect } from "react";
import { api, getAuthToken, getBaseUrl } from "@/lib/api";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
    Box, Paper, Typography, Button, IconButton,
    TextField, CircularProgress, Stack, Chip,
    Tooltip, Divider, ToggleButtonGroup, ToggleButton
} from "@mui/material";
import HistoryIcon from "@mui/icons-material/History";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import DescriptionIcon from "@mui/icons-material/Description";
import CodeIcon from "@mui/icons-material/Code";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import DownloadIcon from "@mui/icons-material/Download";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";

// Alias icons for usage in JSX
const PdfIcon = PictureAsPdfIcon;
const CopyIcon = ContentCopyIcon;
const SparklesIcon = AutoAwesomeIcon;

interface ChatProps {
    baseFilename: string;
    jobDescription: string;
    initialScore: number;
    initialWorkflowId: string;
    initialError?: string;
    currentVersion?: string;
    initialVersion?: string; // New prop
}

interface Version {
    id: string;
    filename: string;
    score: number;
    timestamp: string;
    summary: string;
    status: 'completed' | 'generating' | 'error';
    error?: string;
}
export default function ResumePreview({ baseFilename, jobDescription, initialScore, initialWorkflowId, initialError, initialVersion = "v1" }: ChatProps) {
    // ... state ...
    const [workflowId, setWorkflowId] = useState(initialWorkflowId);
    const [currentVersionId, setCurrentVersionId] = useState(initialVersion);
    const [viewMode, setViewMode] = useState<"resume" | "job" | "code">("resume");
    const [latexSource, setLatexSource] = useState("");
    const [refinementInput, setRefinementInput] = useState("");
    const [isManualCompiling, setIsManualCompiling] = useState(false);

    // Fetch TeX Content
    const getDownloadUrl = (ext: 'pdf' | 'tex' | 'log') => {
        const baseUrl = getBaseUrl();
        const token = getAuthToken(); // Get token from local storage
        return `${baseUrl}/files/workflows/${workflowId}/${currentVersionId}/${currentVersion.filename}.${ext}?token=${token}`;
    };

    const { data: latexContent, isLoading: isLatexLoading } = useQuery({
        queryKey: ["latex", workflowId, currentVersionId],
        queryFn: async () => {
            if (viewMode !== 'code') return "";
            try {
                const url = getDownloadUrl('tex');
                const res = await fetch(url);
                if (!res.ok) throw new Error("Failed to load LaTeX");
                const text = await res.text();
                setLatexSource(text); // Initialize editor
                return text;
            } catch (e) {
                console.error(e);
                return "Error loading LaTeX source.";
            }
        },
        enabled: viewMode === 'code' && !!workflowId
    });

    // Initial Version
    const [versions, setVersions] = useState<Version[]>([
        {
            id: initialVersion,
            filename: baseFilename, // e.g., "Resume_Optimized"
            score: initialScore,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            summary: "Initial Optimization",
            status: initialError ? 'error' : 'completed',
            error: initialError
        }
    ]);

    const currentVersion = versions.find(v => v.id === currentVersionId) || versions[0];

    // Helper to get next version ID
    const getNextVersionId = () => {
        const maxV = versions.reduce((max, v) => {
            const match = v.id.match(/^v(\d+)$/);
            return match ? Math.max(max, parseInt(match[1])) : max;
        }, 0);
        return `v${maxV + 1}`;
    };

    // DEBUG LOGGING
    useEffect(() => {
        console.log("Current Version State:", currentVersion);
        console.log("All Versions:", versions);
        console.log("Refinement Input:", refinementInput);
        console.log("Download URL (PDF):", getDownloadUrl('pdf'));
    }, [currentVersion, versions, refinementInput]); // varied dep array for debugging

    // Poll for refine job result
    const pollRefineJob = (jobId: string, versionId: string) => {
        const interval = setInterval(async () => {
            try {
                const res = await api.get(`/actions/jobs/${jobId}`);
                const data = res.data;

                if (data.status === "SUCCESS" || data.status === "completed") {
                    clearInterval(interval);
                    const result = data.result;
                    const isSuccess = result?.compilation?.success !== false;
                    setVersions(prev => prev.map(v =>
                        v.id === versionId
                            ? {
                                ...v,
                                score: result?.analysis?.ats_score || 0,
                                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                                status: isSuccess ? 'completed' : 'error',
                                summary: result?.refinement?.summary || v.summary,
                                filename: result?.compilation?.output_filename || v.filename,
                                error: isSuccess ? undefined : (result?.compilation?.error || "Unknown Error")
                            }
                            : v
                    ));
                } else if (data.status === "FAILED" || data.status === "FAILURE") {
                    clearInterval(interval);
                    setVersions(prev => prev.map(v =>
                        v.id === versionId
                            ? { ...v, status: 'error', timestamp: 'Failed', error: data.error || "Refinement failed" }
                            : v
                    ));
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 2000);
    };

    // MUTATION
    const refineMutation = useMutation({
        mutationFn: async (userReq: string) => {
            const nextId = getNextVersionId();
            const nextFilename = `${baseFilename.replace(/_v\d+$/, '')}_${nextId}`; // "Resume_Optimized_v2" - clean base first just in case

            // Optimistic Update
            const newVer: Version = {
                id: nextId,
                filename: nextFilename,
                score: 0,
                timestamp: "Generating...",
                summary: userReq,
                status: 'generating'
            };
            setVersions(prev => [newVer, ...prev]); // Add to top
            setCurrentVersionId(nextId);

            const res = await api.post("/actions/refine", {
                workflow_id: workflowId,
                current_version: currentVersionId,
                current_tex_filename: currentVersion.filename,
                user_request: userReq,
                output_filename: nextFilename,
                job_description: jobDescription,
                target_version: nextId
            });
            return { ...res.data, versionId: nextId };
        },
        onSuccess: (data) => {
            // Start polling for the async job result
            if (data.job_id) {
                pollRefineJob(data.job_id, data.versionId);
            }
            setRefinementInput("");
        },
        onError: (err) => {
            console.error(err);
        }
    });

    // MANUAL COMPILE HANDLER
    const handleManualCompile = async () => {
        if (!latexSource.trim()) return;
        setIsManualCompiling(true);
        const nextId = getNextVersionId();
        const nextFilename = `${baseFilename.replace(/_v\d+$/, '')}_${nextId}`;

        // Optimistic Update
        const newVer: Version = {
            id: nextId,
            filename: nextFilename,
            score: 0,
            timestamp: "Compiling...",
            summary: "Manual Edit",
            status: 'generating'
        };
        setVersions(prev => [newVer, ...prev]);
        setCurrentVersionId(nextId);
        setViewMode('resume'); // Switch back to see result

        try {
            const res = await api.post("/actions/compile_new_version", {
                workflow_id: workflowId,
                latex_code: latexSource,
                target_version: nextId,
                output_filename: nextFilename
            });

            const isSuccess = res.data.compilation?.success !== false;

            setVersions(prev => prev.map(v =>
                v.id === nextId ? {
                    ...v,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    status: isSuccess ? 'completed' : 'error',
                    error: isSuccess ? undefined : (res.data.compilation?.error || "Unknown Verification Error")
                } : v
            ));

        } catch (error: any) {
            console.error(error);
            setVersions(prev => prev.map(v =>
                v.id === nextId ? { ...v, status: 'error', error: "Network Error" } : v
            ));
        } finally {
            setIsManualCompiling(false);
        }
    };


    const handleRefine = () => {
        if (!refinementInput.trim() || refineMutation.isPending) return;
        refineMutation.mutate(refinementInput);
    };

    // COPY PROMPT HELPER
    const copyPrompt = () => {
        // Mock prompt for now or fetch from backend if available
        navigator.clipboard.writeText(`Refine the resume to... ${currentVersion.summary}`);
    };

    // URL helper moved up for useQuery access
    // const getDownloadUrl ... removed from here

    return (
        <Paper
            elevation={4}
            sx={{
                height: '850px',
                display: 'flex',
                overflow: 'hidden',
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider'
            }}
        >
            {/* SIDEBAR: VERSION HISTORY */}
            <Box sx={{
                width: 280,
                borderRight: '1px solid',
                borderColor: 'divider',
                bgcolor: 'grey.50',
                display: 'flex',
                flexDirection: 'column'
            }}>
                <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider', bgcolor: 'white' }}>
                    <Typography variant="subtitle1" fontWeight="bold" color="primary.main">
                        <HistoryIcon sx={{ verticalAlign: 'middle', mr: 1, fontSize: 20 }} />
                        Version History
                    </Typography>
                </Box>

                <Box sx={{ flex: 1, overflowY: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {versions.map((ver) => (
                        <Paper
                            key={ver.id}
                            variant="outlined"
                            onClick={() => setCurrentVersionId(ver.id)}
                            sx={{
                                p: 2,
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                border: currentVersionId === ver.id ? '2px solid' : '1px solid',
                                borderColor: currentVersionId === ver.id ? 'primary.main' : 'divider',
                                bgcolor: currentVersionId === ver.id ? 'primary.50' : 'white',
                                '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' }
                            }}
                        >
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    {ver.status === 'generating' ? (
                                        <CircularProgress size={14} />
                                    ) : (
                                        <Typography variant="caption" fontWeight="bold" sx={{ color: 'text.secondary' }}>
                                            {ver.id.toUpperCase()}
                                        </Typography>
                                    )}
                                    <Typography variant="caption" color="text.disabled">
                                        {ver.timestamp}
                                    </Typography>
                                </Box>

                                {ver.score > 0 && (
                                    <Chip
                                        label={`${ver.score}%`}
                                        size="small"
                                        color={ver.score >= 90 ? "success" : ver.score >= 80 ? "warning" : "error"}
                                        sx={{ height: 20, fontSize: '0.65rem', fontWeight: 'bold' }}
                                    />
                                )}
                            </Box>

                            <Typography variant="body2" sx={{
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical',
                                overflow: 'hidden',
                                fontSize: '0.8rem',
                                color: 'text.primary',
                                opacity: 0.9
                            }}>
                                {ver.summary}
                            </Typography>
                        </Paper>
                    ))}
                </Box>
            </Box>

            {/* MAIN CONTENT AREA */}
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', bgcolor: '#f8fafc' }}>

                {/* TOOLBAR */}
                <Box sx={{
                    p: 1.5,
                    bgcolor: 'white',
                    borderBottom: '1px solid',
                    borderColor: 'divider',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    {/* View Toggles */}
                    <ToggleButtonGroup
                        value={viewMode}
                        exclusive
                        onChange={(_, v) => v && setViewMode(v)}
                        size="small"
                        sx={{ height: 36 }}
                    >
                        <ToggleButton value="resume">
                            <PdfIcon sx={{ mr: 1, fontSize: 18 }} /> Resume
                        </ToggleButton>
                        <ToggleButton value="job">
                            <DescriptionIcon sx={{ mr: 1, fontSize: 18 }} /> JD
                        </ToggleButton>
                        <ToggleButton value="code">
                            <CodeIcon sx={{ mr: 1, fontSize: 18 }} /> LaTeX
                        </ToggleButton>
                    </ToggleButtonGroup>

                    {/* Actions */}
                    <Stack direction="row" spacing={1}>
                        <Button
                            variant="outlined"
                            size="small"
                            startIcon={<CopyIcon />}
                            onClick={copyPrompt}
                            sx={{ color: 'text.secondary', borderColor: 'divider' }}
                        >
                            Copy Prompt
                        </Button>
                        <Button
                            variant="outlined"
                            size="small"
                            startIcon={<OpenInNewIcon />}
                            href="https://chat.openai.com"
                            target="_blank"
                            sx={{ color: 'text.secondary', borderColor: 'divider' }}
                        >
                            ChatGPT
                        </Button>
                        <Button
                            variant="outlined"
                            size="small"
                            startIcon={<DescriptionIcon />}
                            href={getDownloadUrl('tex')}
                            target="_blank"
                            sx={{ color: 'text.secondary', borderColor: 'divider' }}
                        >
                            TeX
                        </Button>
                        <Button
                            variant="contained"
                            size="small"
                            startIcon={<DownloadIcon />}
                            href={getDownloadUrl('pdf')}
                            target="_blank"
                            color="primary"
                        >
                            Download PDF
                        </Button>
                    </Stack>
                </Box>

                {/* VIEWPORT */}
                <Box sx={{ flex: 1, overflow: 'hidden', position: 'relative' }}>

                    {/* RESUME VIEW */}
                    {viewMode === 'resume' && (
                        <Box sx={{ width: '100%', height: '100%', bgcolor: 'grey.200', p: 3, display: 'flex', justifyContent: 'center' }}>
                            {currentVersion.status === 'generating' ? (
                                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                                    <CircularProgress size={40} thickness={4} />
                                    <Typography sx={{ mt: 2, color: 'text.secondary' }}>Generating Resume PDF...</Typography>
                                </Box>
                            ) : (
                                <embed
                                    key={currentVersion.filename}
                                    src={`${getDownloadUrl('pdf')}&t=${currentVersion.status === 'completed' ? currentVersion.timestamp : Date.now()}#toolbar=0&navpanes=0&scrollbar=0`}
                                    type="application/pdf"
                                    width="100%"
                                    height="100%"
                                    style={{ borderRadius: 8, border: 'none' }}
                                />


                            )}
                        </Box>
                    )}

                    {/* JOB DESC VIEW */}
                    {viewMode === 'job' && (
                        <Box sx={{ p: 4, height: '100%', overflowY: 'auto', bgcolor: 'white' }}>
                            <Typography variant="h6" gutterBottom color="primary">Job Description</Typography>
                            <Divider sx={{ mb: 2 }} />
                            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', color: 'text.secondary', lineHeight: 1.6 }}>
                                {jobDescription}
                            </Typography>
                        </Box>
                    )}

                    {/* LATEX CODE VIEW (Manual Edit) */}
                    {viewMode === 'code' && (
                        <Box sx={{ p: 0, height: '100%', bgcolor: '#1e1e1e', display: 'flex', flexDirection: 'column' }}>
                            <Box sx={{ p: 2, borderBottom: '1px solid #333', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="subtitle2" sx={{ color: '#aaa', fontFamily: 'monospace' }}>
                                    {currentVersion.filename}.tex
                                </Typography>
                                <Button
                                    size="small"
                                    startIcon={<CheckCircleIcon />}
                                    onClick={handleManualCompile}
                                    variant="contained"
                                    color="success"
                                    disabled={isManualCompiling}
                                >
                                    {isManualCompiling ? "Compiling..." : "Save & Compile New Version"}
                                </Button>
                            </Box>
                            <Box sx={{ flex: 1, overflow: 'auto', p: 0 }}>
                                {isLatexLoading ? (
                                    <Box sx={{ p: 4, textAlign: 'center' }}>
                                        <CircularProgress size={24} sx={{ color: 'grey.500' }} />
                                    </Box>
                                ) : (
                                    <textarea
                                        style={{
                                            width: '100%',
                                            height: '100%',
                                            backgroundColor: '#1e1e1e',
                                            color: '#d4d4d4',
                                            fontFamily: 'Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace',
                                            fontSize: '13px',
                                            padding: '16px',
                                            border: 'none',
                                            resize: 'none',
                                            outline: 'none',
                                            lineHeight: 1.5,
                                        }}
                                        value={latexSource}
                                        onChange={(e) => setLatexSource(e.target.value)}
                                        spellCheck={false}
                                    />
                                )}
                            </Box>
                        </Box>
                    )}
                </Box>

                {/* REFINEMENT FOOTER */}
                <Paper
                    elevation={3}
                    sx={{
                        p: 2,
                        borderTop: '1px solid',
                        borderColor: 'divider',
                        bgcolor: 'background.paper',
                        zIndex: 10
                    }}
                >
                    <Box sx={{ display: 'flex', gap: 2, maxWidth: 1200, mx: 'auto' }}>
                        <TextField
                            fullWidth
                            placeholder="Describe changes to refine this version (e.g. 'Add more keywords for React', 'Make summary stronger')..."
                            value={refinementInput}
                            onChange={(e) => setRefinementInput(e.target.value)}
                            size="medium"
                            InputProps={{
                                sx: { bgcolor: 'white' }
                            }}
                            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleRefine()}
                        />
                        <Button
                            variant="contained"
                            size="large"
                            onClick={handleRefine}
                            disabled={!refinementInput.trim() || refineMutation.isPending}
                            startIcon={refineMutation.isPending ? <CircularProgress size={20} color="inherit" /> : <SparklesIcon />}
                            sx={{ minWidth: 140, bgcolor: 'secondary.main', '&:hover': { bgcolor: 'secondary.dark' } }}
                        >
                            {refineMutation.isPending ? "Refining..." : "Refine"}
                        </Button>
                    </Box>
                </Paper>
            </Box>
        </Paper >
    );
}
