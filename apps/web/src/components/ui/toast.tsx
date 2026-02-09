"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

// Toast Context
interface ToastContextValue {
    toasts: ToastItem[]
    addToast: (toast: Omit<ToastItem, "id">) => void
    removeToast: (id: string) => void
}

interface ToastItem {
    id: string
    title?: string
    description?: string
    variant?: "default" | "destructive"
    duration?: number
}

const ToastContext = React.createContext<ToastContextValue | undefined>(undefined)

// Toast variants
const toastVariants = cva(
    "group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all animate-in slide-in-from-top-full",
    {
        variants: {
            variant: {
                default: "border bg-background text-foreground",
                destructive: "destructive group border-destructive bg-destructive text-destructive-foreground",
            },
        },
        defaultVariants: {
            variant: "default",
        },
    }
)

// Toast Provider Component
export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = React.useState<ToastItem[]>([])

    const addToast = React.useCallback((toast: Omit<ToastItem, "id">) => {
        const id = Math.random().toString(36).substring(2, 9)
        setToasts((prev) => [...prev, { ...toast, id }])

        // Auto-remove after duration
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id))
        }, toast.duration || 5000)
    }, [])

    const removeToast = React.useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
    }, [])

    return (
        <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
            {children}
            <ToastViewport />
        </ToastContext.Provider>
    )
}

// Toast Viewport - renders all toasts
function ToastViewport() {
    const context = React.useContext(ToastContext)
    if (!context) return null

    const { toasts, removeToast } = context

    return (
        <div className="fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]">
            {toasts.map((toast) => (
                <Toast key={toast.id} {...toast} onClose={() => removeToast(toast.id)} />
            ))}
        </div>
    )
}

// Individual Toast Component
interface ToastProps extends VariantProps<typeof toastVariants> {
    id: string
    title?: string
    description?: string
    onClose: () => void
}

function Toast({ title, description, variant, onClose }: ToastProps) {
    return (
        <div className={cn(toastVariants({ variant }), "mb-2")}>
            <div className="grid gap-1">
                {title && <div className="text-sm font-semibold">{title}</div>}
                {description && <div className="text-sm opacity-90">{description}</div>}
            </div>
            <button
                onClick={onClose}
                className="absolute right-2 top-2 rounded-md p-1 text-foreground/50 opacity-0 transition-opacity hover:text-foreground focus:opacity-100 focus:outline-none focus:ring-2 group-hover:opacity-100"
            >
                <X className="h-4 w-4" />
            </button>
        </div>
    )
}

// Hook to use toast
export function useToastContext() {
    const context = React.useContext(ToastContext)
    if (!context) {
        throw new Error("useToastContext must be used within a ToastProvider")
    }
    return context
}

// Export types for compatibility
export type ToastProps_Compat = {
    variant?: "default" | "destructive"
    title?: string
    description?: string
}

export type ToastActionElement = React.ReactElement
