import { ActionIcon, Box, Drawer, Slider, Stack, Switch, Text, TextInput } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconAdjustments, IconSearch, IconX } from "@tabler/icons-react";
import { ChronicleButton } from "../../components/chronicle";
import { useIsMobile } from "../../shared/hooks/useBreakpoint";

type Props = {
    onOpenFilters: () => void;
    lineWidth: number;
    onLineWidthChange: (value: number) => void;
    pointSize: number;
    onPointSizeChange: (value: number) => void;
    onlySuperior: boolean;
    onOnlySuperiorChange: (value: boolean) => void;
    searchTerm: string;
    onSearchChange: (value: string) => void;
    totalProjects: number;
    filteredCount: number;
    /** Omitted when the deployment has no railway tile source — the switch is then hidden. */
    showRailwayLines?: boolean;
    onShowRailwayLinesChange?: (value: boolean) => void;
    showConstituencies: boolean;
    onShowConstituenciesChange: (value: boolean) => void;
};

export default function MapControls({
    onOpenFilters,
    lineWidth,
    onLineWidthChange,
    pointSize,
    onPointSizeChange,
    onlySuperior,
    onOnlySuperiorChange,
    searchTerm,
    onSearchChange,
    totalProjects,
    filteredCount,
    showRailwayLines,
    onShowRailwayLinesChange,
    showConstituencies,
    onShowConstituenciesChange,
}: Props) {
    const isMobile = useIsMobile();
    const [sheetOpened, { open: openSheet, close: closeSheet }] = useDisclosure(false);

    const searchField = (
        <TextInput
            placeholder="Projekt suchen…"
            leftSection={<IconSearch size={14} />}
            rightSection={
                searchTerm ? (
                    <ActionIcon variant="subtle" size="xs" onClick={() => onSearchChange("")} aria-label="Suche leeren">
                        <IconX size={12} />
                    </ActionIcon>
                ) : undefined
            }
            value={searchTerm}
            onChange={(e) => onSearchChange(e.currentTarget.value)}
            size="sm"
            style={isMobile ? { flex: 1, minWidth: 0 } : { width: 180 }}
        />
    );

    const layerSwitches = (
        <>
            {showRailwayLines !== undefined && onShowRailwayLinesChange && (
                <Switch
                    label="Strecken"
                    checked={showRailwayLines}
                    onChange={(e) => onShowRailwayLinesChange(e.currentTarget.checked)}
                    size={isMobile ? "md" : "sm"}
                />
            )}
            <Switch
                label="Wahlkreise"
                checked={showConstituencies}
                onChange={(e) => onShowConstituenciesChange(e.currentTarget.checked)}
                size={isMobile ? "md" : "sm"}
            />
            <Switch
                label="Nur Hauptprojekte"
                checked={onlySuperior}
                onChange={(e) => onOnlySuperiorChange(e.currentTarget.checked)}
                size={isMobile ? "md" : "sm"}
            />
        </>
    );

    const sizeSliders = (
        <>
            <Stack gap={4}>
                <Text size="xs" c="dimmed">
                    Linienbreite: {lineWidth} px
                </Text>
                <Slider
                    value={lineWidth}
                    onChange={onLineWidthChange}
                    min={1}
                    max={10}
                    step={1}
                    size="sm"
                    style={{ width: isMobile ? "100%" : 140 }}
                />
            </Stack>
            <Stack gap={4}>
                <Text size="xs" c="dimmed">
                    Punktgröße: {pointSize} px
                </Text>
                <Slider
                    value={pointSize}
                    onChange={onPointSizeChange}
                    min={1}
                    max={15}
                    step={1}
                    size="sm"
                    style={{ width: isMobile ? "100%" : 140 }}
                />
            </Stack>
        </>
    );

    // ── Phone: a slim search strip over the map, everything else in a bottom
    //    sheet. A floating panel would cover the map it is meant to control.
    if (isMobile) {
        return (
            <>
                <Box
                    style={{
                        position: "absolute",
                        top: 8,
                        left: 8,
                        right: 8,
                        zIndex: 10,
                        display: "flex",
                        gap: 8,
                        alignItems: "center",
                    }}
                >
                    <Box
                        style={{
                            flex: 1,
                            minWidth: 0,
                            background: "rgba(255, 255, 255, 0.92)",
                            border: "1px solid var(--rule)",
                            boxShadow: "var(--shadow-float)",
                            padding: 4,
                        }}
                    >
                        {searchField}
                    </Box>
                    <ActionIcon
                        onClick={openSheet}
                        size={42}
                        radius={0}
                        variant="filled"
                        color="preussen"
                        aria-label="Karteneinstellungen öffnen"
                        style={{ boxShadow: "var(--shadow-float)" }}
                    >
                        <IconAdjustments size={20} />
                    </ActionIcon>
                </Box>

                {searchTerm && (
                    <Box
                        style={{
                            position: "absolute",
                            top: 60,
                            left: 8,
                            zIndex: 10,
                            background: "rgba(255, 255, 255, 0.92)",
                            border: "1px solid var(--rule)",
                            padding: "2px 6px",
                        }}
                    >
                        <Text size="xs" c="dimmed">
                            {filteredCount} von {totalProjects} Projekten
                        </Text>
                    </Box>
                )}

                <Drawer
                    opened={sheetOpened}
                    onClose={closeSheet}
                    position="bottom"
                    title="Karte einstellen"
                    // A bottom sheet hugs its content instead of filling the screen.
                    styles={{ content: { height: "auto", maxHeight: "85dvh" } }}
                >
                    <Stack gap="md" pb="md">
                        <ChronicleButton
                            onClick={() => {
                                // Both drawers at once would stack — hand over instead.
                                closeSheet();
                                onOpenFilters();
                            }}
                        >
                            Projektgruppen
                        </ChronicleButton>
                        {layerSwitches}
                        {sizeSliders}
                        <ChronicleButton variant="ghost" onClick={closeSheet}>
                            Schließen
                        </ChronicleButton>
                    </Stack>
                </Drawer>
            </>
        );
    }

    // ── Desktop: floating panel in the top-right corner of the map.
    return (
        <Box
            style={{
                position: "absolute",
                top: 12,
                right: 30,
                zIndex: 10,
            }}
        >
            <div
                style={{
                    background: "rgba(255, 255, 255, 0.92)",
                    backdropFilter: "blur(20px)",
                    WebkitBackdropFilter: "blur(20px)",
                    borderRadius: 0,
                    boxShadow: "var(--shadow-float)",
                    padding: "12px",
                    border: "1px solid var(--rule)",
                }}
            >
                <Stack gap="sm">
                    {searchField}
                    {searchTerm && (
                        <Text size="xs" c="dimmed">
                            {filteredCount} von {totalProjects} Projekten
                        </Text>
                    )}
                    <ChronicleButton onClick={onOpenFilters}>
                        Projektgruppen
                    </ChronicleButton>
                    {layerSwitches}
                    {sizeSliders}
                </Stack>
            </div>
        </Box>
    );
}
