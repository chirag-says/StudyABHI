"use client"

import * as React from "react"

const TOAST_LIMIT = 5
const TOAST_REMOVE_DELAY = 5000

type ToasterToast = {
    id: string
    title?: string
    description?: string
    variant?: "default" | "destructive"
}

type ToastActionType =
    | { type: "ADD_TOAST"; toast: ToasterToast }
    | { type: "UPDATE_TOAST"; toast: Partial<ToasterToast> & { id: string } }
    | { type: "DISMISS_TOAST"; toastId?: string }
    | { type: "REMOVE_TOAST"; toastId?: string }

interface ToastState {
    toasts: ToasterToast[]
}

let count = 0

function genId() {
    count = (count + 1) % Number.MAX_VALUE
    return count.toString()
}

const toastTimeouts = new Map<string, ReturnType<typeof setTimeout>>()

function addToRemoveQueue(toastId: string) {
    if (toastTimeouts.has(toastId)) {
        return
    }

    const timeout = setTimeout(() => {
        toastTimeouts.delete(toastId)
        dispatch({ type: "REMOVE_TOAST", toastId })
    }, TOAST_REMOVE_DELAY)

    toastTimeouts.set(toastId, timeout)
}

const reducer = (state: ToastState, action: ToastActionType): ToastState => {
    switch (action.type) {
        case "ADD_TOAST":
            return {
                ...state,
                toasts: [action.toast, ...state.toasts].slice(0, TOAST_LIMIT),
            }
        case "UPDATE_TOAST":
            return {
                ...state,
                toasts: state.toasts.map((t) =>
                    t.id === action.toast.id ? { ...t, ...action.toast } : t
                ),
            }
        case "DISMISS_TOAST": {
            const { toastId } = action
            if (toastId) {
                addToRemoveQueue(toastId)
            } else {
                state.toasts.forEach((toast) => {
                    addToRemoveQueue(toast.id)
                })
            }
            return state
        }
        case "REMOVE_TOAST":
            if (action.toastId === undefined) {
                return { ...state, toasts: [] }
            }
            return {
                ...state,
                toasts: state.toasts.filter((t) => t.id !== action.toastId),
            }
        default:
            return state
    }
}

const listeners: Array<(state: ToastState) => void> = []
let memoryState: ToastState = { toasts: [] }

function dispatch(action: ToastActionType) {
    memoryState = reducer(memoryState, action)
    listeners.forEach((listener) => {
        listener(memoryState)
    })
}

interface ToastOptions {
    title?: string
    description?: string
    variant?: "default" | "destructive"
}

function toast(options: ToastOptions) {
    const id = genId()

    dispatch({
        type: "ADD_TOAST",
        toast: {
            id,
            ...options,
        },
    })

    // Auto dismiss
    setTimeout(() => {
        dispatch({ type: "DISMISS_TOAST", toastId: id })
    }, TOAST_REMOVE_DELAY)

    return {
        id,
        dismiss: () => dispatch({ type: "DISMISS_TOAST", toastId: id }),
        update: (props: ToastOptions) =>
            dispatch({ type: "UPDATE_TOAST", toast: { id, ...props } }),
    }
}

function useToast() {
    const [state, setState] = React.useState<ToastState>(memoryState)

    React.useEffect(() => {
        listeners.push(setState)
        return () => {
            const index = listeners.indexOf(setState)
            if (index > -1) {
                listeners.splice(index, 1)
            }
        }
    }, [])

    return {
        ...state,
        toast,
        dismiss: (toastId?: string) => dispatch({ type: "DISMISS_TOAST", toastId }),
    }
}

export { useToast, toast }
