"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
    Drawer,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    Typography,
    Box,
    Divider,
    Avatar
} from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import PersonIcon from "@mui/icons-material/Person";
import SettingsIcon from "@mui/icons-material/Settings";
import HistoryIcon from "@mui/icons-material/History";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const drawerWidth = 240;

export default function Sidebar() {
    const pathname = usePathname();
    const [username, setUsername] = useState<string>("");

    useEffect(() => {
        // Fetch username
        api.get("/auth/user").then(res => setUsername(res.data.username)).catch(() => setUsername("User"));
    }, []);

    const menuItems = [
        { text: "Dashboard", icon: <DashboardIcon />, href: "/dashboard" },
        { text: "Profiles", icon: <PersonIcon />, href: "/profiles" },
        { text: "Settings", icon: <SettingsIcon />, href: "/settings" },
        { text: "History", icon: <HistoryIcon />, href: "/history" },
    ];

    return (
        <Drawer
            variant="permanent"
            sx={{
                width: drawerWidth,
                flexShrink: 0,
                "& .MuiDrawer-paper": {
                    width: drawerWidth,
                    boxSizing: "border-box",
                },
            }}
        >
            <Box sx={{ p: 3, textAlign: "center" }}>
                <Typography variant="h5" sx={{ fontWeight: "bold", background: "linear-gradient(90deg, #06b6d4, #8b5cf6)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                    ATS AGENT
                </Typography>
                <Typography variant="caption" color="text.secondary">
                    Resume Tailoring Engine
                </Typography>
            </Box>

            <Divider />

            <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 2 }}>
                <Avatar sx={{ bgcolor: "secondary.main" }}>{username.charAt(0).toUpperCase()}</Avatar>
                <Box>
                    <Typography variant="subtitle2">{username}</Typography>
                    <Typography variant="caption" color="success.main">● Online</Typography>
                </Box>
            </Box>

            <Divider />

            <List>
                {menuItems.map((item) => {
                    const active = pathname === item.href;
                    return (
                        <ListItem key={item.text} disablePadding>
                            <ListItemButton
                                component={Link}
                                href={item.href}
                                selected={active}
                                sx={{
                                    mx: 1,
                                    borderRadius: 2,
                                    "&.Mui-selected": {
                                        bgcolor: "primary.main",
                                        color: "white",
                                        "&:hover": {
                                            bgcolor: "primary.dark",
                                        },
                                        "& .MuiListItemIcon-root": {
                                            color: "white"
                                        }
                                    }
                                }}
                            >
                                <ListItemIcon sx={{ color: active ? "white" : "inherit" }}>
                                    {item.icon}
                                </ListItemIcon>
                                <ListItemText primary={item.text} />
                            </ListItemButton>
                        </ListItem>
                    );
                })}
            </List>
        </Drawer>
    );
}
