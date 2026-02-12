"use client";

import { Container, Typography, Box, Paper, List, ListItem, ListItemText, ListItemIcon, Divider, Chip } from "@mui/material";
import HistoryIcon from "@mui/icons-material/History";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";

export default function HistoryPage() {
    // Placeholder data - ideally this would come from an API
    const historyItems = [
        { id: 1, action: "Resume Optimized", details: "Software Engineer_v2.pdf", date: "2024-05-20", status: "Success" },
        { id: 2, action: "Profile Analyzed", details: "JohnDoe_LinkedIn.pdf", date: "2024-05-19", status: "Completed" },
        { id: 3, action: "Template Uploaded", details: "Modern_Tech_Resume.tex", date: "2024-05-18", status: "Uploaded" },
    ];

    return (
        <Container maxWidth="lg">
            <Box sx={{ mb: 4 }}>
                <Typography variant="h4" fontWeight="bold">Activity History</Typography>
            </Box>

            <Paper sx={{ p: 3 }}>
                <Typography variant="h6" display="flex" alignItems="center" gap={1} gutterBottom>
                    <HistoryIcon color="primary" /> Recent Actions
                </Typography>
                <Divider sx={{ mb: 2 }} />

                <List>
                    {historyItems.map((item) => (
                        <ListItem key={item.id} divider>
                            <ListItemIcon>
                                <CheckCircleOutlineIcon color="success" />
                            </ListItemIcon>
                            <ListItemText
                                primary={item.action}
                                secondary={item.details}
                                primaryTypographyProps={{ fontWeight: 'medium' }}
                            />
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Typography variant="body2" color="text.secondary">{item.date}</Typography>
                                <Chip label={item.status} color="success" size="small" variant="outlined" />
                            </Box>
                        </ListItem>
                    ))}
                </List>

                {historyItems.length === 0 && (
                    <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
                        <Typography>No history available yet.</Typography>
                    </Box>
                )}
            </Paper>
        </Container>
    );
}
