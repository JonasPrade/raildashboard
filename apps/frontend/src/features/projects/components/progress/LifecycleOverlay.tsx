import { Alert } from "@mantine/core";
import { Pause, Ban } from "lucide-react";

import { LIFECYCLE_LABEL, type LifecycleStatus } from "./phaseMeta";

type Props = {
    status: LifecycleStatus;
};

/** Banner shown when the lifecycle overlay (PAUSIERT/ABGEBROCHEN) is active.
 * Returns null for AKTIV. The phase stepper is dimmed separately. */
export default function LifecycleOverlay({ status }: Props) {
    if (status === "AKTIV") return null;
    const isAbort = status === "ABGEBROCHEN";
    return (
        <Alert
            // Lifecycle is no "Versäumnis": neutral alert, the icon tells pause from abort.
            color="teal"
            variant="light"
            icon={isAbort ? <Ban size={16} /> : <Pause size={16} />}
            title={`Projekt ${LIFECYCLE_LABEL[status]}`}
        >
            {isAbort
                ? "Dieses Projekt wurde abgebrochen. Der zuletzt bekannte Planungsstand bleibt zur Information erhalten."
                : "Dieses Projekt ist derzeit pausiert. Der zuletzt bekannte Planungsstand bleibt erhalten."}
        </Alert>
    );
}
