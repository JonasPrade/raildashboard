import { Alert, Stack, Text } from "@mantine/core";
import { Pause, Ban } from "lucide-react";

import { formatDateShort } from "../../../../shared/format";
import { LIFECYCLE_LABEL, type LifecycleStatus } from "./phaseMeta";

type Props = {
    status: LifecycleStatus;
    /** Reason and start date of PAUSIERT / ABGEBROCHEN. */
    note?: string | null;
    date?: string | null;
};

/** Banner shown when the lifecycle overlay (PAUSIERT/ABGEBROCHEN) is active,
 * with its reason and start date. Returns null for AKTIV. The phase stepper is
 * dimmed separately. */
export default function LifecycleOverlay({ status, note, date }: Props) {
    if (status === "AKTIV") return null;
    const isAbort = status === "ABGEBROCHEN";
    return (
        <Alert
            // Lifecycle is no "Versäumnis": neutral alert, the icon tells pause from abort.
            color="teal"
            variant="light"
            icon={isAbort ? <Ban size={16} /> : <Pause size={16} />}
            title={`Projekt ${LIFECYCLE_LABEL[status]}${date ? ` seit ${formatDateShort(date)}` : ""}`}
        >
            <Stack gap={4}>
                <Text size="sm">
                    {isAbort
                        ? "Dieses Projekt wurde abgebrochen. Der zuletzt bekannte Planungsstand bleibt zur Information erhalten."
                        : "Dieses Projekt ist derzeit pausiert. Der zuletzt bekannte Planungsstand bleibt erhalten."}
                </Text>
                {note && <Text size="sm">Begründung: {note}</Text>}
            </Stack>
        </Alert>
    );
}
