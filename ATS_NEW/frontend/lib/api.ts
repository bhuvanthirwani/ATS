import axios from "axios";

// Create Axios Instance (Initial base URL is placeholder, updated by interceptor)
export const api = axios.create({
    headers: {
        "Content-Type": "application/json",
    },
});

// Dynamic Base URL Strategy
export const getBaseUrl = () => {
    if (typeof window !== "undefined") {
        // Client Side
        const hostname = window.location.hostname;
        if (hostname !== "localhost" && hostname !== "127.0.0.1") {
            // Production/Remote: Use relative path
            return "/api/v1";
        }
    }
    // Server Side / Localhost fallback
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
};

// Helper to set/get Token
export const setAuthToken = (token: string, username: string) => {
    if (typeof window !== "undefined") {
        localStorage.setItem("token", token);
        localStorage.setItem("username", username);
        // Force reload or event dispatch could happen here
    }
};

export const getAuthToken = () => {
    if (typeof window !== "undefined") {
        return localStorage.getItem("token");
    }
    return null;
}

export const getUsername = () => {
    if (typeof window !== "undefined") {
        return localStorage.getItem("username");
    }
    return null;
}

export const clearAuth = () => {
    if (typeof window !== "undefined") {
        localStorage.removeItem("token");
        localStorage.removeItem("username");
        window.location.href = "/";
    }
};

// Request Interceptor: Dynamic URL & Auth
api.interceptors.request.use((config) => {
    // 1. Set Base URL Dynamically per request
    // This fixes SSR/Hydration issues where window might be undefined initially
    config.baseURL = getBaseUrl();

    // 2. Add Token
    const token = getAuthToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }

    // Debug Log (Optional, remove in strict prod if needed)
    // console.log(`[API] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);

    return config;
});

// Response Interceptor: Handle 401
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Only redirect if not already on login page to avoid loops
            if (typeof window !== "undefined" && window.location.pathname !== "/") {
                clearAuth();
            }
        }
        return Promise.reject(error);
    }
);
