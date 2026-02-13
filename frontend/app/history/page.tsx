"use client";

import { api, getBaseUrl, getAuthToken } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import {
    Container, Typography, Box, Paper, Chip, CircularProgress, Button,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    IconButton, Tooltip
} from "@mui/material";
import HistoryIcon from "@mui/icons-material/History";
import DescriptionIcon from "@mui/icons-material/Description";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { useRouter } from "next/navigation";
import { formatDistanceToNow } from "date-fns";

const getStatusColor = (status: string) => {
    const s = status?.toUpperCase();
    if (s === "SUCCESS" || s === "COMPLETED") return { bg: "#e8f5e9", color: "#2e7d32", border: "#c8e6c9" }; // Green
    if (s === "FAILED" || s === "FAILURE") return { bg: "#ffebee", color: "#c62828", border: "#ffcdd2" }; // Red
    if (s === "PENDING" || s === "PROCESSING") return { bg: "#fff3e0", color: "#ef6c00", border: "#ffe0b2" }; // Orange
    return { bg: "#f5f5f5", color: "#616161", border: "#e0e0e0" }; // Grey
};



const getDownloadUrl = (workflowId: string, version: string, filename: string) => {
    const baseUrl = getBaseUrl();
    const token = getAuthToken();
    return `${baseUrl}/files/workflows/${workflowId}/${version}/${filename}?token=${token}`;
};

export default function HistoryPage() {
    const router = useRouter();

    const { data: workflows, isLoading } = useQuery({
        queryKey: ["workflows"],
        queryFn: async () => (await api.get("/actions/workflows")).data,
        refetchInterval: 5000
    });

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Box sx={{ mb: 4 }}>
                <Typography variant="h4" fontWeight="bold">Activity History</Typography>
                <Typography variant="subtitle1" color="text.secondary">
                    Your resume optimization sessions
                </Typography>
            </Box>

            {isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                </Box>
            ) : workflows?.length === 0 ? (
                <Paper sx={{ p: 6, textAlign: 'center', color: 'text.secondary' }}>
                    <HistoryIcon sx={{ fontSize: 60, mb: 2, opacity: 0.5 }} />
                    <Typography variant="h6">No history found</Typography>
                    <Typography>Run an optimization to see it here.</Typography>
                    <Button variant="contained" sx={{ mt: 2 }} onClick={() => router.push('/dashboard')}>
                        Go to Dashboard
                    </Button>
                </Paper>
            ) : (
                <TableContainer component={Paper} variant="outlined">
                    <Table>
                        <TableHead>
                            <TableRow sx={{ bgcolor: 'grey.50' }}>
                                <TableCell sx={{ fontWeight: 'bold' }}>Workflow ID</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Versions</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Created</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }} align="right">Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {workflows?.map((workflow: any) => {
                                const jobs = workflow.jobs || [];
                                const sortedJobs = [...jobs].sort(
                                    (a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                                );
                                const latestJob = sortedJobs[0];
                                const status = latestJob?.status || "PENDING";
                                const isCompleted = status === "SUCCESS" || status === "completed";

                                // Resolve filenames from latest successful job
                                const successfulJob = sortedJobs.find(
                                    (j: any) => j.status === "SUCCESS" || j.status === "completed"
                                );
                                const version = successfulJob?.result_data?.version || "v1";
                                const outputFilename = successfulJob?.result_data?.compilation?.output_filename;
                                const pdfPath = successfulJob?.result_data?.compilation?.pdf_path;
                                const pdfName = pdfPath ? pdfPath.split('/').pop() : (outputFilename ? `${outputFilename}.pdf` : null);
                                const texName = outputFilename ? `${outputFilename}.tex` : null;

                                return (
                                    <TableRow
                                        key={workflow.id}
                                        hover
                                        sx={{ '&:last-child td': { borderBottom: 0 }, cursor: 'pointer' }}
                                        onClick={() => router.push(`/history/${workflow.id}`)}
                                    >
                                        <TableCell>
                                            <Chip
                                                label={workflow.id.substring(0, 8)}
                                                size="small"
                                                variant="filled"
                                                sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={`${jobs.length}`}
                                                size="small"
                                                variant="filled"
                                                sx={{
                                                    bgcolor: "#e3f2fd",
                                                    color: "#1565c0",
                                                    fontWeight: 'bold',
                                                    border: "1px solid #bbdefb"
                                                }}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={status}
                                                size="small"
                                                variant="filled"
                                                sx={{
                                                    bgcolor: getStatusColor(status).bg,
                                                    color: getStatusColor(status).color,
                                                    fontWeight: 'bold',
                                                    border: `1px solid ${getStatusColor(status).border}`
                                                }}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="caption" color="text.secondary" noWrap>
                                                {formatDistanceToNow(new Date(workflow.created_at))} ago
                                            </Typography>
                                        </TableCell>
                                        <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                                            <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 1 }}>
                                                {isCompleted && texName && pdfName && (
                                                    <>
                                                        <Tooltip title="Download TeX">
                                                            <IconButton
                                                                size="small"
                                                                component="a"
                                                                href={getDownloadUrl(workflow.id, version, texName)}
                                                                onClick={(e) => e.stopPropagation()}
                                                            >
                                                                <DescriptionIcon fontSize="small" />
                                                            </IconButton>
                                                        </Tooltip>
                                                        <Tooltip title="Download PDF">
                                                            <IconButton
                                                                size="small"
                                                                color="primary"
                                                                component="a"
                                                                href={getDownloadUrl(workflow.id, version, pdfName)}
                                                                target="_blank"
                                                                onClick={(e) => e.stopPropagation()}
                                                            >
                                                                <PictureAsPdfIcon fontSize="small" />
                                                            </IconButton>
                                                        </Tooltip>
                                                    </>
                                                )}
                                                <Button
                                                    size="small"
                                                    variant="contained"
                                                    endIcon={<ArrowForwardIcon />}
                                                    onClick={() => router.push(`/history/${workflow.id}`)}
                                                >
                                                    View/Edit
                                                </Button>
                                            </Box>
                                        </TableCell>
                                    </TableRow>
                                );
                            })}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}
        </Container>
    );
}
