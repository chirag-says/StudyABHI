import api, { getErrorMessage } from './api';

// Types
export interface User {
    id: string;
    email: string;
    full_name: string;
    phone?: string;
    role: 'student' | 'teacher' | 'admin';
    exam_type: 'upsc' | 'jee' | 'neet';
    is_active: boolean;
    is_verified: boolean;
    profile_image?: string;
    bio?: string;
    created_at: string;
    last_login?: string;
}

export interface AuthTokens {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface RegisterData {
    email: string;
    password: string;
    confirm_password: string;
    full_name: string;
    phone?: string;
    exam_type?: 'upsc' | 'jee' | 'neet';
}

export interface LoginData {
    email: string;
    password: string;
}

export interface AuthResponse {
    user: User;
    tokens: AuthTokens;
}

// Auth service
class AuthService {
    /**
     * Register a new user
     */
    async register(data: RegisterData): Promise<AuthResponse> {
        const response = await api.post<AuthResponse>('/auth/register', data);
        return response.data;
    }

    /**
     * Login user
     */
    async login(data: LoginData): Promise<AuthResponse> {
        const response = await api.post<AuthResponse>('/auth/login', data);
        return response.data;
    }

    /**
     * Get current user
     */
    async getCurrentUser(): Promise<User> {
        const response = await api.get<User>('/auth/me');
        return response.data;
    }

    /**
     * Refresh tokens
     */
    async refreshTokens(refreshToken: string): Promise<AuthTokens> {
        const response = await api.post<AuthTokens>('/auth/refresh', {
            refresh_token: refreshToken,
        });
        return response.data;
    }

    /**
     * Logout user
     */
    async logout(): Promise<void> {
        try {
            await api.post('/auth/logout');
        } catch (error) {
            // Ignore errors on logout
            console.warn('Logout error:', getErrorMessage(error));
        }
    }

    /**
     * Update user profile
     */
    async updateProfile(data: Partial<User>): Promise<User> {
        const response = await api.patch<User>('/users/me', data);
        return response.data;
    }

    /**
     * Change password
     */
    async changePassword(
        currentPassword: string,
        newPassword: string,
        confirmPassword: string
    ): Promise<{ message: string }> {
        const response = await api.post('/users/me/change-password', {
            current_password: currentPassword,
            new_password: newPassword,
            confirm_password: confirmPassword,
        });
        return response.data;
    }
}

export const authService = new AuthService();
