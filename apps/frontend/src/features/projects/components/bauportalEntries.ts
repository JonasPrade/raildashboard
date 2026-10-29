import type { ProjectBauportalEntry } from "../../../shared/api/queries";

/** Confirmed entries that carry a link — the only ones the card shows. */
export function bauportalLinkedEntries(
    entries: ProjectBauportalEntry[] | undefined,
): (ProjectBauportalEntry & { url: string })[] {
    return (entries ?? []).filter((e): e is ProjectBauportalEntry & { url: string } => !!e.url);
}
