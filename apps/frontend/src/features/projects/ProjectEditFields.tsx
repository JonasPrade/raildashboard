import {
    Button,
    Divider,
    MultiSelect,
    NumberInput,
    Stack,
    Switch,
    Text,
    Textarea,
    TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Fragment, useMemo, useState } from "react";

import { useProjectGroups } from "../../shared/api/queries";
import { computeGeojsonLengthKm } from "../../shared/geo/length";
import type { ProjectEditFormValues } from "./ProjectEdit";
import {
    PROPERTY_SECTIONS,
    type BoolKey,
    type NumKey,
    type PropField,
} from "./projectPropertyFields";

export type ProjectEditFieldsProps = {
    values: ProjectEditFormValues;
    setValues: React.Dispatch<React.SetStateAction<ProjectEditFormValues>>;
    /** Project geometry (geojson_representation). Enables "Länge aus Geometrie berechnen". */
    geojson?: string | null;
};



function SwitchField({
    label,
    fieldKey,
    values,
    setValues,
}: {
    label: string;
    fieldKey: BoolKey;
    values: ProjectEditFormValues;
    setValues: React.Dispatch<React.SetStateAction<ProjectEditFormValues>>;
}) {
    return (
        <Switch
            label={label}
            checked={values[fieldKey]}
            onChange={(event) => {
                const checked = event.currentTarget.checked;
                setValues((prev) => ({ ...prev, [fieldKey]: checked }));
            }}
        />
    );
}

function NumberField({
    label,
    fieldKey,
    indent,
    values,
    setValues,
}: {
    label: string;
    fieldKey: NumKey;
    indent?: boolean;
    values: ProjectEditFormValues;
    setValues: React.Dispatch<React.SetStateAction<ProjectEditFormValues>>;
}) {
    return (
        <NumberInput
            label={label}
            value={values[fieldKey] ?? ""}
            onChange={(value) =>
                setValues((prev) => ({
                    ...prev,
                    [fieldKey]: typeof value === "number" ? value : null,
                }))
            }
            min={0}
            ml={indent ? "xl" : undefined}
        />
    );
}

export function ProjectEditFields({ values, setValues, geojson }: ProjectEditFieldsProps) {
    const { data: groups = [] } = useProjectGroups();
    const projectGroupOptions = useMemo(
        () => groups.map((g) => ({ value: String(g.id), label: g.name })),
        [groups],
    );

    const [search, setSearch] = useState("");
    const query = search.trim().toLowerCase();
    const matches = (label: string) => query === "" || label.toLowerCase().includes(query);

    const hasLineGeometry = !!geojson;

    const handleComputeLength = () => {
        const km = computeGeojsonLengthKm(geojson);
        if (km == null) {
            notifications.show({
                color: "yellow",
                title: "Keine Linien-Geometrie",
                message: "Aus der Projektgeometrie konnte keine Länge berechnet werden.",
            });
            return;
        }
        setValues((prev) => ({ ...prev, length: km }));
        notifications.show({
            color: "green",
            title: "Länge berechnet",
            message: `Länge aus der Geometrie: ${km.toLocaleString("de-DE")} km`,
        });
    };

    const renderField = (field: PropField) =>
        field.kind === "switch" ? (
            <SwitchField key={field.key} label={field.label} fieldKey={field.key} values={values} setValues={setValues} />
        ) : (
            <NumberField
                key={field.key}
                label={field.label}
                fieldKey={field.key}
                indent={field.indent}
                values={values}
                setValues={setValues}
            />
        );

    return (
        <Stack gap="md">
            <Divider label="Stammdaten" labelPosition="left" />

            <TextInput
                label="Projektname"
                required
                value={values.name}
                onChange={(event) => {
                    const value = event.currentTarget.value;
                    setValues((prev) => ({ ...prev, name: value }));
                }}
            />

            <TextInput
                label="Projektnummer"
                placeholder="z. B. ABS 123"
                value={values.project_number ?? ""}
                onChange={(event) => {
                    const value = event.currentTarget.value;
                    setValues((prev) => ({ ...prev, project_number: value || null }));
                }}
            />

            <div>
                <NumberInput
                    label="Länge in Kilometern"
                    placeholder="z. B. 42,5"
                    value={values.length ?? ""}
                    onChange={(value) =>
                        setValues((prev) => ({
                            ...prev,
                            length: typeof value === "number" ? value : null,
                        }))
                    }
                    decimalScale={2}
                    min={0}
                />
                {hasLineGeometry && (
                    <Button size="xs" variant="light" mt={6} onClick={handleComputeLength}>
                        Aus Geometrie berechnen
                    </Button>
                )}
            </div>

            <Textarea
                label="Beschreibung"
                minRows={3}
                autosize
                value={values.description ?? ""}
                onChange={(event) => {
                    const value = event.currentTarget.value;
                    setValues((prev) => ({ ...prev, description: value || null }));
                }}
            />

            <Textarea
                label="Begründung"
                minRows={2}
                autosize
                value={values.justification ?? ""}
                onChange={(event) => {
                    const value = event.currentTarget.value;
                    setValues((prev) => ({ ...prev, justification: value || null }));
                }}
            />

            <MultiSelect
                label="Projektgruppen"
                placeholder="Gruppen auswählen…"
                data={projectGroupOptions}
                value={values.project_group_ids.map(String)}
                onChange={(selected) =>
                    setValues((prev) => ({
                        ...prev,
                        project_group_ids: selected
                            .map((s) => parseInt(s, 10))
                            .filter((n) => !isNaN(n)),
                    }))
                }
                searchable
                clearable
            />

            <Divider label="Eigenschaften" labelPosition="left" />
            <TextInput
                placeholder="Eigenschaft suchen… (z. B. ETCS, Tunnel, Bahnsteig)"
                value={search}
                onChange={(event) => setSearch(event.currentTarget.value)}
            />

            {(() => {
                const visibleSections = PROPERTY_SECTIONS.map((section) => ({
                    label: section.label,
                    fields: section.fields.filter((f) => matches(f.label)),
                })).filter((section) => section.fields.length > 0);

                if (visibleSections.length === 0) {
                    return (
                        <Text c="dimmed" size="sm">
                            Keine Eigenschaft passt zu „{search}".
                        </Text>
                    );
                }

                return visibleSections.map((section) => (
                    <Fragment key={section.label}>
                        <Divider label={section.label} labelPosition="left" />
                        <Stack gap="xs">{section.fields.map(renderField)}</Stack>
                    </Fragment>
                ));
            })()}
        </Stack>
    );
}

export default ProjectEditFields;
