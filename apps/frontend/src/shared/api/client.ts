import { getCredentials } from "../../lib/auth";

type PathParams = Record<string, string | number | undefined>;

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type ApiError = {
    status: number;
    message: string;
    details?: unknown;
};

type ApiRequestInit = RequestInit & {
    params?: {
        path?: PathParams;
    };
};

function resolvePath(path: string, pathParams?: PathParams) {
    if (!pathParams) return path;

    return Object.entries(pathParams).reduce((acc, [key, value]) => {
        if (value === undefined || value === null) {
            return acc;
        }

        return acc.replace(`:${key}`, encodeURIComponent(String(value)));
    }, path);
}

export async function api<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
    const { params, headers, ...requestInit } = init;
    const resolvedPath = resolvePath(path, params?.path);
    const authCreds = getCredentials();
    const response = await fetch(`${API_BASE}${resolvedPath}`, {
        ...requestInit,
        headers: {
            Accept: "application/json",
            ...(authCreds ? { Authorization: `Basic ${authCreds}` } : {}),
            ...(headers ?? {}),
        },
    });

    if (!response.ok) {
        let details: unknown;
        try {
            details = await response.json();
        } catch {
            // ignore JSON parsing errors for error bodies
        }

        const error: ApiError = {
            status: response.status,
            message: (details as { message?: string } | undefined)?.message ?? response.statusText,
            details,
        };

        throw error;
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return response.json() as Promise<T>;
}
