// User Types
export interface User {
    id: string;
    email: string;
    full_name: string;
    phone?: string;
    role: UserRole;
    exam_type: ExamType;
    is_active: boolean;
    is_verified: boolean;
    profile_image?: string;
    bio?: string;
    created_at: string;
    last_login?: string;
}

export type UserRole = 'student' | 'teacher' | 'admin';
export type ExamType = 'upsc' | 'jee' | 'neet';

// Auth Types
export interface AuthTokens {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export interface RegisterRequest {
    email: string;
    password: string;
    confirm_password: string;
    full_name: string;
    phone?: string;
    exam_type?: ExamType;
}

// API Response Types
export interface ApiResponse<T> {
    data: T;
    message?: string;
    success: boolean;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    limit: number;
    pages: number;
}

export interface ApiError {
    detail: string;
    errors?: Array<{
        field: string;
        message: string;
    }>;
}
