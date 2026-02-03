import axios from "axios";

// Create Axios Instance
export const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
    headers: {
        "Content-Type": "application/json",
    },
});

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

// Request Interceptor: Add Bearer Token
api.interceptors.request.use((config) => {
    const token = getAuthToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
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
