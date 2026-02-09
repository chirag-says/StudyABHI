'use client';

import { ProtectedRoute } from '@/components/auth';
import { Sidebar } from '@/components/layout/Sidebar';

interface ProtectedLayoutProps {
    children: React.ReactNode;
}

export default function ProtectedLayout({ children }: ProtectedLayoutProps) {
    return (
        <ProtectedRoute>
            <Sidebar>
                {children}
            </Sidebar>
        </ProtectedRoute>
    );
}
