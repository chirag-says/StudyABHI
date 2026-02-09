'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/stores/auth-store';
import { authService } from '@/services/auth.service';

interface AuthProviderProps {
    children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
    const { accessToken, setUser, setLoading, logout } = useAuthStore();

    useEffect(() => {
        const initAuth = async () => {
            // Check if we have a token
            if (!accessToken) {
                setLoading(false);
                return;
            }

            try {
                // Verify token by fetching current user
                const user = await authService.getCurrentUser();
                setUser(user);
            } catch (error) {
                // Token is invalid, logout
                console.error('Auth verification failed:', error);
                logout();
            } finally {
                setLoading(false);
            }
        };

        initAuth();
    }, [accessToken, setUser, setLoading, logout]);

    return <>{children}</>;
}
