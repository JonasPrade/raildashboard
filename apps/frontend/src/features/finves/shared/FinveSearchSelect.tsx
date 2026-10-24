import { Select, type SelectProps } from "@mantine/core";
import { useMemo } from "react";

import { filterProjectOption } from "../../../lib/filterProjectOption";
import { useFinves } from "../../../shared/api/queries";

/** Options rendered at once — the search narrows the rest. */
const MAX_OPTIONS = 50;

type Props = {
    label: string;
    value: number | null;
    onChange: (id: number | null) => void;
    /** FinVes not offered, e.g. those already linked. */
    excludeIds?: number[];
    style?: SelectProps["style"];
};

/** Pick one FinVe, searchable by number and name ("900008 Digitaler Knoten"). */
export default function FinveSearchSelect({ label, value, onChange, excludeIds = [], style }: Props) {
    const { data: finves = [], isLoading } = useFinves();

    const options = useMemo(() => {
        const excluded = new Set(excludeIds);
        return finves
            .filter((f) => !excluded.has(f.id))
            .map((f) => ({
                value: String(f.id),
                label: `${f.id} · ${f.name ?? "ohne Namen"}${f.is_sammel_finve ? " (Sammel-FinVe)" : ""}`,
            }));
    }, [finves, excludeIds]);

    return (
        <Select
            label={label}
            placeholder={isLoading ? "FinVes werden geladen…" : "FinVe-Nummer oder Name"}
            data={options}
            value={value == null ? null : String(value)}
            onChange={(v) => onChange(v == null ? null : Number(v))}
            searchable
            clearable
            filter={filterProjectOption}
            limit={MAX_OPTIONS}
            nothingFoundMessage="Keine FinVe gefunden"
            style={style}
        />
    );
}
