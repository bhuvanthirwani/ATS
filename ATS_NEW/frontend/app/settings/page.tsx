"use client";

import { api } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
    const queryClient = useQueryClient();
    const [config, setConfig] = useState<any>(null);

    // Local state for form
    const [newModel, setNewModel] = useState({
        name: "",
        provider: "openai",
        model_id: "gpt-4-turbo",
        api_key: ""
    });

    const { data: remoteConfig, isLoading } = useQuery({
        queryKey: ["config"],
        queryFn: async () => (await api.get("/files/config")).data
    });

    useEffect(() => {
        if (remoteConfig) setConfig(remoteConfig);
    }, [remoteConfig]);

    const updateConfigMutation = useMutation({
        mutationFn: async (newConfig: any) => {
            return api.post("/files/config", newConfig);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["config"] });
            alert("Configuration Saved!");
        }
    });

    const handleAddModel = () => {
        if (!newModel.api_key || !newModel.name) return;

        const newEntry = {
            id: crypto.randomUUID(),
            name: newModel.name,
            provider: newModel.provider,
            model_id: newModel.model_id, // This acts as sdk_id in old app
            sdk_id: newModel.model_id,
            api_key: newModel.api_key,
            plan_type: "paid"
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

    const handleSelectModel = (id: string) => {
        const updatedConfig = { ...config, selected_llm_id: id };
        setConfig(updatedConfig);
        updateConfigMutation.mutate(updatedConfig);
    }

    const handleDeleteModel = (id: string) => {
        const updatedInventory = config.llm_inventory.filter((m: any) => m.id !== id);
        const updatedConfig = { ...config, llm_inventory: updatedInventory };
        if (config.selected_llm_id === id) {
            updatedConfig.selected_llm_id = updatedInventory[0]?.id || null;
        }
        setConfig(updatedConfig);
        updateConfigMutation.mutate(updatedConfig);
    }

    if (isLoading) return <div>Loading settings...</div>;

    return (
        <div className="space-y-8 max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold">⚙️ Settings</h1>

            {/* ACTIVE MODEL */}
            <div className="card bg-base-200 p-6 border border-white/5">
                <h2 className="text-xl font-semibold mb-4">Active LLM Provider</h2>
                <div className="form-control">
                    <select
                        className="select select-bordered w-full"
                        value={config?.selected_llm_id || ""}
                        onChange={(e) => handleSelectModel(e.target.value)}
                    >
                        <option value="" disabled>Select a model to use...</option>
                        {config?.llm_inventory?.map((m: any) => (
                            <option key={m.id} value={m.id}>{m.name} ({m.provider} - {m.model_id})</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* ADD NEW MODEL */}
            <div className="card bg-base-200 p-6 border border-white/5">
                <h2 className="text-xl font-semibold mb-4">Add New Model</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="form-control">
                        <label className="label">Friendly Name</label>
                        <input
                            type="text"
                            className="input input-bordered"
                            value={newModel.name}
                            onChange={(e) => setNewModel({ ...newModel, name: e.target.value })}
                            placeholder="e.g. My GPT4 Key"
                        />
                    </div>
                    <div className="form-control">
                        <label className="label">Provider</label>
                        <select
                            className="select select-bordered"
                            value={newModel.provider}
                            onChange={(e) => setNewModel({ ...newModel, provider: e.target.value })}
                        >
                            <option value="openai">OpenAI</option>
                            <option value="google">Google Gemini</option>
                        </select>
                    </div>
                    <div className="form-control">
                        <label className="label">Model ID</label>
                        <select
                            className="select select-bordered"
                            value={newModel.model_id}
                            onChange={(e) => setNewModel({ ...newModel, model_id: e.target.value })}
                        >
                            {newModel.provider === 'openai' ? (
                                <>
                                    <option value="gpt-4-turbo-preview">GPT-4 Turbo</option>
                                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                                </>
                            ) : (
                                <>
                                    <option value="gemini-pro">Gemini Pro</option>
                                </>
                            )}
                        </select>
                    </div>
                    <div className="form-control">
                        <label className="label">API Key</label>
                        <input
                            type="password"
                            className="input input-bordered"
                            value={newModel.api_key}
                            onChange={(e) => setNewModel({ ...newModel, api_key: e.target.value })}
                            placeholder="sk-..."
                        />
                    </div>
                </div>
                <button className="btn btn-primary mt-6" onClick={handleAddModel}>➕ Add Model to Inventory</button>
            </div>

            {/* INVENTORY LIST */}
            <div className="card bg-base-200 p-6 border border-white/5">
                <h2 className="text-xl font-semibold mb-4">Inventory</h2>
                <div className="space-y-2">
                    {config?.llm_inventory?.map((m: any) => (
                        <div key={m.id} className="flex justify-between items-center bg-base-100 p-3 rounded-lg">
                            <div>
                                <p className="font-bold">{m.name}</p>
                                <p className="text-xs text-gray-500">{m.model_id}</p>
                            </div>
                            <button className="btn btn-ghost btn-sm text-error" onClick={() => handleDeleteModel(m.id)}>Delete</button>
                        </div>
                    ))}
                    {!config?.llm_inventory?.length && <p className="text-gray-500">No models found.</p>}
                </div>
            </div>

        </div>
    );
}
