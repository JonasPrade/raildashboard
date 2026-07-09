import type { TodoPriority, TodoStatus } from "../../shared/api/queries";
import { formatDateShort } from "../../shared/format";

// German user-facing labels and Mantine colours for the to-do (Aufgaben) feature.

export const STATUS_LABELS: Record<TodoStatus, string> = {
    OPEN: "Offen",
    IN_PROGRESS: "In Arbeit",
    DONE: "Erledigt",
};

export const STATUS_ORDER: TodoStatus[] = ["OPEN", "IN_PROGRESS", "DONE"];

export const STATUS_COLORS: Record<TodoStatus, string> = {
    OPEN: "gray",
    IN_PROGRESS: "blue",
    DONE: "teal",
};

export const PRIORITY_LABELS: Record<TodoPriority, string> = {
    LOW: "Niedrig",
    MEDIUM: "Mittel",
    HIGH: "Hoch",
};

export const PRIORITY_ORDER: TodoPriority[] = ["HIGH", "MEDIUM", "LOW"];

export const PRIORITY_COLORS: Record<TodoPriority, string> = {
    LOW: "gray",
    MEDIUM: "yellow",
    HIGH: "red",
};

/** A due date is overdue when it is strictly before today (local date). */
export function isOverdue(dueDate: string | null | undefined): boolean {
    if (!dueDate) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const due = new Date(`${dueDate}T00:00:00`);
    return due.getTime() < today.getTime();
}

/** Format an ISO date (YYYY-MM-DD) as a German short date, or "" if empty. */
export function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return "";
    const d = new Date(`${dateStr}T00:00:00`);
    if (Number.isNaN(d.getTime())) return dateStr;
    return formatDateShort(d);
}

/** Up to two uppercase initials from a username, for assignee avatars. */
export function initials(username: string): string {
    const parts = username.replace(/[._-]+/g, " ").trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
}
