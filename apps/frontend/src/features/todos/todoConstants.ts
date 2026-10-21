import type { TodoPriority, TodoStatus } from "../../shared/api/queries";
import type { CSSProperties } from "react";

import { formatDateShort } from "../../shared/format";
import { TODO_PRIORITY_WEIGHT, TODO_STATUS_STYLE } from "../../shared/theme/semanticColors";

// German user-facing labels and the status display of the to-do (Aufgaben)
// feature. Anwendungsebene "Status": only overdue carries colour (a red
// underline), done is muted with a check, priority shows through weight.

export const STATUS_LABELS: Record<TodoStatus, string> = {
    OPEN: "Offen",
    IN_PROGRESS: "In Arbeit",
    DONE: "Erledigt",
};

export const STATUS_ORDER: TodoStatus[] = ["OPEN", "IN_PROGRESS", "DONE"];


export const PRIORITY_LABELS: Record<TodoPriority, string> = {
    LOW: "Niedrig",
    MEDIUM: "Mittel",
    HIGH: "Hoch",
};

export const PRIORITY_ORDER: TodoPriority[] = ["HIGH", "MEDIUM", "LOW"];

export const PRIORITY_WEIGHT: Record<TodoPriority, number> = TODO_PRIORITY_WEIGHT;

export type TodoDisplayStatus = keyof typeof TODO_STATUS_STYLE;

/** Status as displayed: an unfinished task past its due date shows as overdue. */
export function displayStatus(status: TodoStatus, dueDate: string | null | undefined): TodoDisplayStatus {
    if (status !== "DONE" && isOverdue(dueDate)) return "OVERDUE";
    return status;
}

/** Text style of a display status (colour, weight, overdue underline). */
export function todoStatusTextStyle(status: TodoDisplayStatus): CSSProperties {
    const def: { color: string; weight: number; underline?: string } = TODO_STATUS_STYLE[status];
    return {
        color: def.color,
        fontWeight: def.weight,
        ...(def.underline ? { borderBottom: `3px solid ${def.underline}`, paddingBottom: 1 } : {}),
    };
}

/** Whether a display status is drawn with a check in front (done). */
export function hasCheck(status: TodoDisplayStatus): boolean {
    return "check" in TODO_STATUS_STYLE[status];
}

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
