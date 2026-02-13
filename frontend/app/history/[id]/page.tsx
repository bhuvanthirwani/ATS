"use client";

import { api, getBaseUrl, getAuthToken } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import {
    Container, Typography, Box, Paper, List, ListItem, ListItemText,
    ListItemIcon, Divider, Chip, CircularProgress, Button, Breadcrumbs, Link,
    Card, CardContent, Grid
} from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import DescriptionIcon from "@mui/icons-material/Description";
import ChatIcon from "@mui/icons-material/Chat";
import { formatDistanceToNow } from "date-fns";
import React, { useState } from "react";
import ChatInterface from "@/components/features/ChatInterface";
import { Dialog, Slide } from "@mui/material";

const Transition = React.forwardRef(function Transition(props: any, ref: any) {
    return <Slide direction="up" ref={ref} {...props} />;
});

export default function WorkflowDetailsPage() {
    const params = useParams();
    const router = useRouter();
    const workflowId = params.id as string;

    // State for Preview/Refine Modal
    const [isPreviewOpen, setIsPreviewOpen] = useState(false);
    const [selectedJob, setSelectedJob] = useState<any>(null);

    const buildDownloadUrl = (version: string, filename: string) => {
        const baseUrl = getBaseUrl();
        const token = getAuthToken();
        return `${baseUrl}/files/workflows/${workflowId}/${version}/${filename}?token=${token}`;
    };

    const { data: workflow, isLoading } = useQuery({
        queryKey: ["workflow", workflowId],
        queryFn: async () => (await api.get(`/actions/workflows/${workflowId}`)).data,
        enabled: !!workflowId,
        refetchInterval: 5000
    });

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "SUCCESS":
            case "completed":
                return <CheckCircleIcon color="success" />;
            case "FAILURE":
            case "failed":
                return <ErrorIcon color="error" />;
            default:
                return <AccessTimeIcon color="warning" />;
        }
    };

    const handleRefine = (job: any) => {
        setSelectedJob(job);
        setIsPreviewOpen(true);
    };

    if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 10 }}><CircularProgress /></Box>;
    if (!workflow) return <Container><Typography variant="h5" sx={{ mt: 5 }}>Workflow not found</Typography></Container>;

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            {/* Breadcrumbs */}
            <Breadcrumbs sx={{ mb: 3 }}>
                <Link color="inherit" href="/dashboard" onClick={(e) => { e.preventDefault(); router.push('/dashboard'); }}>
                    Dashboard
                </Link>
                <Link color="inherit" href="/history" onClick={(e) => { e.preventDefault(); router.push('/history'); }}>
                    History
                </Link>
                <Typography color="text.primary">Details</Typography>
            </Breadcrumbs>

            {/* Header */}
            <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h4" fontWeight="bold" gutterBottom>
                        {workflow.template_filename.replace('.tex', '')}
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Profile: {workflow.profile_filename}
                    </Typography>
                </Box>
                <Chip label={`ID: ${workflow.id.substring(0, 8)}`} />
            </Box>

            <Grid container spacing={3}>
                {/* Workflow Info */}
                <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 3 }}>
                        <Typography variant="h6" gutterBottom>Job Description</Typography>
                        <Divider sx={{ mb: 2 }} />
                        <Typography variant="body2" sx={{ maxHeight: 300, overflowY: 'auto' }}>
                            {workflow.job_description}
                        </Typography>
                    </Paper>
                </Grid>

                {/* Job Versions */}
                <Grid item xs={12} md={8}>
                    <Paper sx={{ p: 3 }}>
                        <Typography variant="h6" gutterBottom>Versions & Attempts</Typography>
                        <Divider sx={{ mb: 2 }} />

                        <List>
                            {workflow.jobs?.sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).map((job: any) => (
                                <ListItem key={job.id} divider sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', py: 2 }}>
                                    <Box sx={{ display: 'flex', width: '100%', alignItems: 'center', mb: 1 }}>
                                        <ListItemIcon>
                                            {getStatusIcon(job.status)}
                                        </ListItemIcon>
                                        <ListItemText
                                            primary={job.result_data?.version ? `Version ${job.result_data.version}` : "Processing..."}
                                            secondary={formatDistanceToNow(new Date(job.created_at)) + " ago"}
                                        />
                                        <Chip label={job.status} color={job.status === "SUCCESS" ? "success" : job.status === "FAILED" ? "error" : "default"} size="small" />
                                    </Box>

                                    {job.status === "SUCCESS" && job.result_data && (
                                        <Box sx={{ ml: 7, width: '100%' }}>
                                            <Box sx={{ display: 'flex', gap: 2, mb: 1 }}>
                                                <Typography variant="body2">
                                                    <strong>Score:</strong> {job.result_data.optimization?.final_score ?? job.result_data.refinement?.final_score ?? "N/A"}%
                                                </Typography>
                                            </Box>
                                            <Box sx={{ display: 'flex', gap: 2 }}>
                                                <Button
                                                    variant="outlined"
                                                    size="small"
                                                    startIcon={<DescriptionIcon />}
                                                    href={buildDownloadUrl(job.result_data.version, job.result_data.compilation.output_filename ? job.result_data.compilation.output_filename + '.tex' : 'resume.tex')}
                                                    target="_blank"
                                                >
                                                    TeX
                                                </Button>
                                                <Button
                                                    variant="outlined"
                                                    size="small"
                                                    startIcon={<InsertDriveFileIcon />}
                                                    href={buildDownloadUrl(job.result_data.version, job.result_data.compilation.pdf_path?.split('/').pop() || 'resume.pdf')}
                                                    target="_blank"
                                                >
                                                    PDF
                                                </Button>
                                                <Button
                                                    variant="contained"
                                                    size="small"
                                                    startIcon={<ChatIcon />}
                                                    onClick={() => handleRefine(job)}
                                                >
                                                    Refine with AI
                                                </Button>
                                            </Box>
                                        </Box>
                                    )}
                                    {job.status === "FAILED" && (
                                        <Typography variant="caption" color="error" sx={{ ml: 7 }}>
                                            Error: {job.error_message}
                                        </Typography>
                                    )}
                                </ListItem>
                            ))}
                        </List>
                    </Paper>
                </Grid>
            </Grid>

            {/* PREVIEW/REFINE MODAL */}
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
                    {selectedJob && (
                        <ChatInterface
                            baseFilename={selectedJob.result_data?.compilation?.output_filename || workflow.template_filename.replace('.tex', '') + "_Optimized"}
                            jobDescription={workflow.job_description}
                            initialScore={selectedJob.result_data.optimization?.final_score}
                            initialWorkflowId={workflow.id}
                            initialError={undefined}
                            initialVersion={selectedJob.result_data?.version || "v1"}
                        />
                    )}
                </Box>
            </Dialog>
        </Container>
    );
}
