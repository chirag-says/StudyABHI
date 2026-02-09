'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api, { getErrorMessage } from '@/services/api';

interface PDFDropzoneProps {
    onUploadSuccess?: (document: DocumentResponse) => void;
    onUploadError?: (error: string) => void;
    maxSizeMB?: number;
}

interface DocumentResponse {
    id: string;
    filename: string;
    status: string;
    page_count?: number;
}

type UploadStatus = 'idle' | 'uploading' | 'processing' | 'success' | 'error';

export function PDFDropzone({
    onUploadSuccess,
    onUploadError,
    maxSizeMB = 10
}: PDFDropzoneProps) {
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<UploadStatus>('idle');
    const [progress, setProgress] = useState(0);
    const [errorMessage, setErrorMessage] = useState('');
    const [uploadedDoc, setUploadedDoc] = useState<DocumentResponse | null>(null);

    const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
        // Handle rejected files
        if (rejectedFiles.length > 0) {
            const rejection = rejectedFiles[0];
            if (rejection.errors[0]?.code === 'file-too-large') {
                setErrorMessage(`File too large. Maximum size is ${maxSizeMB}MB.`);
            } else if (rejection.errors[0]?.code === 'file-invalid-type') {
                setErrorMessage('Only PDF files are accepted.');
            } else {
                setErrorMessage('Invalid file. Please try again.');
            }
            setStatus('error');
            return;
        }

        // Handle accepted file
        if (acceptedFiles.length > 0) {
            setFile(acceptedFiles[0]);
            setStatus('idle');
            setErrorMessage('');
        }
    }, [maxSizeMB]);

    const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf']
        },
        maxSize: maxSizeMB * 1024 * 1024,
        multiple: false,
    });

    const uploadFile = async () => {
        if (!file) return;

        setStatus('uploading');
        setProgress(0);
        setErrorMessage('');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await api.post<DocumentResponse>('/documents/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                onUploadProgress: (progressEvent) => {
                    if (progressEvent.total) {
                        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        setProgress(percent);
                    }
                },
            });

            setStatus('processing');

            // Poll for processing status
            const docId = response.data.id;
            let attempts = 0;
            const maxAttempts = 30;

            while (attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 2000));

                const statusResponse = await api.get<DocumentResponse>(`/documents/${docId}`);

                if (statusResponse.data.status === 'completed') {
                    setStatus('success');
                    setUploadedDoc(statusResponse.data);
                    onUploadSuccess?.(statusResponse.data);
                    return;
                } else if (statusResponse.data.status === 'failed') {
                    throw new Error('Document processing failed. Please try again.');
                }

                attempts++;
            }

            throw new Error('Processing timeout. Please check document status later.');
        } catch (error) {
            const message = getErrorMessage(error);
            setErrorMessage(message);
            setStatus('error');
            onUploadError?.(message);
        }
    };

    const resetUpload = () => {
        setFile(null);
        setStatus('idle');
        setProgress(0);
        setErrorMessage('');
        setUploadedDoc(null);
    };

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    return (
        <div className="w-full max-w-2xl mx-auto">
            {/* Dropzone */}
            {status !== 'success' && (
                <div
                    {...getRootProps()}
                    className={`
            relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
            transition-all duration-300 ease-in-out
            ${isDragActive && !isDragReject ? 'border-primary bg-primary/5 scale-[1.02]' : ''}
            ${isDragReject ? 'border-destructive bg-destructive/5' : ''}
            ${status === 'error' ? 'border-destructive' : 'border-muted-foreground/25'}
            ${!isDragActive && status !== 'error' ? 'hover:border-primary/50 hover:bg-accent/50' : ''}
          `}
                >
                    <input {...getInputProps()} />

                    {/* Upload Icon */}
                    <div className={`
            w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center
            transition-all duration-300
            ${isDragActive ? 'bg-primary/20 scale-110' : 'bg-muted'}
          `}>
                        {status === 'uploading' || status === 'processing' ? (
                            <Loader2 className="w-8 h-8 text-primary animate-spin" />
                        ) : status === 'error' ? (
                            <AlertCircle className="w-8 h-8 text-destructive" />
                        ) : (
                            <Upload className={`w-8 h-8 ${isDragActive ? 'text-primary' : 'text-muted-foreground'}`} />
                        )}
                    </div>

                    {/* Text */}
                    <div className="space-y-2">
                        {status === 'idle' && !file && (
                            <>
                                <p className="text-lg font-medium">
                                    {isDragActive ? 'Drop your PDF here' : 'Drag & drop your PDF'}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                    or click to browse • Max {maxSizeMB}MB
                                </p>
                            </>
                        )}

                        {status === 'idle' && file && (
                            <div className="flex items-center justify-center gap-3">
                                <FileText className="w-5 h-5 text-primary" />
                                <span className="font-medium">{file.name}</span>
                                <span className="text-sm text-muted-foreground">
                                    ({formatFileSize(file.size)})
                                </span>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        resetUpload();
                                    }}
                                    className="p-1 rounded-full hover:bg-muted"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                        )}

                        {status === 'uploading' && (
                            <div className="space-y-2">
                                <p className="font-medium">Uploading...</p>
                                <div className="w-full max-w-xs mx-auto h-2 bg-muted rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-primary transition-all duration-300 rounded-full"
                                        style={{ width: `${progress}%` }}
                                    />
                                </div>
                                <p className="text-sm text-muted-foreground">{progress}%</p>
                            </div>
                        )}

                        {status === 'processing' && (
                            <div className="space-y-2">
                                <p className="font-medium">Processing your PDF...</p>
                                <p className="text-sm text-muted-foreground">
                                    Extracting text and preparing for AI analysis
                                </p>
                            </div>
                        )}

                        {status === 'error' && (
                            <div className="space-y-2">
                                <p className="font-medium text-destructive">{errorMessage}</p>
                                <p className="text-sm text-muted-foreground">
                                    Click or drop to try again
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Success State */}
            {status === 'success' && uploadedDoc && (
                <div className="border rounded-xl p-6 bg-card">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                            <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold">Upload Complete!</h3>
                            <p className="text-sm text-muted-foreground">
                                {uploadedDoc.filename} • {uploadedDoc.page_count || 'Multiple'} pages
                            </p>
                        </div>
                    </div>

                    <div className="mt-4 flex gap-3">
                        <Button asChild className="flex-1">
                            <a href={`/study/${uploadedDoc.id}`}>
                                Start Studying
                            </a>
                        </Button>
                        <Button variant="outline" onClick={resetUpload}>
                            Upload Another
                        </Button>
                    </div>
                </div>
            )}

            {/* Upload Button */}
            {status === 'idle' && file && (
                <div className="mt-4 flex justify-center">
                    <Button onClick={uploadFile} size="lg" className="px-8">
                        <Upload className="w-4 h-4 mr-2" />
                        Upload PDF
                    </Button>
                </div>
            )}
        </div>
    );
}
