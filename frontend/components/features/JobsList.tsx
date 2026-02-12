import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
    Box, Typography, List, ListItem, ListItemText,
    Chip, CircularProgress, Paper, IconButton, Tooltip
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import AccessTimeIcon from "@mui/icons-material/AccessTime";

interface JobsListProps {
    onSelectJob: (jobId: string) => void;
    activeJobId?: string;
}

export default function JobsList({ onSelectJob, activeJobId }: JobsListProps) {
    const { data: jobs, isLoading, refetch } = useQuery({
        queryKey: ["jobs"],
        queryFn: async () => {
            const res = await api.get("/actions/jobs");
            return res.data;
        },
        refetchInterval: 5000 // Poll every 5s for list updates
    });

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "SUCCESS":
            case "completed":
                return <CheckCircleIcon color="success" fontSize="small" />;
            case "FAILURE":
            case "failed":
                return <ErrorIcon color="error" fontSize="small" />;
            default:
                return <CircularProgress size={16} />;
        }
    };

    return (
        <Paper sx={{ p: 2, height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" fontWeight="bold">
                    Recent Jobs
                </Typography>
                <Tooltip title="Refresh">
                    <IconButton size="small" onClick={() => refetch()}>
                        <RefreshIcon />
                    </IconButton>
                </Tooltip>
            </Box>

            {isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                </Box>
            ) : (
                <List sx={{ flexGrow: 1, overflowY: 'auto' }}>
                    {jobs?.map((job: any) => (
                        <ListItem
                            key={job.job_id}
                            button
                            onClick={() => onSelectJob(job.job_id)}
                            selected={activeJobId === job.job_id}
                            sx={{
                                mb: 1,
                                borderRadius: 1,
                                border: '1px solid',
                                borderColor: activeJobId === job.job_id ? 'primary.main' : 'divider',
                                bgcolor: activeJobId === job.job_id ? 'primary.light' : 'background.paper'
                            }}
                        >
                            <Box sx={{ mr: 2, display: 'flex', alignItems: 'center' }}>
                                {getStatusIcon(job.status)}
                            </Box>
                            <ListItemText
                                primary={`Job ${job.job_id.substring(0, 8)}...`}
                                secondary={job.status.toUpperCase()}
                                primaryTypographyProps={{ variant: 'body2', fontWeight: 600 }}
                                secondaryTypographyProps={{ variant: 'caption' }}
                            />
                        </ListItem>
                    ))}
                    {jobs?.length === 0 && (
                        <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 4 }}>
                            No jobs found.
                        </Typography>
                    )}
                </List>
            )}
        </Paper>
    );
}
