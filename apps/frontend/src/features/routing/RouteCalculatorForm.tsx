import { useState } from "react";
import {
    ActionIcon,
    Button,
    Checkbox,
    Group,
    Stack,
    Text,
} from "@mantine/core";
import type { OperationalPointRef, RouteNetworks, RoutePreviewFeature } from "../../shared/api/queries";
import { useCalculateRoute } from "../../shared/api/queries";
import { NO_EXTRA_NETWORKS } from "./geometryOrigin";
import StationSelect from "./StationSelect";

type Props = {
    onResult: (feature: RoutePreviewFeature, stations: OperationalPointRef[]) => void;
    onError: (message: string) => void;
    /** Compare the route with this project's lines (deviation in the result). */
    compareProjectId?: number;
};

export default function RouteCalculatorForm({ onResult, onError, compareProjectId }: Props) {
    const [start, setStart] = useState<OperationalPointRef | null>(null);
    const [end, setEnd] = useState<OperationalPointRef | null>(null);
    const [viaList, setViaList] = useState<Array<OperationalPointRef | null>>([]);
    // Off by default: the route then never touches a track that is not in operation.
    const [networks, setNetworks] = useState<RouteNetworks>(NO_EXTRA_NETWORKS);
    const usesPlanned = networks.construction || networks.proposed;

    const { mutate: calculate, isPending } = useCalculateRoute();

    function addVia() {
        setViaList((prev) => [...prev, null]);
    }

    function removeVia(index: number) {
        setViaList((prev) => prev.filter((_, i) => i !== index));
    }

    function updateVia(index: number, op: OperationalPointRef | null) {
        setViaList((prev) => prev.map((v, i) => (i === index ? op : v)));
    }

    function buildWaypoints() {
        const stations = [start, ...viaList, end];
        return stations
            .filter((op): op is OperationalPointRef =>
                op !== null && op.latitude !== null && op.longitude !== null,
            )
            .map((op) => ({ lat: op.latitude!, lon: op.longitude! }));
    }

    function handleCalculate() {
        const waypoints = buildWaypoints();
        if (waypoints.length < 2) {
            onError("Start- und Zielbahnhof müssen angegeben werden.");
            return;
        }
        const stations = [start, ...viaList, end].filter(
            (op): op is OperationalPointRef =>
                op !== null && op.latitude !== null && op.longitude !== null,
        );
        calculate(
            { waypoints, networks, compare_project_id: compareProjectId },
            {
                onSuccess: (feature) => onResult(feature, stations),
                onError: (err) => {
                    const status = (err as { status?: number }).status;
                    if (status === 502) {
                        onError("Routing-Dienst nicht erreichbar.");
                    } else if (status === 422) {
                        onError(usesPlanned
                            ? "Kein Pfad gefunden. Die gewählten Gleise verbinden Start und Ziel nicht durchgehend (Lücke in OSM?)."
                            : "Kein Pfad gefunden.");
                    } else {
                        onError("Fehler bei der Routenberechnung.");
                    }
                },
            },
        );
    }

    const canCalculate = start !== null && end !== null && !isPending;

    return (
        <Stack gap="sm">
            <StationSelect label="Startbahnhof" value={start} onChange={setStart} />

            {viaList.map((via, i) => (
                <Group key={i} align="flex-end" gap="xs">
                    <div style={{ flex: 1 }}>
                        <StationSelect
                            label={`Via ${i + 1}`}
                            value={via}
                            onChange={(op) => updateVia(i, op)}
                        />
                    </div>
                    <ActionIcon
                        variant="subtle"
                        color="red"
                        onClick={() => removeVia(i)}
                        mb={1}
                        aria-label="Via entfernen"
                    >
                        ×
                    </ActionIcon>
                </Group>
            ))}

            <Button variant="subtle" size="xs" onClick={addVia} style={{ alignSelf: "flex-start" }}>
                + Via-Bahnhof hinzufügen
            </Button>

            <StationSelect label="Zielbahnhof" value={end} onChange={setEnd} />

            <Stack gap={6}>
                <Text size="sm" fw={500}>Auch nutzen</Text>
                <Checkbox
                    label="Gleise im Bau (OSM)"
                    checked={networks.construction}
                    onChange={(e) => setNetworks((n) => ({ ...n, construction: e.currentTarget.checked }))}
                />
                <Checkbox
                    label="Geplante Gleise (OSM)"
                    checked={networks.proposed}
                    onChange={(e) => setNetworks((n) => ({ ...n, proposed: e.currentTarget.checked }))}
                />
                <Text size="xs" c="dimmed">
                    {usesPlanned
                        ? "Für Neubaustrecken, die OpenStreetMap schon erfasst: Die gewählten Gleise werden vor parallelen Bestandsstrecken bevorzugt. Mit Via-Bahnhöfen lässt sich der Korridor erzwingen."
                        : "Ohne Auswahl führt die Route nur über Gleise in Betrieb."}
                </Text>
            </Stack>

            <Button
                onClick={handleCalculate}
                loading={isPending}
                disabled={!canCalculate}
                mt="xs"
            >
                Route berechnen
            </Button>
        </Stack>
    );
}
