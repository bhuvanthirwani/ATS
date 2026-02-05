"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAuthToken } from "@/lib/api";
import { CircularProgress, Box } from "@mui/material";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const [authorized, setAuthorized] = useState(false);

    useEffect(() => {
        const token = getAuthToken();
        if (!token) {
            router.push("/");
        } else {
            setAuthorized(true);
        }
    }, [router]);

    if (!authorized) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <CircularProgress />
            </Box>
        );
    }

    return <>{children}</>;
}
