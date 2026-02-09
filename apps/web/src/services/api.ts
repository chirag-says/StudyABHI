import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/auth-store';

// API base URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
const api: AxiosInstance = axios.create({
    baseURL: `${API_URL}/api/v1`,
    timeout: 300000, // 5 minutes for local LLM operations
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor - add auth token
api.interceptors.request.use(
    (config) => {
        // Only run on client-side
        if (typeof window !== 'undefined') {
            const token = useAuthStore.getState().accessToken;
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor - handle token refresh
api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        // Handle 401 errors (unauthorized)
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                // Try to refresh the token
                const refreshToken = useAuthStore.getState().refreshToken;

                if (refreshToken) {
                    const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
                        refresh_token: refreshToken,
                    });

                    const { access_token, refresh_token } = response.data;

                    // Update tokens in store
                    useAuthStore.getState().setTokens(access_token, refresh_token);

                    // Retry the original request
                    if (originalRequest.headers) {
                        originalRequest.headers.Authorization = `Bearer ${access_token}`;
                    }
                    return api(originalRequest);
                }
            } catch (refreshError) {
                // Refresh failed, logout user
                useAuthStore.getState().logout();
                if (typeof window !== 'undefined') {
                    window.location.href = '/auth/login';
                }
            }
        }

        return Promise.reject(error);
    }
);

// API error type
export interface ApiError {
    detail: string;
    errors?: Array<{
        field: string;
        message: string;
    }>;
}

// Extract error message from API response
export function getErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const data = error.response?.data as ApiError;
        if (data?.detail) {
            return data.detail;
        }
        if (data?.errors && data.errors.length > 0) {
            return data.errors.map(e => e.message).join(', ');
        }
        return error.message;
    }
    if (error instanceof Error) {
        return error.message;
    }
    return 'An unexpected error occurred';
}

export default api;
