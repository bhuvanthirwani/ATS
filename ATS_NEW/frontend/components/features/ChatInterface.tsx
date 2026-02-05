"use client";

import { useState, useEffect } from "react";
import { api, getAuthToken } from "@/lib/api";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
    Box, Paper, Typography, Button, IconButton,
    TextField, CircularProgress, Stack, Chip,
    Tooltip, Divider, ToggleButtonGroup, ToggleButton
} from "@mui/material";
import {
    Send as SendIcon,
    Download as DownloadIcon,
    CheckCircle as CheckCircleIcon,
    History as HistoryIcon,
    Description as DescriptionIcon,
    Code as CodeIcon,
    PictureAsPdf as PdfIcon,
    ContentCopy as CopyIcon,
    OpenInNew as OpenInNewIcon,
    AutoFixHigh as SparklesIcon,
    Edit as EditIcon
} from "@mui/icons-material";

interface ChatProps {
    baseFilename: string; // The base name without _vX suffix
    jobDescription: string;
    initialScore: number;
    initialScore: number;
    initialWorkflowId: string; // NEW: Required for fetching files
    initialError?: string; // NEW: Capture initial compilation error
}

interface Version {
    id: string;      // "v1", "v2"
    filename: string; // "Optimized_Resume_v1"
    score: number;
    timestamp: string;
    summary: string;
    status: 'current' | 'generating' | 'completed' | 'error';
    error?: string; // Specific error message
}

export default function ResumePreview({ baseFilename, jobDescription, initialScore, initialWorkflowId, initialError }: ChatProps) {
    // STATE
    const [viewMode, setViewMode] = useState<'resume' | 'job' | 'code'>('resume');
    const [currentVersionId, setCurrentVersionId] = useState("v1");
    const [workflowId, setWorkflowId] = useState(initialWorkflowId); // Store workflow ID
    const [refinementInput, setRefinementInput] = useState("");
    const [latexSource, setLatexSource] = useState(""); // For manual editing
    const [isManualCompiling, setIsManualCompiling] = useState(false);

    // Fetch TeX Content
    const getDownloadUrl = (ext: 'pdf' | 'tex' | 'log') => {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
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
            id: "v1",
            filename: baseFilename, // e.g., "Resume_Optimized"
            score: initialScore,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            summary: "Initial Optimization",
            status: initialError ? 'error' : 'completed',
            error: initialError
        }
    ]);

    const currentVersion = versions.find(v => v.id === currentVersionId) || versions[0];

    // MUTATION
    const refineMutation = useMutation({
        mutationFn: async (userReq: string) => {
            const nextId = `v${versions.length + 1}`;
            const nextFilename = `${baseFilename}_${nextId}`; // "Resume_Optimized_v2"

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
                workflow_id: workflowId, // Send ID
                current_version: currentVersionId, // Send current version e.g "v1"
                current_tex_filename: currentVersion.filename,
                user_request: userReq,
                output_filename: nextFilename,
                job_description: jobDescription,
                target_version: nextId // Explicitly set next version
            });
            return { ...res.data, versionId: nextId };
        },
        onSuccess: (data) => {
            const isSuccess = data.compilation?.success !== false;
            setVersions(prev => prev.map(v =>
                v.id === data.versionId
                    ? {
                        ...v,
                        score: data.analysis?.ats_score || 0,
                        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                        status: isSuccess ? 'completed' : 'error',
                        summary: data.refinement.summary,
                        error: isSuccess ? undefined : (data.compilation?.error || "Unknown Verification Error")
                    }
                    : v
            ));
            setRefinementInput("");
        },
        onError: (err) => {
            // Revert or mark error
            console.error(err);
        }
    });

    // MANUAL COMPILE HANDLER
    const handleManualCompile = async () => {
        if (!latexSource.trim()) return;
        setIsManualCompiling(true);
        const nextId = `v${versions.length + 1}`; // Ensure always unique next step
        const nextFilename = `${baseFilename}_${nextId}`;

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
                                <object
                                    key={currentVersion.filename}
                                    data={getDownloadUrl('pdf') + "#toolbar=0&navpanes=0&scrollbar=0"}
                                    type="application/pdf"
                                    width="100%"
                                    height="100%"
                                    style={{ borderRadius: 8, border: 'none' }}
                                >
                                    <Box sx={{
                                        height: '100%',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        bgcolor: 'error.50',
                                        p: 3,
                                        textAlign: 'center'
                                    }}>
                                        <Typography variant="h6" color="error" gutterBottom>
                                            PDF Not Compiled
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                            Error in LaTeX Code. Please check the source or try regenerating.
                                        </Typography>

                                        {currentVersion.error && (
                                            <Paper
                                                variant="outlined"
                                                sx={{
                                                    p: 2,
                                                    bgcolor: 'grey.900',
                                                    color: 'error.light',
                                                    fontFamily: 'monospace',
                                                    fontSize: '0.75rem',
                                                    textAlign: 'left',
                                                    width: '100%',
                                                    maxHeight: 200,
                                                    overflow: 'auto',
                                                    mb: 2
                                                }}
                                            >
                                                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                                                    {currentVersion.error.slice(0, 500)}
                                                    {currentVersion.error.length > 500 && "..."}
                                                </pre>
                                            </Paper>
                                        )}

                                        <Button
                                            href={getDownloadUrl('log')}
                                            target="_blank"
                                            size="small"
                                            color="error"
                                        >
                                            View Compilation Log
                                        </Button>
                                    </Box>
                                </object>
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
        </Paper>
    );
}
