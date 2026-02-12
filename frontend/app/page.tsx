"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setAuthToken } from "@/lib/api";
import {
    Box,
    Card,
    CardContent,
    Typography,
    Tabs,
    Tab,
    TextField,
    Button,
    Alert,
    CircularProgress,
    InputAdornment
} from "@mui/material";
import PersonIcon from "@mui/icons-material/Person";
import LockIcon from "@mui/icons-material/Lock";
import EmailIcon from "@mui/icons-material/Email";

export default function Home() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState(0); // 0 = login, 1 = register
    const [formData, setFormData] = useState({
        username: "",
        email: "",
        password: ""
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            if (activeTab === 1) { // Register
                const res = await api.post("/auth/register", formData);
                setAuthToken(res.data.access_token, res.data.username);
                router.push("/dashboard");
            } else { // Login
                const res = await api.post("/auth/login", {
                    username: formData.username,
                    password: formData.password
                });
                setAuthToken(res.data.access_token, res.data.username);
                router.push("/dashboard");
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || "Authentication failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Box
            sx={{
                minHeight: '100vh',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                position: 'relative',
                overflow: 'hidden',
                bgcolor: 'background.default',
                color: 'text.primary'
            }}
        >
            <Box sx={{ zIndex: 10, textAlign: 'center', mb: 4 }}>
                <Typography variant="h2" fontWeight="900" sx={{ letterSpacing: '-0.03em' }}>
                    ATS PRO
                </Typography>
                <Typography variant="h6" sx={{ opacity: 0.6, color: 'text.secondary', fontWeight: 500 }}>
                    AI-Powered Resume Architecture
                </Typography>
            </Box>

            <Card sx={{ maxWidth: 450, width: '100%', zIndex: 10, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
                <CardContent sx={{ p: 4 }}>
                    <Tabs
                        value={activeTab}
                        onChange={(_, v) => setActiveTab(v)}
                        variant="fullWidth"
                        indicatorColor="primary"
                        sx={{ mb: 3 }}
                    >
                        <Tab label="Login" />
                        <Tab label="Register" />
                    </Tabs>

                    <Typography variant="h5" align="center" fontWeight="bold" sx={{ mb: 3 }}>
                        {activeTab === 0 ? 'Welcome Back' : 'Create Account'}
                    </Typography>

                    <form onSubmit={handleSubmit}>
                        <TextField
                            fullWidth
                            label="Username"
                            margin="normal"
                            value={formData.username}
                            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                            required
                            InputProps={{
                                startAdornment: <InputAdornment position="start"><PersonIcon color="action" /></InputAdornment>
                            }}
                        />

                        {activeTab === 1 && (
                            <TextField
                                fullWidth
                                label="Email"
                                type="email"
                                margin="normal"
                                value={formData.email}
                                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                required
                                InputProps={{
                                    startAdornment: <InputAdornment position="start"><EmailIcon color="action" /></InputAdornment>
                                }}
                            />
                        )}

                        <TextField
                            fullWidth
                            label="Password"
                            type="password"
                            margin="normal"
                            value={formData.password}
                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            required
                            InputProps={{
                                startAdornment: <InputAdornment position="start"><LockIcon color="action" /></InputAdornment>
                            }}
                        />

                        {error && (
                            <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
                        )}

                        <Button
                            type="submit"
                            fullWidth
                            variant="contained"
                            size="large"
                            sx={{ mt: 4, py: 1.5 }}
                            disabled={loading}
                        >
                            {loading ? <CircularProgress size={24} /> : (activeTab === 0 ? 'Login' : 'Register')}
                        </Button>
                    </form>
                </CardContent>
            </Card>

            <Typography variant="caption" sx={{ mt: 4, opacity: 0.5 }}>
                Safe. Secure. Private.
            </Typography>
        </Box>
    );
}
