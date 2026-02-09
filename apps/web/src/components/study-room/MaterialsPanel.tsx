'use client';

import React, { useState, useEffect } from 'react';
import {
    FileText,
    ChevronRight,
    ChevronDown,
    Download,
    BookOpen,
    Loader2,
    Search,
    Folder,
    Globe,
    Leaf,
    FlaskConical,
    Users,
    Landmark,
    Palette,
    Newspaper,
    ExternalLink
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

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

interface MaterialsPanelProps {
    onMaterialSelect?: (material: StudyMaterial & { url: string; categoryId: string }) => void;
    currentMaterialId?: string;
}

// Same categories as the main materials page
const categories: Category[] = [
    {
        id: 'polity',
        name: 'Polity',
        icon: <Landmark className="w-4 h-4" />,
        color: 'from-blue-500 to-blue-600',
        materials: [
            { name: 'Polity', filename: 'Vision-IAS-PT365-Polity-2024.pdf', year: '2024', size: '4.0 MB' },
            { name: 'Polity', filename: 'Vision-IAS-PT365-Polity-2025.pdf', year: '2025', size: '4.8 MB' },
        ]
    },
    {
        id: 'economy',
        name: 'Economy',
        icon: <BookOpen className="w-4 h-4" />,
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
        icon: <Leaf className="w-4 h-4" />,
        color: 'from-emerald-500 to-emerald-600',
        materials: [
            { name: 'Environment', filename: 'Vision-IAS-PT365-Environment-2024.pdf', year: '2024', size: '16.2 MB' },
            { name: 'Environment', filename: 'Vision-IAS-PT365-Environment-2025.pdf', year: '2025', size: '21.3 MB' },
            { name: 'Environment', filename: 'Vision-IAS-PT365-Environment-2026.pdf', year: '2026', size: '11.1 MB' },
        ]
    },
    {
        id: 'science-tech',
        name: 'Science & Tech',
        icon: <FlaskConical className="w-4 h-4" />,
        color: 'from-purple-500 to-purple-600',
        materials: [
            { name: 'Science & Technology', filename: 'Vision-IAS-PT365-Science-Tech-2024.pdf', year: '2024', size: '7.2 MB' },
            { name: 'Science & Technology', filename: 'Vision-IAS-PT365-Science-Tech-2025.pdf', year: '2025', size: '16.5 MB' },
        ]
    },
    {
        id: 'ir',
        name: 'International Relations',
        icon: <Globe className="w-4 h-4" />,
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
        icon: <Palette className="w-4 h-4" />,
        color: 'from-orange-500 to-orange-600',
        materials: [
            { name: 'Culture', filename: 'Vision-IAS-PT365-Culture-2024.pdf', year: '2024', size: '10.2 MB' },
            { name: 'Art & Culture', filename: 'Vision-IAS-PT365-Art-Culture-2025.pdf', year: '2025', size: '8.0 MB' },
        ]
    },
    {
        id: 'social',
        name: 'Social Issues',
        icon: <Users className="w-4 h-4" />,
        color: 'from-pink-500 to-pink-600',
        materials: [
            { name: 'Social Issues', filename: 'Vision-IAS-PT365-Social-Issues-2024.pdf', year: '2024', size: '9.2 MB' },
            { name: 'Social Issues', filename: 'Vision-IAS-PT365-Social-Issues-2025.pdf', year: '2025', size: '10.7 MB' },
        ]
    },
    {
        id: 'current-affairs',
        name: 'Current Affairs',
        icon: <Newspaper className="w-4 h-4" />,
        color: 'from-rose-500 to-rose-600',
        materials: [
            { name: 'News through Maps', filename: 'Vision-IAS-PT365-News-Maps-2025.pdf', year: '2025', size: '43.6 MB' },
            { name: 'Personalities in News', filename: 'Vision-IAS-PT365-Personalities-2025.pdf', year: '2025', size: '16.5 MB' },
            { name: 'March Update Part 1', filename: 'Vision-IAS-PT365-March-2025-Part1.pdf', year: '2025', size: '30.4 MB' },
        ]
    },
];

export function MaterialsPanel({ onMaterialSelect, currentMaterialId }: MaterialsPanelProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['polity']));

    const categoryNames = ['all', ...categories.map(c => c.id)];

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

    const handleMaterialSelect = (categoryId: string, material: StudyMaterial) => {
        const url = `/files/materials/${categoryId}/${material.filename}`;
        onMaterialSelect?.({
            ...material,
            url,
            categoryId
        });
    };

    // Filter categories based on search and selection
    const filteredCategories = categories.filter(cat => {
        if (selectedCategory !== 'all' && cat.id !== selectedCategory) return false;
        if (searchQuery) {
            return cat.materials.some(m =>
                m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                m.filename.toLowerCase().includes(searchQuery.toLowerCase())
            );
        }
        return true;
    });

    return (
        <div className="h-full flex flex-col">
            {/* Search */}
            <div className="p-3 border-b">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search materials..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-muted border-0 focus:ring-2 focus:ring-primary"
                    />
                </div>
            </div>

            {/* Category Filters */}
            <div className="p-3 border-b">
                <div className="flex items-center gap-2 overflow-x-auto scrollbar-thin pb-1">
                    {categoryNames.map(catId => {
                        const cat = categories.find(c => c.id === catId);
                        return (
                            <button
                                key={catId}
                                onClick={() => setSelectedCategory(catId)}
                                className={`px-3 py-1 text-xs rounded-full whitespace-nowrap transition-colors ${selectedCategory === catId
                                        ? 'bg-primary text-primary-foreground'
                                        : 'bg-muted hover:bg-muted/80'
                                    }`}
                            >
                                {catId === 'all' ? 'All' : cat?.name || catId}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Categories List */}
            <div className="flex-1 overflow-y-auto">
                {filteredCategories.length === 0 ? (
                    <div className="text-center py-8 px-4">
                        <Folder className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
                        <p className="text-sm font-medium mb-1">No materials found</p>
                        <p className="text-xs text-muted-foreground">
                            Try a different search term
                        </p>
                    </div>
                ) : (
                    <div className="space-y-1 p-2">
                        {filteredCategories.map((category) => {
                            const isExpanded = expandedCategories.has(category.id);
                            const filteredMats = searchQuery
                                ? category.materials.filter(m =>
                                    m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                                    m.filename.toLowerCase().includes(searchQuery.toLowerCase())
                                )
                                : category.materials;

                            return (
                                <div key={category.id} className="rounded-lg overflow-hidden border">
                                    {/* Category Header */}
                                    <button
                                        onClick={() => toggleCategory(category.id)}
                                        className={`w-full p-3 flex items-center justify-between bg-gradient-to-r ${category.color} text-white`}
                                    >
                                        <div className="flex items-center gap-2">
                                            {category.icon}
                                            <span className="font-medium text-sm">{category.name}</span>
                                            <span className="bg-white/20 px-1.5 py-0.5 rounded text-[10px]">
                                                {filteredMats.length}
                                            </span>
                                        </div>
                                        {isExpanded ? (
                                            <ChevronDown className="w-4 h-4" />
                                        ) : (
                                            <ChevronRight className="w-4 h-4" />
                                        )}
                                    </button>

                                    {/* Materials List */}
                                    {isExpanded && (
                                        <div className="divide-y bg-card">
                                            {filteredMats.map((material, idx) => {
                                                const materialId = `${category.id}-${material.filename}`;
                                                const isSelected = currentMaterialId === materialId;

                                                return (
                                                    <div
                                                        key={idx}
                                                        className={`p-3 cursor-pointer transition-colors ${isSelected
                                                                ? 'bg-primary/10'
                                                                : 'hover:bg-muted/50'
                                                            }`}
                                                        onClick={() => handleMaterialSelect(category.id, material)}
                                                    >
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center flex-shrink-0">
                                                                <FileText className="w-4 h-4 text-primary" />
                                                            </div>
                                                            <div className="flex-1 min-w-0">
                                                                <p className="text-sm font-medium truncate">
                                                                    {material.name}
                                                                </p>
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                                                                        {material.year}
                                                                    </span>
                                                                    <span className="text-[10px] text-muted-foreground">
                                                                        {material.size}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                            <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Quick Actions */}
            <div className="p-3 border-t">
                <Button variant="outline" size="sm" className="w-full" asChild>
                    <Link href="/materials">
                        <ExternalLink className="w-4 h-4 mr-2" />
                        Browse All Materials
                    </Link>
                </Button>
            </div>
        </div>
    );
}

export type { StudyMaterial };
