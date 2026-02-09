import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';
import { AuthProvider } from '@/providers/auth-provider';

const inter = Inter({
    subsets: ['latin'],
    variable: '--font-inter',
});

export const metadata: Metadata = {
    title: {
        default: 'StudyABHI',
        template: '%s | StudyABHI',
    },
    description: 'AI-powered learning platform for UPSC exam preparation',
    keywords: ['UPSC', 'exam preparation', 'AI learning', 'quiz', 'study'],
    authors: [{ name: 'StudyABHI Team' }],
    openGraph: {
        type: 'website',
        locale: 'en_US',
        siteName: 'StudyABHI',
    },
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={`${inter.variable} font-sans antialiased`}>
                <Toaster>
                    <AuthProvider>
                        {children}
                    </AuthProvider>
                </Toaster>
            </body>
        </html>
    );
}

