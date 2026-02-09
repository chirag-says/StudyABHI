import Link from 'next/link';

interface AuthLayoutProps {
    children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
    return (
        <div className="min-h-screen flex flex-col">
            {/* Header */}
            <header className="border-b">
                <div className="container mx-auto px-4 py-4">
                    <Link href="/" className="text-xl font-bold gradient-text">
                        StudyABHI
                    </Link>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 flex items-center justify-center p-4 bg-gradient-to-br from-primary/5 via-background to-secondary/10">
                <div className="w-full max-w-md">
                    {children}
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t py-4">
                <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
                    &copy; {new Date().getFullYear()} StudyABHI
                </div>
            </footer>
        </div>
    );
}
