import { MultiSelect, type MantineSize } from "@mantine/core";
import type { CSSProperties } from "react";

import { phaseFilterOptions, serializePhaseParam, parsePhaseParam, type PhaseFilterValue } from "./phaseFilter";

const OPTIONS = phaseFilterOptions();

type Props = {
    value: PhaseFilterValue[];
    onChange: (value: PhaseFilterValue[]) => void;
    /** Visible label; omit for the compact map panel (the placeholder explains it). */
    label?: string;
    size?: MantineSize;
    style?: CSSProperties;
};

/**
 * Multi-select for the planning-phase filter on the map/list page. Stateless:
 * the page keeps the selection in the `?phase=` URL param.
 */
export default function PhaseFilterSelect({ value, onChange, label, size = "sm", style }: Props) {
    return (
        <MultiSelect
            label={label}
            aria-label={label ? undefined : "Nach Planungsphase filtern"}
            placeholder={value.length === 0 ? "Alle Phasen" : undefined}
            data={OPTIONS}
            value={value}
            // Normalise (canonical order, only valid values) before handing it up.
            onChange={(next) => onChange(parsePhaseParam(serializePhaseParam(next)))}
            clearable
            size={size}
            style={style}
        />
    );
}
