'use client';

import React, { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import {
    FileText, Download, BookOpen, Globe, Leaf, FlaskConical, Users, Landmark, Palette, Newspaper,
    ChevronDown, ChevronRight, Home, Upload, Map, Brain, Settings, LogOut, Menu, X, Sparkles, Library,
    Maximize2, Minimize2, ExternalLink
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/auth-store';
import { authService } from '@/services';
import { cn } from '@/lib/utils';

interface StudyMaterial {
    name: string;
    filename: string;
    year: string;
    size: string;
}

interface Category {
    id: string;
    name: string;
    icon: React.ReactNode;
    color: string;
    materials: StudyMaterial[];
}

const categories: Category[] = [
    {
        id: 'polity',
        name: 'Polity',
        icon: <Landmark className="w-5 h-5" />,
        color: 'from-blue-500 to-blue-600',
        materials: [
            { name: 'Polity', filename: 'Vision-IAS-PT365-Polity-2024.pdf', year: '2024', size: '4.0 MB' },
            { name: 'Polity', filename: 'Vision-IAS-PT365-Polity-2025.pdf', year: '2025', size: '4.8 MB' },
        ]
    },
    {
        id: 'economy',
        name: 'Economy',
        icon: <BookOpen className="w-5 h-5" />,
        color: 'from-green-500 to-green-600',
        materials: [
            { name: 'Economy', filename: 'Vision-IAS-PT365-Economy-2024.pdf', year: '2024', size: '5.1 MB' },
            { name: 'Economy', filename: 'Vision-IAS-PT365-Economy-2025.pdf', year: '2025', size: '6.6 MB' },
            { name: 'Economy', filename: 'Vision-IAS-PT365-Economy-2026.pdf', year: '2026', size: '9.1 MB' },
        ]
    },
    {
        id: 'environment',
        name: 'Environment',
        icon: <Leaf className="w-5 h-5" />,
        color: 'from-emerald-500 to-emerald-600',
        materials: [
            { name: 'Environment', filename: 'Vision-IAS-PT365-Environment-2024.pdf', year: '2024', size: '16.2 MB' },
            { name: 'Environment', filename: 'Vision-IAS-PT365-Environment-2025.pdf', year: '2025', size: '21.3 MB' },
            { name: 'Environment', filename: 'Vision-IAS-PT365-Environment-2026.pdf', year: '2026', size: '11.1 MB' },
        ]
    },
    {
        id: 'science-tech',
        name: 'Science & Technology',
        icon: <FlaskConical className="w-5 h-5" />,
        color: 'from-purple-500 to-purple-600',
        materials: [
            { name: 'Science & Technology', filename: 'Vision-IAS-PT365-Science-Tech-2024.pdf', year: '2024', size: '7.2 MB' },
            { name: 'Science & Technology', filename: 'Vision-IAS-PT365-Science-Tech-2025.pdf', year: '2025', size: '16.5 MB' },
        ]
    },
    {
        id: 'ir',
        name: 'International Relations',
        icon: <Globe className="w-5 h-5" />,
        color: 'from-indigo-500 to-indigo-600',
        materials: [
            { name: 'International Relations', filename: 'Vision-IAS-PT365-IR-2024.pdf', year: '2024', size: '9.6 MB' },
            { name: 'International Relations', filename: 'Vision-IAS-PT365-IR-2025.pdf', year: '2025', size: '13.6 MB' },
            { name: 'International Relations', filename: 'Vision-IAS-PT365-IR-2026.pdf', year: '2026', size: '8.8 MB' },
        ]
    },
    {
        id: 'art-culture',
        name: 'Art & Culture',
        icon: <Palette className="w-5 h-5" />,
        color: 'from-orange-500 to-orange-600',
        materials: [
            { name: 'Culture', filename: 'Vision-IAS-PT365-Culture-2024.pdf', year: '2024', size: '10.2 MB' },
            { name: 'Art & Culture', filename: 'Vision-IAS-PT365-Art-Culture-2025.pdf', year: '2025', size: '8.0 MB' },
        ]
    },
    {
        id: 'social',
        name: 'Social Issues',
        icon: <Users className="w-5 h-5" />,
        color: 'from-pink-500 to-pink-600',
        materials: [
            { name: 'Social Issues', filename: 'Vision-IAS-PT365-Social-Issues-2024.pdf', year: '2024', size: '9.2 MB' },
            { name: 'Social Issues', filename: 'Vision-IAS-PT365-Social-Issues-2025.pdf', year: '2025', size: '10.7 MB' },
        ]
    },
    {
        id: 'current-affairs',
        name: 'Current Affairs',
        icon: <Newspaper className="w-5 h-5" />,
        color: 'from-rose-500 to-rose-600',
        materials: [
            { name: 'News through Maps', filename: 'Vision-IAS-PT365-News-Maps-2025.pdf', year: '2025', size: '43.6 MB' },
            { name: 'Personalities in News', filename: 'Vision-IAS-PT365-Personalities-2025.pdf', year: '2025', size: '16.5 MB' },
            { name: 'March Update Part 1', filename: 'Vision-IAS-PT365-March-2025-Part1.pdf', year: '2025', size: '30.4 MB' },
        ]
    },
];



// PDF Viewer Modal Component
function PDFViewerModal({
    isOpen,
    onClose,
    pdfUrl,
    title
}: {
    isOpen: boolean;
    onClose: () => void;
    pdfUrl: string;
    title: string;
}) {
    const [isMobile, setIsMobile] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);

    useEffect(() => {
        const checkMobile = () => setIsMobile(window.innerWidth < 768);
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'unset';
        }
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            {/* Close on backdrop click */}
            <div className="absolute inset-0" onClick={onClose} />

            {isMobile ? (
                // iPhone 14 Frame for Mobile
                <div className="relative z-10 animate-in fade-in zoom-in-95 duration-200">
                    <div className="relative mx-auto" style={{ width: '320px' }}>
                        {/* iPhone Frame */}
                        <div className="relative bg-black rounded-[45px] p-3 shadow-2xl">
                            {/* Dynamic Island */}
                            <div className="absolute top-5 left-1/2 -translate-x-1/2 w-24 h-7 bg-black rounded-full z-20" />

                            {/* Screen */}
                            <div className="relative bg-white rounded-[35px] overflow-hidden" style={{ height: '650px' }}>
                                {/* Status Bar */}
                                <div className="absolute top-0 left-0 right-0 h-12 bg-gradient-to-b from-gray-200 to-transparent z-10 flex items-center justify-between px-6 pt-2">
                                    <span className="text-xs font-semibold">9:41</span>
                                    <div className="flex items-center gap-1">
                                        <div className="w-4 h-2 border border-current rounded-sm">
                                            <div className="w-full h-full bg-current rounded-sm" style={{ width: '80%' }} />
                                        </div>
                                    </div>
                                </div>

                                {/* Header Bar */}
                                <div className="absolute top-12 left-0 right-0 h-12 bg-white border-b flex items-center justify-between px-4 z-10">
                                    <button onClick={onClose} className="text-primary font-medium text-sm">
                                        Close
                                    </button>
                                    <span className="text-sm font-semibold truncate max-w-[150px]">{title}</span>
                                    <button
                                        onClick={() => window.open(pdfUrl, '_blank')}
                                        className="text-primary"
                                    >
                                        <ExternalLink className="w-4 h-4" />
                                    </button>
                                </div>

                                {/* PDF Content */}
                                <iframe
                                    src={pdfUrl}
                                    className="w-full h-full pt-24"
                                    style={{ border: 'none' }}
                                />

                                {/* Home Indicator */}
                                <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1 bg-black/20 rounded-full" />
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                // MacBook Frame for Desktop
                <div className={cn(
                    "relative z-10 animate-in fade-in zoom-in-95 duration-200 transition-all",
                    isFullscreen ? "w-full h-full" : "w-[90%] max-w-5xl"
                )}>
                    <div className={cn(
                        "relative mx-auto",
                        isFullscreen ? "w-full h-full" : ""
                    )}>
                        {/* MacBook Frame */}
                        <div className={cn(
                            "bg-[#2D2D2D] shadow-2xl",
                            isFullscreen ? "rounded-none" : "rounded-xl"
                        )}>
                            {/* Menu Bar */}
                            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700">
                                <div className="flex items-center gap-2">
                                    {/* Traffic Lights */}
                                    <button
                                        onClick={onClose}
                                        className="w-3 h-3 rounded-full bg-[#FF5F57] hover:bg-[#FF5F57]/80 flex items-center justify-center group"
                                    >
                                        <X className="w-2 h-2 text-[#4A0002] opacity-0 group-hover:opacity-100" />
                                    </button>
                                    <button className="w-3 h-3 rounded-full bg-[#FEBC2E] hover:bg-[#FEBC2E]/80 flex items-center justify-center group">
                                        <Minimize2 className="w-2 h-2 text-[#985700] opacity-0 group-hover:opacity-100" />
                                    </button>
                                    <button
                                        onClick={() => setIsFullscreen(!isFullscreen)}
                                        className="w-3 h-3 rounded-full bg-[#28C840] hover:bg-[#28C840]/80 flex items-center justify-center group"
                                    >
                                        <Maximize2 className="w-2 h-2 text-[#006500] opacity-0 group-hover:opacity-100" />
                                    </button>
                                </div>

                                {/* Title */}
                                <div className="flex-1 text-center">
                                    <span className="text-gray-300 text-sm font-medium truncate">{title}</span>
                                </div>

                                {/* Actions */}
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => window.open(pdfUrl, '_blank')}
                                        className="text-gray-400 hover:text-white p-1"
                                        title="Open in new tab"
                                    >
                                        <ExternalLink className="w-4 h-4" />
                                    </button>
                                    <a
                                        href={pdfUrl}
                                        download
                                        className="text-gray-400 hover:text-white p-1"
                                        title="Download"
                                    >
                                        <Download className="w-4 h-4" />
                                    </a>
                                </div>
                            </div>

                            {/* Content Area */}
                            <div className={cn(
                                "bg-[#1E1E1E]",
                                isFullscreen ? "h-[calc(100vh-40px)]" : "h-[70vh]"
                            )}>
                                <iframe
                                    src={pdfUrl}
                                    className="w-full h-full"
                                    style={{ border: 'none' }}
                                />
                            </div>
                        </div>

                        {/* MacBook Bottom Stand (only when not fullscreen) */}
                        {!isFullscreen && (
                            <div className="relative mx-auto">
                                <div className="w-1/4 h-3 mx-auto bg-gradient-to-b from-[#2D2D2D] to-[#1a1a1a] rounded-b-lg" />
                                <div className="w-1/3 h-1 mx-auto bg-[#1a1a1a] rounded-b-xl" />
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default function StudyMaterialsPage() {
    const router = useRouter();
    const pathname = usePathname();
    const { user } = useAuthStore();
    const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['polity']));
    const [selectedYear, setSelectedYear] = useState<string>('all');
    const [pdfViewer, setPdfViewer] = useState<{ isOpen: boolean; url: string; title: string }>({
        isOpen: false,
        url: '',
        title: ''
    });

    const toggleCategory = (categoryId: string) => {
        setExpandedCategories(prev => {
            const newSet = new Set(prev);
            if (newSet.has(categoryId)) {
                newSet.delete(categoryId);
            } else {
                newSet.add(categoryId);
            }
            return newSet;
        });
    };

    const openPdfViewer = (categoryId: string, material: StudyMaterial) => {
        const url = `/files/materials/${categoryId}/${material.filename}`;
        setPdfViewer({
            isOpen: true,
            url,
            title: `${material.name} (${material.year})`
        });
    };

    const closePdfViewer = () => {
        setPdfViewer({ isOpen: false, url: '', title: '' });
    };

    const totalMaterials = categories.reduce((acc, cat) => acc + cat.materials.length, 0);

    return (
        <div className="p-6">
            {/* PDF Viewer Modal */}
            <PDFViewerModal
                isOpen={pdfViewer.isOpen}
                onClose={closePdfViewer}
                pdfUrl={pdfViewer.url}
                title={pdfViewer.title}
            />
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold">📚 Study Materials</h1>
                <p className="text-muted-foreground mt-1">
                    PT365 Comprehensive Study Material for UPSC Prelims
                </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-card border rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-primary">{categories.length}</div>
                    <div className="text-sm text-muted-foreground">Categories</div>
                </div>
                <div className="bg-card border rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-green-500">{totalMaterials}</div>
                    <div className="text-sm text-muted-foreground">Study Materials</div>
                </div>
                <div className="bg-card border rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-purple-500">3</div>
                    <div className="text-sm text-muted-foreground">Years Covered</div>
                </div>
                <div className="bg-card border rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-orange-500">PT365</div>
                    <div className="text-sm text-muted-foreground">Series</div>
                </div>
            </div>

            {/* Year Filter */}
            <div className="flex gap-2 mb-6">
                <Button
                    variant={selectedYear === 'all' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedYear('all')}
                >
                    All Years
                </Button>
                {['2024', '2025', '2026'].map(year => (
                    <Button
                        key={year}
                        variant={selectedYear === year ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setSelectedYear(year)}
                    >
                        {year}
                    </Button>
                ))}
            </div>

            {/* Categories */}
            <div className="space-y-3">
                {categories.map((category) => {
                    const filteredMaterials = selectedYear === 'all'
                        ? category.materials
                        : category.materials.filter(m => m.year === selectedYear);

                    if (filteredMaterials.length === 0) return null;

                    const isExpanded = expandedCategories.has(category.id);

                    return (
                        <div key={category.id} className="bg-card border rounded-xl overflow-hidden shadow-sm">
                            {/* Category Header */}
                            <button
                                onClick={() => toggleCategory(category.id)}
                                className={`w-full p-4 flex items-center justify-between bg-gradient-to-r ${category.color} text-white hover:opacity-95 transition-opacity`}
                            >
                                <div className="flex items-center gap-3">
                                    {category.icon}
                                    <span className="font-semibold">{category.name}</span>
                                    <span className="bg-white/20 px-2 py-0.5 rounded-full text-xs">
                                        {filteredMaterials.length} {filteredMaterials.length === 1 ? 'file' : 'files'}
                                    </span>
                                </div>
                                {isExpanded ? (
                                    <ChevronDown className="w-5 h-5" />
                                ) : (
                                    <ChevronRight className="w-5 h-5" />
                                )}
                            </button>

                            {/* Materials List */}
                            {isExpanded && (
                                <div className="divide-y">
                                    {filteredMaterials.map((material, index) => (
                                        <div
                                            key={index}
                                            className="p-4 flex items-center justify-between hover:bg-muted/50 transition-colors"
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                                    <FileText className="w-5 h-5 text-primary" />
                                                </div>
                                                <div>
                                                    <h3 className="font-medium">{material.name}</h3>
                                                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                        <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-xs font-medium">
                                                            {material.year}
                                                        </span>
                                                        <span className="text-xs">{material.size}</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Button
                                                    size="sm"
                                                    variant="default"
                                                    className="gap-2"
                                                    onClick={() => openPdfViewer(category.id, material)}
                                                >
                                                    <BookOpen className="w-4 h-4" />
                                                    <span className="hidden sm:inline">Read</span>
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    className="gap-2"
                                                    onClick={() => {
                                                        const link = document.createElement('a');
                                                        link.href = `/files/materials/${category.id}/${material.filename}`;
                                                        link.download = material.filename;
                                                        link.click();
                                                    }}
                                                >
                                                    <Download className="w-4 h-4" />
                                                    <span className="hidden sm:inline">Download</span>
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Info Card */}
            <div className="mt-6 bg-gradient-to-r from-primary/5 to-primary/10 border border-primary/20 rounded-xl p-5">
                <h3 className="font-semibold mb-2">💡 How to use these materials</h3>
                <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• PT365 materials are specifically designed for UPSC Prelims preparation</li>
                    <li>• Start with the latest year materials and work backwards for revision</li>
                    <li>• Focus on Environment, Polity, and Economy for maximum marks</li>
                    <li>• Use the AI Tutor feature to ask questions about any topic</li>
                </ul>
            </div>
        </div>
    );
}
