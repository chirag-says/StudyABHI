'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Upload,
    Brain,
    Map,
    Settings,
    Menu,
    X,
    LogOut,
    ChevronLeft,
    Library,
    Eye
} from 'lucide-react';
import { useAuthStore } from '@/stores/auth-store';
import { cn } from '@/lib/utils';
import { authService } from '@/services';
import { useRouter } from 'next/navigation';

interface NavItem {
    href: string;
    label: string;
    icon: React.ReactNode;
}

const navItems: NavItem[] = [
    { href: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
    { href: '/upload', label: 'Upload PDF', icon: <Upload className="w-5 h-5" /> },
    { href: '/materials', label: 'Study Materials', icon: <Library className="w-5 h-5" /> },
    { href: '/study-room', label: 'Study Room', icon: <Eye className="w-5 h-5" /> },
    { href: '/roadmap', label: 'My Roadmap', icon: <Map className="w-5 h-5" /> },
    { href: '/quiz', label: 'Take Quiz', icon: <Brain className="w-5 h-5" /> },
    { href: '/settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
];

interface SidebarProps {
    children?: React.ReactNode;
}

export function Sidebar({ children }: SidebarProps) {
    const router = useRouter();
    const pathname = usePathname();
    const { user, logout: logoutStore } = useAuthStore();
    const [collapsed, setCollapsed] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);

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

    const NavContent = () => (
        <>
            {/* Logo */}
            <div className="p-4 border-b h-16 flex items-center justify-center overflow-hidden">
                <Link href="/dashboard" className="flex items-center gap-3 justify-center w-full">
                    <div className={cn("relative transition-all duration-300", collapsed ? "w-10 h-10" : "w-40 h-12")}>
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
            <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                {navItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => setMobileOpen(false)}
                        className={cn(
                            'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap',
                            isActive(item.href)
                                ? 'bg-primary text-primary-foreground'
                                : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                        )}
                        title={collapsed ? item.label : undefined}
                    >
                        {item.icon}
                        {!collapsed && <span>{item.label}</span>}
                    </Link>
                ))}
            </nav>

            {/* User Section */}
            <div className="p-4 border-t">
                {!collapsed ? (
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center text-white font-bold shrink-0">
                            {user?.full_name?.charAt(0) || 'U'}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-medium truncate">{user?.full_name || 'User'}</p>
                            <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                        </div>
                    </div>
                ) : (
                    <div className="w-10 h-10 mx-auto rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center text-white font-bold mb-3">
                        {user?.full_name?.charAt(0) || 'U'}
                    </div>
                )}
                <button
                    onClick={handleLogout}
                    className={cn(
                        'flex items-center gap-3 px-3 py-2 rounded-lg w-full text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors whitespace-nowrap',
                        collapsed && 'justify-center'
                    )}
                    title={collapsed ? "Logout" : undefined}
                >
                    <LogOut className="w-5 h-5" />
                    {!collapsed && <span>Logout</span>}
                </button>
            </div>

            {/* Collapse Toggle - Desktop Only */}
            <button
                onClick={() => setCollapsed(!collapsed)}
                className="hidden lg:flex absolute -right-3 top-20 w-6 h-6 bg-background border rounded-full items-center justify-center hover:bg-muted shadow-sm z-50 text-foreground"
            >
                <ChevronLeft className={cn('w-4 h-4 transition-transform', collapsed && 'rotate-180')} />
            </button>
        </>
    );

    return (
        <div className="min-h-screen bg-muted/30">
            {/* Mobile Header */}
            <header className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-background border-b z-50 flex items-center px-4 justify-between">
                <button
                    onClick={() => setMobileOpen(true)}
                    className="p-2 hover:bg-muted rounded-md"
                >
                    <Menu className="w-6 h-6" />
                </button>
                <div className="relative w-32 h-10">
                    <Image
                        src="/assets/StudyABHI.png"
                        alt="StudyABHI Logo"
                        fill
                        className="object-contain"
                        priority
                    />
                </div>
                <div className="w-10"></div> {/* Spacer for centering */}
            </header>

            {/* Mobile Sidebar Overlay */}
            {mobileOpen && (
                <div
                    className="lg:hidden fixed inset-0 bg-black/50 z-40"
                    onClick={() => setMobileOpen(false)}
                />
            )}

            {/* Mobile Sidebar */}
            <aside
                className={cn(
                    'lg:hidden fixed top-0 left-0 bottom-0 w-72 bg-background border-r z-50 transform transition-transform duration-300',
                    mobileOpen ? 'translate-x-0' : '-translate-x-full'
                )}
            >
                <div className="relative h-full flex flex-col">
                    <button
                        onClick={() => setMobileOpen(false)}
                        className="absolute top-4 right-4 p-2 hover:bg-muted rounded-lg z-10"
                    >
                        <X className="w-5 h-5" />
                    </button>
                    <NavContent />
                </div>
            </aside>

            {/* Desktop Sidebar */}
            <aside
                className={cn(
                    'hidden lg:flex flex-col fixed top-0 left-0 bottom-0 bg-background border-r z-30 transition-all duration-300',
                    collapsed ? 'w-20' : 'w-64'
                )}
            >
                <NavContent />
            </aside>

            {/* Main Content */}
            <main className={cn(
                "transition-all duration-300 min-h-screen",
                "pt-16 lg:pt-0", // Mobile header spacing
                collapsed ? "lg:ml-20" : "lg:ml-64"
            )}>
                {children}
            </main>
        </div>
    );
}
