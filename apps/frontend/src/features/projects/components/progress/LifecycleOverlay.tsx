import { Alert } from "@mantine/core";
import { IconPlayerPause, IconBan } from "@tabler/icons-react";

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
            color={isAbort ? "red" : "orange"}
            variant="light"
            icon={isAbort ? <IconBan size={18} /> : <IconPlayerPause size={18} />}
            title={`Projekt ${LIFECYCLE_LABEL[status]}`}
        >
            {isAbort
                ? "Dieses Projekt wurde abgebrochen. Der zuletzt bekannte Planungsstand bleibt zur Information erhalten."
                : "Dieses Projekt ist derzeit pausiert. Der zuletzt bekannte Planungsstand bleibt erhalten."}
        </Alert>
    );
}
