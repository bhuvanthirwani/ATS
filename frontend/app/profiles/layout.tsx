import Sidebar from "@/components/Sidebar";
import Box from "@mui/material/Box";

export default function ProfilesLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <Box sx={{ display: 'flex' }}>
            <Sidebar />
            <Box component="main" sx={{ flexGrow: 1, p: 3, width: '100%' }}>
                {children}
            </Box>
        </Box>
    );
}
