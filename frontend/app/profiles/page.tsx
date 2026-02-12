"use client";

import { api } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
    Container, Typography, Box, Paper, Grid, Button,
    IconButton, List, ListItem, ListItemText, ListItemAvatar,
    Avatar, CircularProgress, Alert, Divider
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DescriptionIcon from "@mui/icons-material/Description";
import LinkedInIcon from "@mui/icons-material/LinkedIn";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import PersonIcon from "@mui/icons-material/Person";

export default function ProfilesPage() {
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
        mutationFn: async ({ filename, type }: { filename: string; type: "template" | "profile" }) => {
            const endpoint = type === "template" ? `/files/templates/${filename}` : `/files/profiles/${filename}`;
            return api.delete(endpoint);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["templates"] });
            queryClient.invalidateQueries({ queryKey: ["profiles"] });
        }
    });

    const handleUpload = (e: React.ChangeEvent<HTMLInputElement>, type: "template" | "profile") => {
        if (e.target.files?.[0]) {
            setUploading(true);
            uploadMutation.mutate({ file: e.target.files[0], type });
        }
    };

    return (
        <Container maxWidth="lg">
            <Box sx={{ mb: 4 }}>
                <Typography variant="h4" fontWeight="bold">File Management</Typography>
            </Box>

            <Grid container spacing={4}>
                {/* TEMPLATES CARD */}
                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 3, height: '100%' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                            <Typography variant="h6" display="flex" alignItems="center" gap={1}>
                                <DescriptionIcon color="primary" /> Resume Templates
                            </Typography>
                            <Button
                                component="label"
                                variant="contained"
                                startIcon={uploading ? <CircularProgress size={20} color="inherit" /> : <CloudUploadIcon />}
                                disabled={uploading}
                            >
                                Upload
                                <input type="file" accept=".tex,.txt" hidden onChange={(e) => handleUpload(e, "template")} />
                            </Button>
                        </Box>

                        <Divider />

                        <List sx={{ mt: 2 }}>
                            {!templates.data?.length && (
                                <Box sx={{ p: 2, textAlign: 'center', opacity: 0.6 }}>
                                    <Typography variant="body2">No templates found.</Typography>
                                </Box>
                            )}
                            {templates.data?.map((file: string) => (
                                <ListItem
                                    key={file}
                                    secondaryAction={
                                        <IconButton edge="end" aria-label="delete" onClick={() => deleteMutation.mutate({ filename: file, type: "template" })}>
                                            <DeleteIcon color="error" />
                                        </IconButton>
                                    }
                                >
                                    <ListItemAvatar>
                                        <Avatar sx={{ bgcolor: 'primary.main' }}>
                                            <InsertDriveFileIcon />
                                        </Avatar>
                                    </ListItemAvatar>
                                    <ListItemText
                                        primary={file}
                                        primaryTypographyProps={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
                                    />
                                </ListItem>
                            ))}
                        </List>
                    </Paper>
                </Grid>

                {/* PROFILES CARD */}
                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 3, height: '100%' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                            <Typography variant="h6" display="flex" alignItems="center" gap={1}>
                                <LinkedInIcon color="secondary" /> LinkedIn Profiles
                            </Typography>
                            <Button
                                component="label"
                                variant="contained"
                                color="secondary"
                                startIcon={uploading ? <CircularProgress size={20} color="inherit" /> : <CloudUploadIcon />}
                                disabled={uploading}
                            >
                                Upload
                                <input type="file" accept=".pdf" hidden onChange={(e) => handleUpload(e, "profile")} />
                            </Button>
                        </Box>

                        <Divider />

                        <List sx={{ mt: 2 }}>
                            {!profiles.data?.length && (
                                <Box sx={{ p: 2, textAlign: 'center', opacity: 0.6 }}>
                                    <Typography variant="body2">No profiles found.</Typography>
                                </Box>
                            )}
                            {profiles.data?.map((file: string) => (
                                <ListItem
                                    key={file}
                                    secondaryAction={
                                        <IconButton edge="end" aria-label="delete" onClick={() => deleteMutation.mutate({ filename: file, type: "profile" })}>
                                            <DeleteIcon color="error" />
                                        </IconButton>
                                    }
                                >
                                    <ListItemAvatar>
                                        <Avatar sx={{ bgcolor: 'secondary.main' }}>
                                            <PersonIcon />
                                        </Avatar>
                                    </ListItemAvatar>
                                    <ListItemText
                                        primary={file}
                                        primaryTypographyProps={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
                                    />
                                </ListItem>
                            ))}
                        </List>
                    </Paper>
                </Grid>
            </Grid>
        </Container>
    );
}
