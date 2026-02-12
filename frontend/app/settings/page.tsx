"use client";

import { api } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import {
    Container, Typography, Box, Paper, Tabs, Tab,
    TextField, Button, Select, MenuItem, FormControl,
    InputLabel, IconButton, Grid, Chip, Divider, Alert, Snackbar
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import AddIcon from "@mui/icons-material/Add";

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

function CustomTabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props;
    return (
        <div role="tabpanel" hidden={value !== index} {...other}>
            {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
        </div>
    );
}

export default function SettingsPage() {
    const queryClient = useQueryClient();
    const [tabValue, setTabValue] = useState(0);
    const [config, setConfig] = useState<any>(null);
    const [message, setMessage] = useState<{ text: string, type: "success" | "error" } | null>(null);

    // Form State
    const [newModel, setNewModel] = useState({
        name: "",
        provider: "openai",
        model_id: "",
        api_key: ""
    });

    const [prompts, setPrompts] = useState({
        analyze_prompt: "",
        optimize_prompt: ""
    });

    // Queries
    const { data: remoteConfig } = useQuery({
        queryKey: ["config"],
        queryFn: async () => (await api.get("/files/config")).data
    });

    const { data: llmCatalog } = useQuery({
        queryKey: ["llm-catalog"],
        queryFn: async () => (await api.get("/files/llm-catalog")).data
    });

    useEffect(() => {
        if (remoteConfig) {
            setConfig(remoteConfig);
            setPrompts({
                analyze_prompt: remoteConfig.prompts?.analyze_prompt || "",
                optimize_prompt: remoteConfig.prompts?.optimize_prompt || ""
            });
        }
    }, [remoteConfig]);

    const updateConfigMutation = useMutation({
        mutationFn: async (newConfig: any) => api.post("/files/config", newConfig),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["config"] });
            setMessage({ text: "Configuration Saved!", type: "success" });
        },
        onError: () => setMessage({ text: "Failed to save configuration.", type: "error" })
    });

    const handleSavePrompts = () => {
        if (!config) return;
        const updatedConfig = { ...config, prompts: prompts };
        setConfig(updatedConfig);
        updateConfigMutation.mutate(updatedConfig);
    };

    const handleAddModel = () => {
        if (!newModel.api_key || !newModel.name || !newModel.model_id) return;
        const catalogItem = llmCatalog?.find((c: any) => c.id === newModel.model_id);

        const newEntry = {
            id: crypto.randomUUID(),
            name: newModel.name,
            provider: catalogItem?.provider || newModel.provider,
            model_id: catalogItem?.model_name || newModel.model_id,
            sdk_id: catalogItem?.id || newModel.model_id,
            api_key: newModel.api_key,
            plan_type: catalogItem?.plans_supported?.includes('free') ? 'free' : 'paid'
        };

        const updatedInventory = [...(config.llm_inventory || []), newEntry];
        const updatedConfig = {
            ...config,
            llm_inventory: updatedInventory,
            selected_llm_id: config.selected_llm_id || newEntry.id
        };

        setConfig(updatedConfig);
        updateConfigMutation.mutate(updatedConfig);
        setNewModel({ ...newModel, name: "", api_key: "" });
    };

    const handleDeleteModel = (id: string) => {
        const updatedInventory = config.llm_inventory.filter((m: any) => m.id !== id);
        const updatedConfig = { ...config, llm_inventory: updatedInventory };
        if (config.selected_llm_id === id) updatedConfig.selected_llm_id = null;

        setConfig(updatedConfig);
        updateConfigMutation.mutate(updatedConfig);
    };

    const handleSelectModel = (id: string) => {
        const updatedConfig = { ...config, selected_llm_id: id };
        setConfig(updatedConfig);
        updateConfigMutation.mutate(updatedConfig);
    };

    return (
        <Container maxWidth="lg">
            <Box sx={{ mb: 4 }}>
                <Typography variant="h4" fontWeight="bold">Configuration</Typography>
            </Box>

            <Paper sx={{ width: '100%' }}>
                <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} indicatorColor="primary" textColor="primary">
                    <Tab label="AI Models" />
                    <Tab label="LLM Inventory" />
                    <Tab label="System Prompts" />
                </Tabs>

                {/* TAB 1: MODEL SELECTION */}
                <CustomTabPanel value={tabValue} index={0}>
                    <Typography variant="h6" gutterBottom>Active Model</Typography>

                    {config?.llm_inventory?.length > 0 ? (
                        <Grid container spacing={2} alignItems="center">
                            <Grid item xs={12} md={6}>
                                <FormControl fullWidth>
                                    <InputLabel>Choose Model</InputLabel>
                                    <Select
                                        value={config?.selected_llm_id || ""}
                                        label="Choose Model"
                                        onChange={(e) => handleSelectModel(e.target.value)}
                                    >
                                        {config.llm_inventory.map((m: any) => (
                                            <MenuItem key={m.id} value={m.id}>
                                                {m.name} ({m.provider}/{m.plan_type})
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                            <Grid item xs={12}>
                                <Alert severity="info" sx={{ mt: 2 }}>
                                    Selected model will be used for all analysis and optimization tasks.
                                </Alert>
                            </Grid>
                        </Grid>
                    ) : (
                        <Alert severity="warning">No models found! Please go to Inventory tab to add one.</Alert>
                    )}
                </CustomTabPanel>

                {/* TAB 2: INVENTORY */}
                <CustomTabPanel value={tabValue} index={1}>
                    <Typography variant="h6" gutterBottom>Add New Model</Typography>
                    <Grid container spacing={2} sx={{ mb: 4 }}>
                        <Grid item xs={12} md={4}>
                            <FormControl fullWidth>
                                <InputLabel>Base Model</InputLabel>
                                <Select
                                    value={newModel.model_id}
                                    label="Base Model"
                                    onChange={(e) => {
                                        const found = llmCatalog?.find((c: any) => c.id === e.target.value);
                                        setNewModel({
                                            ...newModel,
                                            model_id: e.target.value,
                                            provider: found?.provider || "openai"
                                        });
                                    }}
                                >
                                    {llmCatalog?.map((c: any) => (
                                        <MenuItem key={c.id} value={c.id}>
                                            {c.display_name} ({c.provider})
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} md={4}>
                            <TextField
                                fullWidth
                                label="Friendly Name"
                                value={newModel.name}
                                onChange={(e) => setNewModel({ ...newModel, name: e.target.value })}
                            />
                        </Grid>
                        <Grid item xs={12} md={4}>
                            <TextField
                                fullWidth
                                label="API Key"
                                type="password"
                                value={newModel.api_key}
                                onChange={(e) => setNewModel({ ...newModel, api_key: e.target.value })}
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <Button
                                variant="contained"
                                startIcon={<AddIcon />}
                                onClick={handleAddModel}
                                disabled={!newModel.api_key || !newModel.name || !newModel.model_id}
                            >
                                Add to Inventory
                            </Button>
                        </Grid>
                    </Grid>

                    <Divider sx={{ my: 4 }} />
                    <Typography variant="h6" gutterBottom>Existing Models</Typography>
                    <Grid container spacing={2}>
                        {config?.llm_inventory?.map((m: any) => (
                            <Grid item xs={12} md={6} key={m.id}>
                                <Paper variant="outlined" sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Box>
                                        <Typography variant="subtitle1" fontWeight="bold">{m.name}</Typography>
                                        <Typography variant="caption" color="text.secondary">{m.provider} • {m.plan_type}</Typography>
                                    </Box>
                                    <IconButton color="error" onClick={() => handleDeleteModel(m.id)}>
                                        <DeleteIcon />
                                    </IconButton>
                                </Paper>
                            </Grid>
                        ))}
                    </Grid>
                </CustomTabPanel>

                {/* TAB 3: PROMPTS */}
                <CustomTabPanel value={tabValue} index={2}>
                    <Typography variant="h6" gutterBottom>System Prompts</Typography>
                    <Alert severity="info" sx={{ mb: 3 }}>
                        Customize the instructions sent to the LLM.
                        Use placeholders like <code>{"{resume_text}"}</code> and <code>{"{job_description}"}</code>.
                    </Alert>

                    <Box sx={{ mb: 4 }}>
                        <Typography variant="subtitle2" gutterBottom>Analysis Prompt</Typography>
                        <Box sx={{ mb: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            {["{resume_text}", "{job_description}"].map((ph) => (
                                <Chip
                                    key={ph}
                                    label={ph}
                                    onClick={() => setPrompts(prev => ({ ...prev, analyze_prompt: prev.analyze_prompt + " " + ph }))}
                                    color="primary"
                                    variant="outlined"
                                    size="small"
                                    clickable
                                />
                            ))}
                        </Box>
                        <TextField
                            fullWidth
                            multiline
                            rows={8}
                            value={prompts.analyze_prompt}
                            onChange={(e) => setPrompts({ ...prompts, analyze_prompt: e.target.value })}
                        />
                    </Box>

                    <Box sx={{ mb: 4 }}>
                        <Typography variant="subtitle2" gutterBottom>Optimization Prompt</Typography>
                        <Box sx={{ mb: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            {["{resume_text}", "{job_description}", "{initial_ats_score}", "{missing_keywords}", "{matched_keywords}", "{justification}"].map((ph) => (
                                <Chip
                                    key={ph}
                                    label={ph}
                                    onClick={() => setPrompts(prev => ({ ...prev, optimize_prompt: prev.optimize_prompt + " " + ph }))}
                                    color="secondary"
                                    variant="outlined"
                                    size="small"
                                    clickable
                                />
                            ))}
                        </Box>
                        <TextField
                            fullWidth
                            multiline
                            rows={8}
                            value={prompts.optimize_prompt}
                            onChange={(e) => setPrompts({ ...prompts, optimize_prompt: e.target.value })}
                        />
                    </Box>

                    <Button
                        variant="contained"
                        size="large"
                        startIcon={<SaveIcon />}
                        onClick={handleSavePrompts}
                    >
                        Save Prompts
                    </Button>
                </CustomTabPanel>
            </Paper>

            <Snackbar
                open={!!message}
                autoHideDuration={4000}
                onClose={() => setMessage(null)}
            >
                <Alert severity={message?.type || "info"} onClose={() => setMessage(null)}>
                    {message?.text}
                </Alert>
            </Snackbar>
        </Container>
    );
}
