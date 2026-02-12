"use client";

import { useEffect, useState } from "react";
import {
    Container, Typography, Box, Paper, Chip,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    IconButton, Tooltip, CircularProgress
} from "@mui/material";
import HistoryIcon from "@mui/icons-material/History";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import { Download as DownloadIcon, Description as DescriptionIcon, PictureAsPdf as PdfIcon } from "@mui/icons-material";
import { api, getAuthToken, getBaseUrl } from "@/lib/api";

interface HistoryItem {
    id: string;
    workflow_id: string;
    version: string;
    action: string;
    details: string;
    date: string;
    status: string;
    files: string[];
}

export default function HistoryPage() {
    const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const res = await api.get("/files/history");
                setHistoryItems(res.data);
            } catch (err) {
                console.error("Failed to fetch history", err);
            } finally {
                setLoading(false);
            }
        };

        fetchHistory();
    }, []);

    const getDownloadUrl = (workflowId: string, version: string, filename: string) => {
        const baseUrl = getBaseUrl();
        const token = getAuthToken();
        return `${baseUrl}/files/workflows/${workflowId}/${version}/${filename}?token=${token}`;
    };

    return (
        <Container maxWidth="xl">
            <Box sx={{ mb: 4 }}>
                <Typography variant="h4" fontWeight="bold">Activity History</Typography>
            </Box>

            <Paper sx={{ p: 3 }}>
                <Typography variant="h6" display="flex" alignItems="center" gap={1} gutterBottom>
                    <HistoryIcon color="primary" /> Recent Optimizations
                </Typography>

                {loading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                        <CircularProgress />
                    </Box>
                ) : (
                    <TableContainer>
                        <Table>
                            <TableHead>
                                <TableRow>
                                    <TableCell>Status</TableCell>
                                    <TableCell>Date</TableCell>
                                    <TableCell>Action</TableCell>
                                    <TableCell>Workflow ID</TableCell>
                                    <TableCell>Version</TableCell>
                                    <TableCell>Filename</TableCell>
                                    <TableCell align="right">Downloads</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {historyItems.map((item) => (
                                    <TableRow key={item.id} hover>
                                        <TableCell>
                                            <CheckCircleOutlineIcon color="success" fontSize="small" />
                                        </TableCell>
                                        <TableCell sx={{ whiteSpace: 'nowrap' }}>
                                            <Typography variant="body2" color="text.secondary">{item.date}</Typography>
                                        </TableCell>
                                        <TableCell>{item.action}</TableCell>
                                        <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                                            {item.workflow_id.slice(0, 8)}...
                                        </TableCell>
                                        <TableCell>
                                            <Chip label={item.version} size="small" variant="outlined" />
                                        </TableCell>
                                        <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {item.details}
                                        </TableCell>
                                        <TableCell align="right">
                                            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                                                <Tooltip title="Download PDF">
                                                    <IconButton
                                                        size="small"
                                                        color="primary"
                                                        href={getDownloadUrl(item.workflow_id, item.version, item.details)}
                                                        target="_blank"
                                                    >
                                                        <PdfIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                                <Tooltip title="Download TeX source">
                                                    <IconButton
                                                        size="small"
                                                        color="default"
                                                        href={getDownloadUrl(item.workflow_id, item.version, item.details.replace(".pdf", ".tex"))}
                                                        target="_blank"
                                                    >
                                                        <DescriptionIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                            </Box>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )}

                {!loading && historyItems.length === 0 && (
                    <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
                        <Typography>No history available yet.</Typography>
                    </Box>
                )}
            </Paper>
        </Container>
    );
}
