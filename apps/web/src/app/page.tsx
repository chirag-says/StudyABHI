import Link from 'next/link';
import { ArrowRight, BookOpen, Brain, Target, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function HomePage() {
    return (
        <main className="min-h-screen">
            {/* Hero Section */}
            <section className="relative overflow-hidden bg-gradient-to-br from-primary/5 via-background to-secondary/10">
                {/* Background decoration */}
                <div className="absolute inset-0 -z-10">
                    <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
                    <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
                </div>

                <div className="container mx-auto px-4 py-24 lg:py-32">
                    <div className="max-w-4xl mx-auto text-center">
                        {/* Badge */}
                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary mb-8 animate-fade-in">
                            <Sparkles className="w-4 h-4" />
                            <span className="text-sm font-medium">AI-Powered Learning Platform</span>
                        </div>

                        {/* Heading */}
                        <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6 animate-slide-in">
                            Master UPSC with
                            <span className="gradient-text"> Intelligent Learning</span>
                        </h1>

                        {/* Subheading */}
                        <p className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
                            Personalized study plans, AI-generated quizzes, and smart content
                            summarization to accelerate your exam preparation.
                        </p>

                        {/* CTA Buttons */}
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <Link href="/auth/register">
                                <Button size="lg" className="w-full sm:w-auto gap-2">
                                    Get Started Free
                                    <ArrowRight className="w-4 h-4" />
                                </Button>
                            </Link>
                            <Link href="/auth/login">
                                <Button variant="outline" size="lg" className="w-full sm:w-auto">
                                    Sign In
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-20 bg-muted/30">
                <div className="container mx-auto px-4">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold mb-4">
                            Why Choose StudyABHI?
                        </h2>
                        <p className="text-muted-foreground max-w-2xl mx-auto">
                            Leverage cutting-edge AI technology to make your preparation smarter, not harder.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
                        {/* Feature 1 */}
                        <div className="bg-card rounded-xl p-8 shadow-sm border hover:shadow-md transition-shadow">
                            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-6">
                                <Brain className="w-6 h-6 text-primary" />
                            </div>
                            <h3 className="text-xl font-semibold mb-3">AI Quiz Generation</h3>
                            <p className="text-muted-foreground">
                                Generate practice questions from any topic instantly.
                                Adaptive difficulty based on your performance.
                            </p>
                        </div>

                        {/* Feature 2 */}
                        <div className="bg-card rounded-xl p-8 shadow-sm border hover:shadow-md transition-shadow">
                            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-6">
                                <BookOpen className="w-6 h-6 text-primary" />
                            </div>
                            <h3 className="text-xl font-semibold mb-3">Smart Summarization</h3>
                            <p className="text-muted-foreground">
                                Get concise summaries of lengthy documents and articles.
                                Focus on what matters most.
                            </p>
                        </div>

                        {/* Feature 3 */}
                        <div className="bg-card rounded-xl p-8 shadow-sm border hover:shadow-md transition-shadow">
                            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-6">
                                <Target className="w-6 h-6 text-primary" />
                            </div>
                            <h3 className="text-xl font-semibold mb-3">Expert RAG System</h3>
                            <p className="text-muted-foreground">
                                Ask questions and get accurate answers backed by
                                verified study materials.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20">
                <div className="container mx-auto px-4">
                    <div className="max-w-3xl mx-auto text-center bg-gradient-to-r from-primary/10 to-blue-500/10 rounded-2xl p-12 border">
                        <h2 className="text-3xl font-bold mb-4">
                            Ready to Transform Your Preparation?
                        </h2>
                        <p className="text-muted-foreground mb-8">
                            Join thousands of aspirants who are already using AI to crack UPSC.
                        </p>
                        <Link href="/auth/register">
                            <Button size="lg" className="gap-2">
                                Start Learning Now
                                <ArrowRight className="w-4 h-4" />
                            </Button>
                        </Link>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t py-8">
                <div className="container mx-auto px-4 text-center text-muted-foreground">
                    <p>&copy; {new Date().getFullYear()} StudyABHI. All rights reserved.</p>
                </div>
            </footer>
        </main>
    );
}
