'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';
import { Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
    children: React.ReactNode;
}

/**
 * Higher-order component for protecting routes
 * Redirects to login if user is not authenticated
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
    const router = useRouter();
    const pathname = usePathname();
    const { isAuthenticated, isLoading } = useAuthStore();

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            // Store the intended destination for redirect after login
            const returnUrl = encodeURIComponent(pathname);
            router.push(`/auth/login?returnUrl=${returnUrl}`);
        }
    }, [isAuthenticated, isLoading, pathname, router]);

    // Show loading spinner while checking auth
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
                    <p className="mt-4 text-muted-foreground">Loading...</p>
                </div>
            </div>
        );
    }

    // Don't render children if not authenticated
    if (!isAuthenticated) {
        return null;
    }

    return <>{children}</>;
}

/**
 * Hook for checking if user is authenticated
 */
export function useAuth() {
    const { user, isAuthenticated, isLoading, logout } = useAuthStore();
    return { user, isAuthenticated, isLoading, logout };
}

/**
 * Hook for requiring authentication
 * Redirects to login if not authenticated
 */
export function useRequireAuth() {
    const router = useRouter();
    const pathname = usePathname();
    const { user, isAuthenticated, isLoading } = useAuthStore();

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            const returnUrl = encodeURIComponent(pathname);
            router.push(`/auth/login?returnUrl=${returnUrl}`);
        }
    }, [isAuthenticated, isLoading, pathname, router]);

    return { user, isAuthenticated, isLoading };
}
