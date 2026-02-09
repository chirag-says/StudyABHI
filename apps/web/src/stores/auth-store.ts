import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { User } from '@/services/auth.service';

interface AuthState {
    // State
    user: User | null;
    accessToken: string | null;
    refreshToken: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;

    // Actions
    setUser: (user: User | null) => void;
    setTokens: (accessToken: string, refreshToken: string) => void;
    setLoading: (loading: boolean) => void;
    login: (user: User, accessToken: string, refreshToken: string) => void;
    logout: () => void;
    updateUser: (userData: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            // Initial state
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: true,

            // Actions
            setUser: (user) =>
                set({
                    user,
                    isAuthenticated: user !== null
                }),

            setTokens: (accessToken, refreshToken) =>
                set({
                    accessToken,
                    refreshToken
                }),

            setLoading: (isLoading) =>
                set({ isLoading }),

            login: (user, accessToken, refreshToken) =>
                set({
                    user,
                    accessToken,
                    refreshToken,
                    isAuthenticated: true,
                    isLoading: false,
                }),

            logout: () =>
                set({
                    user: null,
                    accessToken: null,
                    refreshToken: null,
                    isAuthenticated: false,
                    isLoading: false,
                }),

            updateUser: (userData) => {
                const currentUser = get().user;
                if (currentUser) {
                    set({
                        user: { ...currentUser, ...userData },
                    });
                }
            },
        }),
        {
            name: 'upsc-auth-storage',
            storage: createJSONStorage(() => localStorage),
            partialize: (state) => ({
                user: state.user,
                accessToken: state.accessToken,
                refreshToken: state.refreshToken,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);
