import { Suspense } from 'react';

export const metadata = {
    title: 'Study Room - StudyABHI',
    description: 'Focus study environment with AI-powered attention tracking, timers, and quizzes',
};

export default function StudyRoomLayout({ children }: { children: React.ReactNode }) {
    return (
        <Suspense fallback={
            <div className="h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        }>
            {children}
        </Suspense>
    );
}
