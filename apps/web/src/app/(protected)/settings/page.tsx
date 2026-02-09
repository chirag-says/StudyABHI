'use client';

import React, { useState, useEffect } from 'react';
import { User, Settings, Globe, Shield, LogOut, Camera, Save, Loader2, ChevronRight, Bell, Moon, Sun, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api, { getErrorMessage } from '@/services/api';
import { useAuthStore } from '@/stores/auth-store';
import { useRouter } from 'next/navigation';

interface UserProfile {
    id: string;
    email: string;
    full_name: string;
    avatar_url?: string;
    phone?: string;
    created_at: string;
}

interface UserPreferences {
    language: 'en' | 'hi' | 'hinglish';
    theme: 'light' | 'dark' | 'system';
    daily_goal_minutes: number;
    notifications_enabled: boolean;
    email_digest: 'daily' | 'weekly' | 'never';
    study_reminder_time?: string;
}

interface PrivacySettings {
    analytics_enabled: boolean;
    share_progress: boolean;
    store_conversations: boolean;
}

type Tab = 'profile' | 'preferences' | 'privacy';

export default function SettingsPage() {
    const router = useRouter();
    const { logout } = useAuthStore();

    const [activeTab, setActiveTab] = useState<Tab>('profile');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [preferences, setPreferences] = useState<UserPreferences>({
        language: 'en',
        theme: 'system',
        daily_goal_minutes: 60,
        notifications_enabled: true,
        email_digest: 'weekly',
    });
    const [privacy, setPrivacy] = useState<PrivacySettings>({
        analytics_enabled: true,
        share_progress: false,
        store_conversations: true,
    });

    const [editedProfile, setEditedProfile] = useState<Partial<UserProfile>>({});
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [profileRes, prefsRes, privacyRes] = await Promise.all([
                api.get<UserProfile>('/users/me'),
                api.get<UserPreferences>('/users/preferences').catch(() => ({ data: preferences })),
                api.get<PrivacySettings>('/privacy/settings').catch(() => ({ data: privacy })),
            ]);

            setProfile(profileRes.data);
            setEditedProfile(profileRes.data);
            setPreferences(prefsRes.data);
            setPrivacy(privacyRes.data);
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const saveProfile = async () => {
        setSaving(true);
        try {
            await api.patch('/users/me', editedProfile);
            setProfile({ ...profile!, ...editedProfile });
        } catch (error) {
            alert(getErrorMessage(error));
        } finally {
            setSaving(false);
        }
    };

    const savePreferences = async () => {
        setSaving(true);
        try {
            await api.patch('/users/preferences', preferences);
        } catch (error) {
            alert(getErrorMessage(error));
        } finally {
            setSaving(false);
        }
    };

    const savePrivacy = async () => {
        setSaving(true);
        try {
            await api.patch('/privacy/settings', privacy);
        } catch (error) {
            alert(getErrorMessage(error));
        } finally {
            setSaving(false);
        }
    };

    const handleLogout = () => {
        logout();
        router.push('/auth/login');
    };

    const requestDataExport = async () => {
        try {
            await api.post('/privacy/export');
            alert('Data export requested. You will receive an email when ready.');
        } catch (error) {
            alert(getErrorMessage(error));
        }
    };

    const requestAccountDeletion = async () => {
        try {
            await api.post('/privacy/delete-account');
            logout();
            router.push('/');
        } catch (error) {
            alert(getErrorMessage(error));
        }
    };

    const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
        { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
        { id: 'preferences', label: 'Preferences', icon: <Settings className="w-4 h-4" /> },
        { id: 'privacy', label: 'Privacy', icon: <Shield className="w-4 h-4" /> },
    ];

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Loader2 className="w-10 h-10 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
            {/* Header */}
            <div className="border-b bg-background/95 backdrop-blur">
                <div className="container py-6">
                    <h1 className="text-3xl font-bold">Settings</h1>
                    <p className="text-muted-foreground mt-1">Manage your account and preferences</p>
                </div>
            </div>

            <div className="container py-8">
                <div className="grid lg:grid-cols-4 gap-8">
                    {/* Sidebar */}
                    <aside className="lg:col-span-1">
                        <nav className="space-y-1 bg-card border rounded-xl p-2">
                            {tabs.map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${activeTab === tab.id
                                            ? 'bg-primary text-primary-foreground'
                                            : 'hover:bg-muted'
                                        }`}
                                >
                                    {tab.icon}
                                    {tab.label}
                                    <ChevronRight className="w-4 h-4 ml-auto" />
                                </button>
                            ))}
                        </nav>

                        {/* Logout Button */}
                        <Button
                            variant="ghost"
                            className="w-full mt-4 text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={handleLogout}
                        >
                            <LogOut className="w-4 h-4 mr-2" />
                            Logout
                        </Button>
                    </aside>

                    {/* Main Content */}
                    <main className="lg:col-span-3">
                        {/* Profile Tab */}
                        {activeTab === 'profile' && (
                            <div className="bg-card border rounded-xl p-6 space-y-6">
                                <h2 className="text-xl font-semibold">Personal Information</h2>

                                {/* Avatar */}
                                <div className="flex items-center gap-4">
                                    <div className="relative">
                                        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center text-white text-2xl font-bold">
                                            {profile?.full_name?.charAt(0) || 'U'}
                                        </div>
                                        <button className="absolute bottom-0 right-0 w-8 h-8 bg-background border rounded-full flex items-center justify-center hover:bg-muted">
                                            <Camera className="w-4 h-4" />
                                        </button>
                                    </div>
                                    <div>
                                        <h3 className="font-semibold">{profile?.full_name}</h3>
                                        <p className="text-sm text-muted-foreground">{profile?.email}</p>
                                    </div>
                                </div>

                                {/* Form */}
                                <div className="grid md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Full Name</label>
                                        <input
                                            type="text"
                                            value={editedProfile.full_name || ''}
                                            onChange={(e) => setEditedProfile({ ...editedProfile, full_name: e.target.value })}
                                            className="w-full px-4 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:outline-none"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Email</label>
                                        <input
                                            type="email"
                                            value={profile?.email || ''}
                                            disabled
                                            className="w-full px-4 py-2 border rounded-lg bg-muted text-muted-foreground"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Phone (Optional)</label>
                                        <input
                                            type="tel"
                                            value={editedProfile.phone || ''}
                                            onChange={(e) => setEditedProfile({ ...editedProfile, phone: e.target.value })}
                                            placeholder="+91 12345 67890"
                                            className="w-full px-4 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:outline-none"
                                        />
                                    </div>
                                </div>

                                <div className="flex justify-end">
                                    <Button onClick={saveProfile} disabled={saving}>
                                        {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                        Save Changes
                                    </Button>
                                </div>
                            </div>
                        )}

                        {/* Preferences Tab */}
                        {activeTab === 'preferences' && (
                            <div className="space-y-6">
                                {/* Language */}
                                <div className="bg-card border rounded-xl p-6">
                                    <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                        <Globe className="w-5 h-5 text-primary" />
                                        Language
                                    </h2>
                                    <div className="grid grid-cols-3 gap-3">
                                        {[
                                            { value: 'en', label: 'English' },
                                            { value: 'hi', label: 'हिंदी' },
                                            { value: 'hinglish', label: 'Hinglish' },
                                        ].map((lang) => (
                                            <button
                                                key={lang.value}
                                                onClick={() => setPreferences({ ...preferences, language: lang.value as any })}
                                                className={`p-4 rounded-xl border-2 transition-all ${preferences.language === lang.value
                                                        ? 'border-primary bg-primary/5'
                                                        : 'border-transparent bg-muted hover:border-primary/30'
                                                    }`}
                                            >
                                                <p className="font-medium">{lang.label}</p>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Theme */}
                                <div className="bg-card border rounded-xl p-6">
                                    <h2 className="text-xl font-semibold mb-4">Appearance</h2>
                                    <div className="grid grid-cols-3 gap-3">
                                        {[
                                            { value: 'light', label: 'Light', icon: <Sun className="w-5 h-5" /> },
                                            { value: 'dark', label: 'Dark', icon: <Moon className="w-5 h-5" /> },
                                            { value: 'system', label: 'System', icon: <Settings className="w-5 h-5" /> },
                                        ].map((theme) => (
                                            <button
                                                key={theme.value}
                                                onClick={() => setPreferences({ ...preferences, theme: theme.value as any })}
                                                className={`p-4 rounded-xl border-2 transition-all ${preferences.theme === theme.value
                                                        ? 'border-primary bg-primary/5'
                                                        : 'border-transparent bg-muted hover:border-primary/30'
                                                    }`}
                                            >
                                                <div className="flex flex-col items-center gap-2">
                                                    {theme.icon}
                                                    <p className="font-medium text-sm">{theme.label}</p>
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Study Goals */}
                                <div className="bg-card border rounded-xl p-6">
                                    <h2 className="text-xl font-semibold mb-4">Study Goals</h2>
                                    <div className="space-y-4">
                                        <div>
                                            <label className="block text-sm font-medium mb-2">Daily Goal (minutes)</label>
                                            <input
                                                type="range"
                                                min="15"
                                                max="180"
                                                step="15"
                                                value={preferences.daily_goal_minutes}
                                                onChange={(e) => setPreferences({ ...preferences, daily_goal_minutes: parseInt(e.target.value) })}
                                                className="w-full"
                                            />
                                            <div className="flex justify-between text-sm text-muted-foreground mt-1">
                                                <span>15m</span>
                                                <span className="font-bold text-foreground">{preferences.daily_goal_minutes} minutes</span>
                                                <span>180m</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Notifications */}
                                <div className="bg-card border rounded-xl p-6">
                                    <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                        <Bell className="w-5 h-5 text-primary" />
                                        Notifications
                                    </h2>
                                    <div className="space-y-4">
                                        <label className="flex items-center justify-between cursor-pointer">
                                            <span>Enable notifications</span>
                                            <div className="relative">
                                                <input
                                                    type="checkbox"
                                                    checked={preferences.notifications_enabled}
                                                    onChange={(e) => setPreferences({ ...preferences, notifications_enabled: e.target.checked })}
                                                    className="sr-only peer"
                                                />
                                                <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                                                <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
                                            </div>
                                        </label>
                                        <div>
                                            <label className="block text-sm font-medium mb-2">Email Digest</label>
                                            <select
                                                value={preferences.email_digest}
                                                onChange={(e) => setPreferences({ ...preferences, email_digest: e.target.value as any })}
                                                className="w-full px-4 py-2 border rounded-lg bg-background"
                                            >
                                                <option value="daily">Daily</option>
                                                <option value="weekly">Weekly</option>
                                                <option value="never">Never</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex justify-end">
                                    <Button onClick={savePreferences} disabled={saving}>
                                        {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                        Save Preferences
                                    </Button>
                                </div>
                            </div>
                        )}

                        {/* Privacy Tab */}
                        {activeTab === 'privacy' && (
                            <div className="space-y-6">
                                <div className="bg-card border rounded-xl p-6">
                                    <h2 className="text-xl font-semibold mb-4">Data & Privacy</h2>
                                    <div className="space-y-4">
                                        <label className="flex items-center justify-between cursor-pointer p-3 rounded-lg hover:bg-muted">
                                            <div>
                                                <p className="font-medium">Usage Analytics</p>
                                                <p className="text-sm text-muted-foreground">Help us improve by sharing anonymous usage data</p>
                                            </div>
                                            <div className="relative">
                                                <input
                                                    type="checkbox"
                                                    checked={privacy.analytics_enabled}
                                                    onChange={(e) => setPrivacy({ ...privacy, analytics_enabled: e.target.checked })}
                                                    className="sr-only peer"
                                                />
                                                <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                                                <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
                                            </div>
                                        </label>

                                        <label className="flex items-center justify-between cursor-pointer p-3 rounded-lg hover:bg-muted">
                                            <div>
                                                <p className="font-medium">Store Conversations</p>
                                                <p className="text-sm text-muted-foreground">Save AI chat history for context</p>
                                            </div>
                                            <div className="relative">
                                                <input
                                                    type="checkbox"
                                                    checked={privacy.store_conversations}
                                                    onChange={(e) => setPrivacy({ ...privacy, store_conversations: e.target.checked })}
                                                    className="sr-only peer"
                                                />
                                                <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                                                <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
                                            </div>
                                        </label>
                                    </div>
                                </div>

                                <div className="bg-card border rounded-xl p-6">
                                    <h2 className="text-xl font-semibold mb-4">Your Data</h2>
                                    <div className="space-y-4">
                                        <Button variant="outline" onClick={requestDataExport} className="w-full justify-start">
                                            <Eye className="w-4 h-4 mr-2" />
                                            Export My Data
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => setShowDeleteConfirm(true)}
                                            className="w-full justify-start text-destructive hover:text-destructive"
                                        >
                                            <EyeOff className="w-4 h-4 mr-2" />
                                            Delete My Account
                                        </Button>
                                    </div>
                                </div>

                                <div className="flex justify-end">
                                    <Button onClick={savePrivacy} disabled={saving}>
                                        {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                        Save Privacy Settings
                                    </Button>
                                </div>
                            </div>
                        )}
                    </main>
                </div>
            </div>

            {/* Delete Account Confirm Modal */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-card rounded-2xl p-6 max-w-md w-full">
                        <h3 className="text-xl font-semibold text-destructive mb-2">Delete Account?</h3>
                        <p className="text-muted-foreground mb-4">
                            This will permanently delete your account and all associated data. This action cannot be undone.
                        </p>
                        <div className="flex gap-3">
                            <Button
                                variant="outline"
                                onClick={() => setShowDeleteConfirm(false)}
                                className="flex-1"
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="destructive"
                                onClick={requestAccountDeletion}
                                className="flex-1"
                            >
                                Delete Account
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
