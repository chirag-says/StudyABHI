'use client';

import React, { useState, useEffect } from 'react';
import { FileText, Clock, Trash2, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PDFDropzone } from '@/components/upload/PDFDropzone';
import api, { getErrorMessage } from '@/services/api';
import Link from 'next/link';

interface Document {
    id: string;
    filename: string;
    original_filename: string;
    status: string;
    page_count?: number;
    created_at: string;
}

export default function UploadPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDocuments();
    }, []);

    const fetchDocuments = async () => {
        try {
            const response = await api.get<{ documents?: Document[], items?: Document[] }>('/documents');
            // Handle both 'documents' and 'items' response formats
            setDocuments(response.data.documents || response.data.items || []);
        } catch (error) {
            console.error('Failed to fetch documents:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleUploadSuccess = (doc: any) => {
        setDocuments(prev => [doc, ...prev]);
    };

    const deleteDocument = async (docId: string) => {
        if (!confirm('Are you sure you want to delete this document?')) return;

        try {
            await api.delete(`/documents/${docId}`);
            setDocuments(prev => prev.filter(d => d.id !== docId));
        } catch (error) {
            alert(getErrorMessage(error));
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-IN', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
        });
    };

    const getStatusBadge = (status: string) => {
        const styles: Record<string, string> = {
            pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
            processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
            completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
            failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
        };
        return styles[status] || styles.pending;
    };

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
            {/* Header */}
            <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                <div className="container py-6">
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                        Upload Study Materials
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Upload your PDFs and start learning with AI
                    </p>
                </div>
            </div>

            <div className="container py-8 space-y-8">
                {/* Upload Section */}
                <section>
                    <PDFDropzone onUploadSuccess={handleUploadSuccess} />
                </section>

                {/* Tips */}
                <section className="bg-card border rounded-xl p-6">
                    <h2 className="font-semibold mb-3">📚 Tips for best results</h2>
                    <ul className="grid md:grid-cols-2 gap-2 text-sm text-muted-foreground">
                        <li className="flex items-start gap-2">
                            <span className="text-primary">•</span>
                            Upload searchable PDFs (not scanned images)
                        </li>
                        <li className="flex items-start gap-2">
                            <span className="text-primary">•</span>
                            NCERTs and standard textbooks work best
                        </li>
                        <li className="flex items-start gap-2">
                            <span className="text-primary">•</span>
                            Keep file size under 10MB for faster processing
                        </li>
                        <li className="flex items-start gap-2">
                            <span className="text-primary">•</span>
                            You can upload up to 5 documents per day
                        </li>
                    </ul>
                </section>

                {/* Document List */}
                <section>
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-semibold">Your Documents</h2>
                        <span className="text-sm text-muted-foreground">
                            {documents.length} document{documents.length !== 1 ? 's' : ''}
                        </span>
                    </div>

                    {loading ? (
                        <div className="grid gap-4">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="h-20 bg-muted animate-pulse rounded-xl" />
                            ))}
                        </div>
                    ) : documents.length === 0 ? (
                        <div className="text-center py-12 bg-card border rounded-xl">
                            <FileText className="w-12 h-12 mx-auto text-muted-foreground/50" />
                            <p className="mt-4 text-muted-foreground">No documents yet</p>
                            <p className="text-sm text-muted-foreground">Upload your first PDF to get started</p>
                        </div>
                    ) : (
                        <div className="grid gap-4">
                            {documents.map((doc) => (
                                <div
                                    key={doc.id}
                                    className="group flex items-center gap-4 p-4 bg-card border rounded-xl hover:shadow-md transition-all"
                                >
                                    {/* Icon */}
                                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                                        <FileText className="w-6 h-6 text-primary" />
                                    </div>

                                    {/* Info */}
                                    <div className="flex-1 min-w-0">
                                        <h3 className="font-medium truncate">{doc.original_filename || doc.filename}</h3>
                                        <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {formatDate(doc.created_at)}
                                            </span>
                                            {doc.page_count && (
                                                <span>{doc.page_count} pages</span>
                                            )}
                                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(doc.status)}`}>
                                                {doc.status}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        {doc.status === 'completed' && (
                                            <Button asChild size="sm">
                                                <Link href={`/study/${doc.id}`}>
                                                    <ExternalLink className="w-4 h-4 mr-1" />
                                                    Study
                                                </Link>
                                            </Button>
                                        )}
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => deleteDocument(doc.id)}
                                            className="text-destructive hover:text-destructive"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
}
