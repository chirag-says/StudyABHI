'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useRouter, usePathname } from 'next/navigation';
import {
    Upload,
    Home,
    LogOut,
    Settings,
    Menu,
    X,
    Map,
    Brain,
    Sparkles,
    ArrowLeft
} from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/auth-store';
import { authService } from '@/services';
import { cn } from '@/lib/utils';

interface AppShellProps {
    children: React.ReactNode;
    showBackButton?: boolean;
    backHref?: string;
    title?: string;
}

const navItems = [
    { href: '/dashboard', label: 'Dashboard', icon: Home },
    { href: '/upload', label: 'Upload PDF', icon: Upload },
    { href: '/roadmap', label: 'My Roadmap', icon: Map },
    { href: '/quiz', label: 'Take Quiz', icon: Brain },
    { href: '/settings', label: 'Settings', icon: Settings },
];

export function AppShell({ children, showBackButton, backHref = '/dashboard', title }: AppShellProps) {
    const router = useRouter();
    const pathname = usePathname();
    const { user, logout: logoutStore } = useAuthStore();
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    const handleLogout = async () => {
        await authService.logout();
        logoutStore();
        router.push('/');
    };

    const isActive = (href: string) => {
        if (href === '/dashboard') {
            return pathname === '/dashboard';
        }
        return pathname?.startsWith(href);
    };

    return (
        <div className="min-h-screen bg-muted/30">
            {/* Mobile Header */}
            <header className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-background border-b z-50 flex items-center px-4">
                {showBackButton ? (
                    <Link href={backHref} className="p-2 hover:bg-muted rounded-md">
                        <ArrowLeft className="h-6 w-6" />
                    </Link>
                ) : (
                    <button
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                        className="p-2 hover:bg-muted rounded-md"
                    >
                        {isSidebarOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
                    </button>
                )}
                <span className="ml-4 font-semibold text-primary">{title || 'StudyABHI'}</span>
            </header>

            {/* Sidebar */}
            <aside
                className={cn(
                    "fixed top-0 left-0 h-full w-64 bg-background border-r z-40 transition-transform duration-300",
                    "lg:translate-x-0",
                    isSidebarOpen ? "translate-x-0" : "-translate-x-full"
                )}
            >
                {/* Logo */}
                <div className="h-16 flex items-center px-6 border-b">
                    <Link href="/dashboard" className="flex items-center gap-3 justify-center w-full">
                        <div className="relative w-48 h-16">
                            <Image
                                src="/assets/StudyABHI.png"
                                alt="StudyABHI Logo"
                                fill
                                className="object-contain"
                                priority
                            />
                        </div>
                    </Link>
                </div>

                {/* Navigation */}
                <nav className="p-4 space-y-1">
                    {navItems.map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            onClick={() => setIsSidebarOpen(false)}
                            className={cn(
                                "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors",
                                isActive(item.href)
                                    ? "bg-primary text-primary-foreground"
                                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                            )}
                        >
                            <item.icon className="h-5 w-5" />
                            {item.label}
                        </Link>
                    ))}
                </nav>

                {/* User Section */}
                <div className="absolute bottom-0 left-0 right-0 p-4 border-t bg-background">
                    <div className="flex items-center gap-3 mb-4 px-4">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center text-white font-bold">
                            {user?.full_name?.charAt(0) || 'U'}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-medium truncate">{user?.full_name || 'User'}</p>
                            <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                        </div>
                    </div>
                    <Button
                        variant="outline"
                        className="w-full gap-2"
                        onClick={handleLogout}
                    >
                        <LogOut className="h-4 w-4" />
                        Logout
                    </Button>
                </div>
            </aside>

            {/* Overlay for mobile */}
            {isSidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-30 lg:hidden"
                    onClick={() => setIsSidebarOpen(false)}
                />
            )}

            {/* Main Content */}
            <main className="lg:ml-64 pt-16 lg:pt-0 min-h-screen">
                {children}
            </main>
        </div>
    );
}
