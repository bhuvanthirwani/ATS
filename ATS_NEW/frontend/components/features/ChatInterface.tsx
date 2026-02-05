"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useMutation } from "@tanstack/react-query";
import {
    Box, Paper, Typography, Tabs, Tab, TextField,
    Button, Chip, CircularProgress, Stack, Divider,
    IconButton
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import DownloadIcon from "@mui/icons-material/Download";

interface ChatProps {
    baseFilename: string;
    jobDescription: string;
    initialScore: number;
}

interface ChatMessage {
    role: "user" | "assistant";
    content: string;
    version?: string;
    score?: number;
    summary?: string;
}

export default function ChatInterface({ baseFilename, jobDescription, initialScore }: ChatProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([{
        role: "assistant",
        content: `I've created the initial optimized resume (v1). It has a predicted score of ${initialScore}%. How would you like to refine it?`,
        version: "v1",
        score: initialScore
    }]);

    const [input, setInput] = useState("");
    const [currentVersion, setCurrentVersion] = useState("v1");
    const [versions, setVersions] = useState<string[]>(["v1"]);

    const refineMutation = useMutation({
        mutationFn: async (userReq: string) => {
            const nextVer = `v${versions.length + 1}`;
            const actualCurrentFilename = currentVersion === "v1" ? baseFilename : `${baseFilename}_${currentVersion}`;
            const outputFilename = `${baseFilename}_${nextVer}`;

            return await api.post("/actions/refine", {
                current_tex_filename: actualCurrentFilename,
                user_request: userReq,
                output_filename: outputFilename,
                job_description: jobDescription
            });
        },
        onSuccess: (res) => {
            const data = res.data;
            const nextVer = `v${versions.length + 1}`;
            const newMsg: ChatMessage = {
                role: "assistant",
                content: `I've updated the resume based on your request: "${data.refinement.summary}".`,
                version: nextVer,
                score: data.analysis?.ats_score,
                summary: data.refinement.summary
            };

            setMessages(prev => [...prev, newMsg]);
            setVersions(prev => [...prev, nextVer]);
            setCurrentVersion(nextVer);
        },
        onError: (err) => {
            setMessages(prev => [...prev, { role: "assistant", content: `Error: ${err.message}` }]);
        }
    });

    const handleSend = () => {
        if (!input.trim() || refineMutation.isPending) return;
        const userMsg: ChatMessage = { role: "user", content: input };
        setMessages(prev => [...prev, userMsg]);
        refineMutation.mutate(input);
        setInput("");
    };

    return (
        <Paper elevation={3} sx={{ height: '800px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Box sx={{ p: 2, borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', bgcolor: 'background.paper' }}>
                <Typography variant="h6">💬 Refinement Chat</Typography>
                <Tabs
                    value={versions.indexOf(currentVersion)}
                    onChange={(_, idx) => setCurrentVersion(versions[idx])}
                    variant="scrollable"
                    scrollButtons="auto"
                >
                    {versions.map(v => <Tab key={v} label={v} />)}
                </Tabs>
            </Box>

            <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                {/* PREVIEW PANEL */}
                <Box sx={{ width: '50%', p: 2, bgcolor: 'background.default', borderRight: '1px solid rgba(255,255,255,0.05)' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                        <Typography variant="caption" color="text.secondary">
                            Viewing: {currentVersion === "v1" ? baseFilename : `${baseFilename}_${currentVersion}`}
                        </Typography>
                        <Stack direction="row" spacing={1}>
                            <Button
                                size="small"
                                startIcon={<DownloadIcon />}
                                href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/files/output/${currentVersion === "v1" ? baseFilename : `${baseFilename}_${currentVersion}`}.pdf`}
                                target="_blank"
                            >
                                PDF
                            </Button>
                            <Button
                                size="small"
                                startIcon={<DownloadIcon />}
                                href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/files/output/${currentVersion === "v1" ? baseFilename : `${baseFilename}_${currentVersion}`}.tex`}
                                target="_blank"
                            >
                                TeX
                            </Button>
                        </Stack>
                    </Box>
                    <Box sx={{
                        width: '100%',
                        height: 'calc(100% - 40px)',
                        bgcolor: 'background.paper',
                        borderRadius: 1,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: '2px dashed rgba(255,255,255,0.1)'
                    }}>
                        <Typography color="text.secondary">PDF Preview Not Available</Typography>
                    </Box>
                </Box>

                {/* CHAT PANEL */}
                <Box sx={{ width: '50%', display: 'flex', flexDirection: 'column' }}>
                    <Box sx={{ flex: 1, overflowY: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {messages.map((m, i) => (
                            <Box
                                key={i}
                                sx={{
                                    alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                                    maxWidth: '80%',
                                    bgcolor: m.role === 'user' ? 'primary.main' : 'background.paper',
                                    p: 2,
                                    borderRadius: 2,
                                    boxShadow: 1
                                }}
                            >
                                <Typography variant="body1">{m.content}</Typography>
                                {m.score && (
                                    <Typography variant="caption" display="block" sx={{ mt: 1, opacity: 0.8 }}>
                                        ATS Score: {m.score}%
                                    </Typography>
                                )}
                            </Box>
                        ))}
                        {refineMutation.isPending && <CircularProgress size={20} sx={{ ml: 2 }} />}
                    </Box>

                    <Box sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.1)', bgcolor: 'background.paper', display: 'flex', gap: 1 }}>
                        <TextField
                            fullWidth
                            placeholder="Request changes (e.g. 'Add more React keywords')..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            size="small"
                        />
                        <IconButton color="primary" onClick={handleSend} disabled={refineMutation.isPending || !input.trim()}>
                            <SendIcon />
                        </IconButton>
                    </Box>
                </Box>
            </Box>
        </Paper>
    );
}
