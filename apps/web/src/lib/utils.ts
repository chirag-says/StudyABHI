import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Utility function to merge Tailwind CSS classes
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

/**
 * Format date to human readable string
 */
export function formatDate(date: Date | string): string {
    return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    })
}

/**
 * Sleep utility for async operations
 */
export function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Check if we're running on the server
 */
export const isServer = typeof window === 'undefined'

/**
 * Check if we're running on the client
 */
export const isClient = !isServer
