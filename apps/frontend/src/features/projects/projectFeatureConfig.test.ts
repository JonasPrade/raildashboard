import { describe, it, expect } from "vitest";
import { featureGroups, trainCategoryLabels, type FeatureItem } from "./projectFeatureConfig";
// ---------------------------------------------------------------------------
// featureGroups
// ---------------------------------------------------------------------------

describe("featureGroups", () => {
    it("is a non-empty array", () => {
        expect(featureGroups).toBeInstanceOf(Array);
        expect(featureGroups.length).toBeGreaterThan(0);
    });

    it("every group has a non-empty groupLabel and features array", () => {
        for (const group of featureGroups) {
            expect(typeof group.groupLabel).toBe("string");
            expect(group.groupLabel.length).toBeGreaterThan(0);
            expect(Array.isArray(group.features)).toBe(true);
            expect(group.features.length).toBeGreaterThan(0);
        }
    });

    it("every feature item has a non-empty key and label", () => {
        const allFeatures: FeatureItem[] = featureGroups.flatMap((g) => g.features);
        for (const item of allFeatures) {
            expect(typeof item.key).toBe("string");
            expect(item.key.length).toBeGreaterThan(0);
            expect(typeof item.label).toBe("string");
            expect(item.label.length).toBeGreaterThan(0);
        }
    });

    it("feature keys are unique across all groups", () => {
        const allKeys = featureGroups.flatMap((g) => g.features.map((f) => f.key));
        const uniqueKeys = new Set(allKeys);
        expect(uniqueKeys.size).toBe(allKeys.length);
    });

    it("all feature keys are valid Project property names", () => {
        // This is a type-level guarantee at compile time, but we can verify at
        // runtime that the keys exist as strings and are non-empty.
        const allKeys = featureGroups.flatMap((g) => g.features.map((f) => f.key));
        for (const key of allKeys) {
            expect(typeof key).toBe("string");
        }
    });

    it("contains the expected group labels", () => {
        const labels = featureGroups.map((g) => g.groupLabel);
        expect(labels).toContain("Streckenausbau");
        expect(labels).toContain("Bahnhöfe & Infrastruktur");
        expect(labels).toContain("Signaltechnik & Digitalisierung");
        expect(labels).toContain("Elektrifizierung & Energie");
        expect(labels).toContain("Sonstiges");
    });

    it("contains known feature keys", () => {
        const allKeys = featureGroups.flatMap((g) => g.features.map((f) => f.key));
        expect(allKeys).toContain("nbs");
        expect(allKeys).toContain("etcs");
        expect(allKeys).toContain("elektrification");
        expect(allKeys).toContain("sanierung");
    });
});

// ---------------------------------------------------------------------------
// trainCategoryLabels
// ---------------------------------------------------------------------------

describe("trainCategoryLabels", () => {
    it("has exactly 3 categories", () => {
        expect(trainCategoryLabels).toHaveLength(3);
    });

    it("every category has key, label, and color", () => {
        for (const cat of trainCategoryLabels) {
            expect(typeof cat.key).toBe("string");
            expect(cat.key.length).toBeGreaterThan(0);
            expect(typeof cat.label).toBe("string");
            expect(cat.label.length).toBeGreaterThan(0);
            expect(typeof cat.color).toBe("string");
            expect(cat.color.length).toBeGreaterThan(0);
        }
    });

    it("keys are unique", () => {
        const keys = trainCategoryLabels.map((c) => c.key);
        expect(new Set(keys).size).toBe(keys.length);
    });

    it("contains Fernverkehr, Nahverkehr, and Güterverkehr", () => {
        const labels = trainCategoryLabels.map((c) => c.label);
        expect(labels).toContain("Fernverkehr");
        expect(labels).toContain("Nahverkehr");
        expect(labels).toContain("Güterverkehr");
    });

    it("maps to correct Project boolean keys", () => {
        const keys = trainCategoryLabels.map((c) => c.key);
        expect(keys).toContain("effects_passenger_long_rail");
        expect(keys).toContain("effects_passenger_local_rail");
        expect(keys).toContain("effects_cargo_rail");
    });
});
