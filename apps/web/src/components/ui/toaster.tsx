"use client"

import { ToastProvider } from "@/components/ui/toast"

export function Toaster({ children }: { children?: React.ReactNode }) {
    return <ToastProvider>{children}</ToastProvider>
}
