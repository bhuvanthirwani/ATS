"use client";

import { api } from "@/lib/api";
import { useQuery, useMutation } from "@tanstack/react-query";
import React, { useState, useEffect } from "react";
import ChatInterface from "@/components/features/ChatInterface";
import JobsList from "@/components/features/JobsList";
import {
    Container, Typography, Box, Stepper, Step, StepLabel,
    Grid, Paper, FormControl, InputLabel, Select, MenuItem,
    TextField, Button, Chip, CircularProgress, Alert,
    Collapse, List, ListItem, ListItemText, Divider,
    Card, CardContent, Link as MuiLink,
    Dialog, DialogContent, Slide,
    Drawer, Fab
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import DownloadIcon from "@mui/icons-material/Download";
import HistoryIcon from "@mui/icons-material/History";

const Transition = React.forwardRef(function Transition(props: any, ref: any) {
    return <Slide direction="up" ref={ref} {...props} />;
});

export default function Dashboard() {
    const [jobDescription, setJobDescription] = useState("");
    const [selectedTemplate, setSelectedTemplate] = useState("");
    const [selectedProfile, setSelectedProfile] = useState("");
    const [analysisResult, setAnalysisResult] = useState<any>(null);
    const [ignoredKeywords, setIgnoredKeywords] = useState<Set<string>>(new Set());

    // Async Job State
    const [activeJobId, setActiveJobId] = useState<string | null>(null);
    const [jobStatus, setJobStatus] = useState<string>("");
    const [optimizationResult, setOptimizationResult] = useState<any>(null);

    const [customFilename, setCustomFilename] = useState("Optimized_Resume");
    const [isJobsDrawerOpen, setIsJobsDrawerOpen] = useState(false);

    // Data Loading
    const templates = useQuery({ queryKey: ["templates"], queryFn: async () => (await api.get("/files/templates")).data });
    const profiles = useQuery({ queryKey: ["profiles"], queryFn: async () => (await api.get("/files/profiles")).data });

    // Polling for Active Job
    useQuery({
        queryKey: ["jobStatus", activeJobId],
        queryFn: async () => {
            if (!activeJobId) return null;
            const res = await api.get(`/actions/jobs/${activeJobId}`);
            const data = res.data;

            setJobStatus(data.status);

            if (data.status === "completed" || data.status === "SUCCESS") {
                setOptimizationResult(data.result);
                // Also open preview if it was the just-triggered job
                if (!optimizationResult) {
                    setIsPreviewOpen(true);
                }
                setActiveJobId(null); // Stop polling
            } else if (data.status === "failed" || data.status === "FAILURE") {
                setActiveJobId(null); // Stop polling
                alert(`Job Failed: ${data.error}`);
            }
            return data;
        },
        enabled: !!activeJobId,
        refetchInterval: 2000 // Poll every 2s
    });

    // Actions
    const analyzeMutation = useMutation({
        mutationFn: async () => {
            // AUTO-FILL FILENAME LOGIC
            if (selectedTemplate) {
                const baseName = selectedTemplate.replace(/\.[^/.]+$/, "");
                setCustomFilename(baseName + "_Optimized");
            }

            const res = await api.post("/actions/analyze", {
                template_filename: selectedTemplate,
                profile_filename: selectedProfile,
                job_description: jobDescription
            });
            return res.data;
        },
        onSuccess: (data) => setAnalysisResult(data)
    });

    // State for Preview Modal
    const [isPreviewOpen, setIsPreviewOpen] = useState(false);
    const [workflowId, setWorkflowId] = useState("");

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
        onSuccess: (data) => {
            // Async Flow: We get a job_id
            if (data.job_id) {
                setActiveJobId(data.job_id);
                setJobStatus("processing");
            } else {
                // Fallback (Legacy Sync)
                setOptimizationResult(data);
                setWorkflowId(data.workflow_id);
                setIsPreviewOpen(true);
            }
        }
    });

    const handleOptimization = () => {
        optimizeMutation.mutate({ ignored_keywords: Array.from(ignoredKeywords) });
    };

    // Handle selecting a past job
    const handleSelectJob = async (jobId: string) => {
        try {
            const res = await api.get(`/actions/jobs/${jobId}`);
            if (res.data.status === "completed" || res.data.status === "SUCCESS") {
                setOptimizationResult(res.data.result);
                setWorkflowId(res.data.result.workflow_id);
                setIsPreviewOpen(true);
            } else {
                alert(`Job is ${res.data.status}`);
            }
        } catch (e) {
            console.error(e);
        }
    };

    const toggleKeyword = (keyword: string) => {
        const newSet = new Set(ignoredKeywords);
        if (newSet.has(keyword)) newSet.delete(keyword);
        else newSet.add(keyword);
        setIgnoredKeywords(newSet);
    };

    // calculate active step
    let activeStep = 0;
    if (analysisResult) activeStep = 1;
    if (optimizationResult) activeStep = 3; // Completed

    return (
        <Container maxWidth="xl" sx={{ pb: 10 }}>
            <Box sx={{ mb: 4, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <Typography variant="h4" fontWeight="bold">
                    🚀 Resume Studio
                </Typography>
                <Button
                    startIcon={<HistoryIcon />}
                    variant="outlined"
                    onClick={() => setIsJobsDrawerOpen(true)}
                >
                    Job History
                </Button>
            </Box>

            <Stepper activeStep={activeStep} sx={{ mb: 6 }}>
                <Step><StepLabel>Setup & Analyze</StepLabel></Step>
                <Step><StepLabel>Review & Optimize</StepLabel></Step>
                <Step><StepLabel>Download</StepLabel></Step>
            </Stepper>

            <Grid container spacing={4}>
                {/* COLUMN 1: Inputs */}
                <Grid item xs={12} lg={4}>
                    <Paper sx={{ p: 3, height: '100%' }}>
                        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Chip label="1" color="primary" size="small" /> Configuration
                        </Typography>

                        <FormControl fullWidth margin="normal">
                            <InputLabel>Target Template (.tex)</InputLabel>
                            <Select
                                value={selectedTemplate}
                                label="Target Template (.tex)"
                                onChange={(e) => setSelectedTemplate(e.target.value)}
                                disabled={analyzeMutation.isPending || !!analysisResult}
                            >
                                {templates.data?.map((t: string) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                            </Select>
                        </FormControl>

                        <FormControl fullWidth margin="normal">
                            <InputLabel>Source Profile (.pdf)</InputLabel>
                            <Select
                                value={selectedProfile}
                                label="Source Profile (.pdf)"
                                onChange={(e) => setSelectedProfile(e.target.value)}
                                disabled={analyzeMutation.isPending || !!analysisResult}
                            >
                                {profiles.data?.map((p: string) => <MenuItem key={p} value={p}>{p}</MenuItem>)}
                            </Select>
                        </FormControl>

                        {analysisResult && (
                            <Button
                                variant="outlined"
                                color="warning"
                                fullWidth
                                startIcon={<RefreshIcon />}
                                sx={{ mt: 2 }}
                                onClick={() => {
                                    setAnalysisResult(null);
                                    setOptimizationResult(null);
                                    setJobDescription("");
                                }}
                            >
                                Start Over
                            </Button>
                        )}
                    </Paper>
                </Grid>

                {/* COLUMN 2: Actions */}
                <Grid item xs={12} lg={8}>
                    {!analysisResult && (
                        <Paper sx={{ p: 3 }}>
                            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Chip label="2" color="primary" size="small" /> Job Description
                            </Typography>
                            <TextField
                                fullWidth
                                multiline
                                rows={10}
                                placeholder="Paste Job Description here..."
                                value={jobDescription}
                                onChange={(e) => setJobDescription(e.target.value)}
                                variant="outlined"
                                sx={{ mb: 2 }}
                            />
                            <Box display="flex" justifyContent="flex-end">
                                <Button
                                    variant="contained"
                                    size="large"
                                    disabled={!selectedTemplate || !selectedProfile || !jobDescription || analyzeMutation.isPending}
                                    onClick={() => analyzeMutation.mutate()}
                                    startIcon={analyzeMutation.isPending ? <CircularProgress size={20} /> : <CloudUploadIcon />}
                                >
                                    {analyzeMutation.isPending ? "Analyzing..." : "Phase 1: Analyze Match"}
                                </Button>
                            </Box>
                            {analyzeMutation.error && (
                                <Alert severity="error" sx={{ mt: 2 }}>{JSON.stringify(analyzeMutation.error)}</Alert>
                            )}
                        </Paper>
                    )}

                    {analysisResult && (
                        <Paper sx={{ p: 3, mb: 4 }}>
                            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Chip label="3" color="secondary" size="small" /> Analysis & Optimization
                            </Typography>

                            <Grid container spacing={2} sx={{ mb: 3 }}>
                                <Grid item xs={12} md={4}>
                                    <Card variant="outlined">
                                        <CardContent sx={{ textAlign: 'center' }}>
                                            <Typography color="textSecondary" gutterBottom>Match Score</Typography>
                                            <Typography variant="h3" color="primary.main" fontWeight="bold">
                                                {analysisResult.ats_score}%
                                            </Typography>
                                            <Typography variant="caption">Target: 80%+</Typography>
                                        </CardContent>
                                    </Card>
                                </Grid>
                                <Grid item xs={12} md={8}>
                                    <Box sx={{ mb: 2 }}>
                                        <Typography variant="subtitle2" color="success.main" fontWeight="bold">✅ Matched Keywords</Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            {analysisResult.matched_keywords.join(", ")}
                                        </Typography>
                                    </Box>
                                    <Divider />
                                    <Box sx={{ mt: 2 }}>
                                        <Typography variant="subtitle2" color="error.main" fontWeight="bold">❌ Missing (Click to Ignore)</Typography>
                                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                                            {analysisResult.missing_keywords.map((k: string) => (
                                                <Chip
                                                    key={k}
                                                    label={k}
                                                    color={ignoredKeywords.has(k) ? "default" : "error"}
                                                    variant={ignoredKeywords.has(k) ? "outlined" : "filled"}
                                                    onClick={() => toggleKeyword(k)}
                                                    onDelete={ignoredKeywords.has(k) ? undefined : () => toggleKeyword(k)}
                                                    deleteIcon={ignoredKeywords.has(k) ? undefined : <span>×</span>}
                                                    sx={{ textDecoration: ignoredKeywords.has(k) ? 'line-through' : 'none' }}
                                                />
                                            ))}
                                        </Box>
                                    </Box>
                                </Grid>
                            </Grid>

                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                <TextField
                                    label="Output Filename"
                                    value={customFilename}
                                    onChange={(e) => setCustomFilename(e.target.value)}
                                    size="small"
                                    fullWidth
                                />
                                <Button
                                    variant="contained"
                                    color="secondary"
                                    size="large"
                                    fullWidth
                                    disabled={optimizeMutation.isPending || !!optimizationResult || !!activeJobId}
                                    onClick={handleOptimization}
                                    startIcon={(optimizeMutation.isPending || !!activeJobId) ? <CircularProgress size={20} /> : <AutoFixHighIcon />}
                                >
                                    {activeJobId ? "Optimizing (Async)..." : optimizeMutation.isPending ? "Generating..." : "Phase 2: Optimize PDF"}
                                </Button>
                            </Box>
                            {(optimizeMutation.isPending || activeJobId) && (
                                <Box sx={{ width: '100%', mt: 2, textAlign: 'center' }}>
                                    {activeJobId && <Typography variant="caption">Processing Job ID: {activeJobId}</Typography>}
                                    <CircularProgress />
                                </Box>
                            )}
                        </Paper>
                    )}

                    {optimizationResult && (
                        <Paper sx={{ p: 3, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider' }}>
                            <Typography variant="h5" color="success.main" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                ✅ Success!
                            </Typography>

                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                <Typography>Your optimized resume is ready.</Typography>
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                    <Button
                                        variant="outlined"
                                        startIcon={<AutoFixHighIcon />}
                                        onClick={() => setIsPreviewOpen(true)}
                                    >
                                        Preview & Refine
                                    </Button>
                                    <Button
                                        component={MuiLink}
                                        href={`/api/v1/files/workflows/${optimizationResult.workflow_id || workflowId}/v1/${customFilename}_v1.pdf`}
                                        target="_blank"
                                        variant="contained"
                                        color="success"
                                        startIcon={<DownloadIcon />}
                                    >
                                        Download PDF
                                    </Button>
                                </Box>
                            </Box>

                            <Card variant="outlined">
                                <CardContent>
                                    <Typography variant="h6">New Score: {optimizationResult.optimization.final_score}%</Typography>
                                    <Box sx={{ mt: 1 }}>
                                        <Typography variant="subtitle2">Changes Applied:</Typography>
                                        <List dense>
                                            {optimizationResult.optimization.summary.map((s: string, i: number) => (
                                                <ListItem key={i}>
                                                    <ListItemText primary={s} sx={{ '& .MuiListItemText-primary': { fontSize: '0.9rem' } }} />
                                                </ListItem>
                                            ))}
                                        </List>
                                    </Box>
                                </CardContent>
                            </Card>
                        </Paper>
                    )}

                    {/* PREVIEW MODAL */}
                    <Dialog
                        open={isPreviewOpen}
                        onClose={() => {
                            setIsPreviewOpen(false);
                            document.body.style.overflow = "auto";
                        }}
                        TransitionComponent={Transition}
                        fullScreen
                        PaperProps={{
                            sx: { bgcolor: 'background.default' }
                        }}
                    >
                        <Box sx={{ display: 'flex', justifyContent: 'flex-end', p: 2, bgcolor: 'white' }}>
                            <Button onClick={() => {
                                setIsPreviewOpen(false);
                                document.body.style.overflow = "auto";
                            }}>Close Preview</Button>
                        </Box>
                        <Box sx={{ height: 'calc(100vh - 60px)', p: 2 }}>
                            {optimizationResult && (
                                <ChatInterface
                                    baseFilename={customFilename}
                                    jobDescription={jobDescription}
                                    initialScore={optimizationResult.optimization.final_score}
                                    initialWorkflowId={optimizationResult.workflow_id || workflowId}
                                    initialError={optimizationResult.compilation?.success === false ? optimizationResult.compilation?.error : undefined}
                                />
                            )}
                        </Box>
                    </Dialog>

                    {/* JOBS DRAWER */}
                    <Drawer
                        anchor="right"
                        open={isJobsDrawerOpen}
                        onClose={() => setIsJobsDrawerOpen(false)}
                    >
                        <Box sx={{ width: 350, height: '100%', p: 0 }}>
                            <JobsList
                                activeJobId={activeJobId || undefined}
                                onSelectJob={(id) => {
                                    handleSelectJob(id);
                                    setIsJobsDrawerOpen(false);
                                }}
                            />
                        </Box>
                    </Drawer>
                </Grid>
            </Grid>
        </Container>
    );
}
