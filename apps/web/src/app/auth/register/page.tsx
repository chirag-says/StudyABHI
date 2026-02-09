'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Loader2, Mail, Lock, User, Eye, EyeOff, Phone } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/stores/auth-store';
import { authService, getErrorMessage } from '@/services';

// Validation schema
const registerSchema = z.object({
    full_name: z
        .string()
        .min(2, 'Name must be at least 2 characters')
        .max(100, 'Name must be less than 100 characters'),
    email: z.string().email('Please enter a valid email address'),
    phone: z.string().optional(),
    password: z
        .string()
        .min(8, 'Password must be at least 8 characters')
        .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
        .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
        .regex(/[0-9]/, 'Password must contain at least one number')
        .regex(/[!@#$%^&*(),.?":{}|<>]/, 'Password must contain at least one special character'),
    confirm_password: z.string(),
}).refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
    const router = useRouter();
    const { toast } = useToast();
    const { login } = useAuthStore();

    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<RegisterFormData>({
        resolver: zodResolver(registerSchema),
        defaultValues: {
            full_name: '',
            email: '',
            phone: '',
            password: '',
            confirm_password: '',
        },
    });

    const onSubmit = async (data: RegisterFormData) => {
        setIsLoading(true);

        try {
            // Prepare payload - convert empty phone to undefined/null or omit it
            const payload = {
                ...data,
                exam_type: 'upsc' as const,
                phone: data.phone && data.phone.trim() !== '' ? data.phone : undefined,
            };

            const response = await authService.register(payload);

            // Store auth data
            login(
                response.user,
                response.tokens.access_token,
                response.tokens.refresh_token
            );

            toast({
                title: 'Account created!',
                description: 'Welcome to StudyABHI',
            });

            // Redirect to dashboard
            router.push('/dashboard');
        } catch (error) {
            toast({
                title: 'Registration failed',
                description: getErrorMessage(error),
                variant: 'destructive',
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card className="shadow-lg">
            <CardHeader className="space-y-1">
                <CardTitle className="text-2xl text-center">Create account</CardTitle>
                <CardDescription className="text-center">
                    Start your UPSC preparation journey
                </CardDescription>
            </CardHeader>

            <CardContent>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    {/* Full Name */}
                    <div className="space-y-2">
                        <Label htmlFor="full_name">Full Name</Label>
                        <div className="relative">
                            <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                id="full_name"
                                type="text"
                                placeholder="John Doe"
                                className="pl-10"
                                disabled={isLoading}
                                {...register('full_name')}
                            />
                        </div>
                        {errors.full_name && (
                            <p className="text-sm text-destructive">{errors.full_name.message}</p>
                        )}
                    </div>

                    {/* Email */}
                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                id="email"
                                type="email"
                                placeholder="you@example.com"
                                className="pl-10"
                                disabled={isLoading}
                                {...register('email')}
                            />
                        </div>
                        {errors.email && (
                            <p className="text-sm text-destructive">{errors.email.message}</p>
                        )}
                    </div>

                    {/* Phone (Optional) */}
                    <div className="space-y-2">
                        <Label htmlFor="phone">Phone (Optional)</Label>
                        <div className="relative">
                            <Phone className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                id="phone"
                                type="tel"
                                placeholder="+91 9876543210"
                                className="pl-10"
                                disabled={isLoading}
                                {...register('phone')}
                            />
                        </div>
                    </div>

                    {/* Password */}
                    <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                id="password"
                                type={showPassword ? 'text' : 'password'}
                                placeholder="••••••••"
                                className="pl-10 pr-10"
                                disabled={isLoading}
                                {...register('password')}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
                            >
                                {showPassword ? (
                                    <EyeOff className="h-4 w-4" />
                                ) : (
                                    <Eye className="h-4 w-4" />
                                )}
                            </button>
                        </div>
                        {errors.password && (
                            <p className="text-sm text-destructive">{errors.password.message}</p>
                        )}
                    </div>

                    {/* Confirm Password */}
                    <div className="space-y-2">
                        <Label htmlFor="confirm_password">Confirm Password</Label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                id="confirm_password"
                                type={showConfirmPassword ? 'text' : 'password'}
                                placeholder="••••••••"
                                className="pl-10 pr-10"
                                disabled={isLoading}
                                {...register('confirm_password')}
                            />
                            <button
                                type="button"
                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
                            >
                                {showConfirmPassword ? (
                                    <EyeOff className="h-4 w-4" />
                                ) : (
                                    <Eye className="h-4 w-4" />
                                )}
                            </button>
                        </div>
                        {errors.confirm_password && (
                            <p className="text-sm text-destructive">{errors.confirm_password.message}</p>
                        )}
                    </div>

                    {/* Submit Button */}
                    <Button type="submit" className="w-full" disabled={isLoading}>
                        {isLoading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Creating account...
                            </>
                        ) : (
                            'Create account'
                        )}
                    </Button>
                </form>
            </CardContent>

            <CardFooter className="flex-col gap-4">
                <div className="text-center text-sm text-muted-foreground">
                    Already have an account?{' '}
                    <Link href="/auth/login" className="text-primary hover:underline">
                        Sign in
                    </Link>
                </div>

                <p className="text-xs text-center text-muted-foreground">
                    By creating an account, you agree to our{' '}
                    <Link href="/terms" className="underline hover:text-foreground">
                        Terms of Service
                    </Link>{' '}
                    and{' '}
                    <Link href="/privacy" className="underline hover:text-foreground">
                        Privacy Policy
                    </Link>
                </p>
            </CardFooter>
        </Card>
    );
}
