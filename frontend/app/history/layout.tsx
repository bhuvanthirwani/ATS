import Sidebar from "@/components/Sidebar";
import Box from "@mui/material/Box";
import AuthGuard from "@/components/layout/AuthGuard";

export default function HistoryLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <AuthGuard>
            <Box sx={{ display: 'flex' }}>
                <Sidebar />
                <Box component="main" sx={{ flexGrow: 1, p: 3, width: '100%' }}>
                    {children}
                </Box>
            </Box>
        </AuthGuard>
    );
}
