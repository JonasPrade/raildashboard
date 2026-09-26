import { Table, type TableProps } from "@mantine/core";

type Props = TableProps & {
    /**
     * Width the table needs before it starts scrolling. Pick the width at which
     * the columns are still readable — below that the container scrolls
     * horizontally instead of the page.
     */
    minWidth?: number | string;
};

/**
 * A Mantine `Table` that scrolls inside its own card instead of pushing the
 * page sideways on a narrow screen.
 *
 * Drop-in replacement: `Table.Thead` / `Table.Tbody` / `Table.Tr` / `Table.Td`
 * children stay exactly as they are, only the outer `<Table>` is swapped.
 *
 * Plan: docs/features/feature-mobile-usability.md
 */
export function ResponsiveTable({ minWidth = 640, children, ...tableProps }: Props) {
    return (
        <Table.ScrollContainer minWidth={minWidth} type="native">
            <Table {...tableProps}>{children}</Table>
        </Table.ScrollContainer>
    );
}

export default ResponsiveTable;
