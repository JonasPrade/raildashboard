import { useEffect, useLayoutEffect, useRef, type ReactNode } from "react";
import { Table, type TableProps } from "@mantine/core";

import "./ResponsiveTable.css";

type Props = TableProps & {
    /**
     * Width the table needs before it starts scrolling (from 48em up). Pick the
     * width at which the columns are still readable — below that the container
     * scrolls horizontally instead of the page. Below 48em the table turns into
     * cards and this width no longer applies.
     */
    minWidth?: number | string;
    /**
     * Sort control shown as a line above the cards (below 48em only), because
     * the header row with its sortable column heads is hidden there. Pass it for
     * tables with sortable headers, e.g. a small `Select` „Sortiert nach …“.
     */
    sortControl?: ReactNode;
};

const CHECK_CELL = "idt-check-cell";

/** Reads a cell's own marker or the one inherited from its column head. */
function columnFlag(cell: HTMLTableCellElement, head: HTMLTableCellElement | undefined, attr: string) {
    return cell.getAttribute(attr) ?? head?.getAttribute(attr) ?? null;
}

function setAttr(el: Element, name: string, value: string | null) {
    if (value === null) {
        if (el.hasAttribute(name)) el.removeAttribute(name);
    } else if (el.getAttribute(name) !== value) {
        el.setAttribute(name, value);
    }
}

/**
 * Writes the card-mode hints onto every body cell: `data-label` (the text of
 * the column head), and `data-card-title`, `data-card-status`,
 * `data-card-hidden`, `data-card-check`, `data-card-full` for the CSS in
 * `ResponsiveTable.css`. Works on the rendered DOM, so it copes with any
 * Mantine `Table.*` children, row components and colSpans.
 */
function labelTableCells(table: HTMLTableElement) {
    const headRows = table.tHead ? Array.from(table.tHead.rows) : [];
    const headRow = headRows.length > 0 ? headRows[headRows.length - 1] : undefined;

    // Column index → bottom-most head cell covering it (rowSpan/colSpan-aware,
    // so a grouped two-row head still labels every column).
    const grid: HTMLTableCellElement[][] = headRows.map(() => []);
    headRows.forEach((tr, r) => {
        let col = 0;
        for (const th of Array.from(tr.cells)) {
            while (grid[r]![col]) col++;
            const rows = Math.max(1, th.rowSpan);
            const cols = Math.max(1, th.colSpan);
            for (let dr = 0; dr < rows && r + dr < grid.length; dr++) {
                for (let dc = 0; dc < cols; dc++) grid[r + dr]![col + dc] = th;
            }
            col += cols;
        }
    });
    const heads: HTMLTableCellElement[] = grid.length > 0 ? Array.from(grid[grid.length - 1]!) : [];
    const columnCount = heads.length;
    const frame = table.closest(".idt-rtable");
    if (frame) setAttr(frame, "data-card-mode", headRow ? "cards" : "plain");
    if (!headRow) return;

    const rows: HTMLTableRowElement[] = [];
    for (const body of Array.from(table.tBodies)) rows.push(...Array.from(body.rows));
    if (table.tFoot) rows.push(...Array.from(table.tFoot.rows));

    for (const row of rows) {
        let col = 0;
        let titleSet = false;
        for (const cell of Array.from(row.cells)) {
            const span = Math.max(1, cell.colSpan);
            const head = heads[col];
            col += span;

            const full = columnCount > 1 && span >= columnCount;
            const hidden = columnFlag(cell, head, "data-card") === "hide";
            const status =
                columnFlag(cell, head, "data-role") === "status" ||
                cell.classList.contains("status") ||
                (head?.classList.contains("status") ?? false);
            const check =
                cell.classList.contains(CHECK_CELL) ||
                (head?.classList.contains(CHECK_CELL) ?? false) ||
                (col === span &&
                    !head?.textContent?.trim() &&
                    cell.querySelector('input[type="checkbox"]') !== null &&
                    !cell.textContent?.trim());
            const title = !titleSet && !full && !hidden && !status && !check;
            if (title) titleSet = true;

            const label = full ? "" : (head?.textContent ?? "").replace(/\s+/g, " ").trim();
            setAttr(cell, "data-label", label);
            setAttr(cell, "data-card-full", full ? "" : null);
            setAttr(cell, "data-card-hidden", hidden ? "" : null);
            setAttr(cell, "data-card-status", status && !full ? "" : null);
            setAttr(cell, "data-card-check", check && !full ? "" : null);
            setAttr(cell, "data-card-title", title ? "" : null);
        }
        setAttr(row, "data-card-has-check", row.querySelector(":scope > [data-card-check]") ? "" : null);
    }
}

/**
 * The one data table of the app.
 *
 * - From 48em: a Mantine `Table` (class `.idt-table`) in a 2px frame
 *   (`.idt-table-frame`) that scrolls inside itself instead of pushing the page
 *   sideways.
 * - Below 48em (decision W2): every row becomes a card — the first content cell
 *   is the heading (a checkbox cell sits in front of it), the other cells are
 *   label/value pairs with the label taken from the column head, a status cell
 *   (`data-role="status"` or class `status`) stands alone in a footer, and the
 *   header row is hidden (pass `sortControl` for sortable tables).
 *
 * Opt-outs per column: `data-card="hide"` on the `Th` (or a single `Td`) keeps
 * the column out of the card. Numeric columns carry `className="num"`.
 *
 * Drop-in replacement: `Table.Thead` / `Table.Tbody` / `Table.Tr` / `Table.Td`
 * children stay exactly as they are, only the outer `<Table>` is swapped.
 *
 * Plan: docs/features/feature-mobile-usability.md, docs/features/feature-idt-design.md (W2)
 */
export function ResponsiveTable({ minWidth = 640, sortControl, children, className, ...tableProps }: Props) {
    const rootRef = useRef<HTMLDivElement>(null);

    // Re-label after every render of the table itself …
    useLayoutEffect(() => {
        const table = rootRef.current?.querySelector("table");
        if (table) labelTableCells(table);
    });

    // … and whenever rows change without this component re-rendering (row
    // components with their own state, lazy rows).
    useEffect(() => {
        const root = rootRef.current;
        if (!root || typeof MutationObserver === "undefined") return;
        const observer = new MutationObserver(() => {
            const table = root.querySelector("table");
            if (table) labelTableCells(table);
        });
        observer.observe(root, { childList: true, subtree: true, characterData: true });
        return () => observer.disconnect();
    }, []);

    return (
        <div ref={rootRef} className="idt-rtable">
            {sortControl ? <div className="idt-rtable__sort">{sortControl}</div> : null}
            <div className="idt-table-frame">
                <Table.ScrollContainer minWidth={minWidth} type="native">
                    <Table {...tableProps} className={className ? `idt-table ${className}` : "idt-table"}>
                        {children}
                    </Table>
                </Table.ScrollContainer>
            </div>
        </div>
    );
}

export default ResponsiveTable;
