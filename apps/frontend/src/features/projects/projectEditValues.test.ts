import { describe, expect, it } from "vitest";

import type { Project } from "../../shared/api/queries";
import { createInitialValues, createUpdatePayload } from "./ProjectEdit";
import { BOOL_KEYS, NUM_KEYS } from "./projectPropertyFields";

// Minimal project fixture — every property key the derived builders read.
function makeProject(overrides: Partial<Project> = {}): Project {
    return {
        id: 1,
        name: "Testprojekt",
        project_number: null,
        description: null,
        justification: null,
        length: null,
        project_groups: [],
        ...overrides,
    } as Project;
}

describe("createInitialValues", () => {
    it("derives every PROPERTY_SECTIONS key with null/false coercion", () => {
        const values = createInitialValues(makeProject());
        for (const key of BOOL_KEYS) {
            expect(values[key], key).toBe(false);
        }
        for (const key of NUM_KEYS) {
            expect(values[key], key).toBeNull();
        }
    });

    it("keeps set property values", () => {
        const values = createInitialValues(
            makeProject({ nbs: true, new_vmax: 250, number_junction_station: 2 }),
        );
        expect(values.nbs).toBe(true);
        expect(values.new_vmax).toBe(250);
        expect(values.number_junction_station).toBe(2);
    });
});

describe("createUpdatePayload", () => {
    it("trims text fields and maps empty strings to null", () => {
        const values = createInitialValues(makeProject());
        values.name = "  Neues Projekt  ";
        values.project_number = "   ";
        values.description = "  Beschreibung ";
        values.justification = "";
        const payload = createUpdatePayload(values);
        expect(payload.name).toBe("Neues Projekt");
        expect(payload.project_number).toBeNull();
        expect(payload.description).toBe("Beschreibung");
        expect(payload.justification).toBeNull();
    });

    it("normalises non-numeric number-field state to null", () => {
        const values = createInitialValues(makeProject({ new_vmax: 250 }));
        // Mantine's NumberInput can hold "" while the user is typing.
        (values as Record<string, unknown>).etcs_level = "";
        const payload = createUpdatePayload(values);
        expect(payload.new_vmax).toBe(250);
        expect(payload.etcs_level).toBeNull();
    });

    it("carries every derived property key into the payload", () => {
        const values = createInitialValues(makeProject({ abs: true, filling_stations_count: 3 }));
        const payload = createUpdatePayload(values) as Record<string, unknown>;
        for (const key of [...BOOL_KEYS, ...NUM_KEYS]) {
            expect(key in payload, key).toBe(true);
        }
        expect(payload.abs).toBe(true);
        expect(payload.filling_stations_count).toBe(3);
    });
});
