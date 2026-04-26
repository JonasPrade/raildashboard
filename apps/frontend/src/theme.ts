import { createTheme, type MantineColorsTuple } from "@mantine/core";

const preussen: MantineColorsTuple = [
    "#e9edf4", "#c5d0e0", "#9eb1c9", "#7793b3", "#5a7ba1",
    "#3d6390", "#274a76", "#19365b", "#0f2347", "#08152d",
];

const gold: MantineColorsTuple = [
    "#fbf2dc", "#f4dfa6", "#edcb73", "#e6b941", "#dba716",
    "#c98a00", "#a87100", "#7a5300", "#523700", "#2c1e00",
];

const ink: MantineColorsTuple = [
    "#f3f1ec", "#dedad0", "#b8b2a3", "#7a8390", "#3d4550",
    "#1b2028", "#111418", "#0d1013", "#08090c", "#000000",
];

export const theme = createTheme({
    primaryColor: "preussen",
    primaryShade: 8,
    defaultRadius: 0,
    colors: {
        preussen,
        gold,
        ink,
    },
    fontFamily: '"IBM Plex Sans", "Inter", -apple-system, BlinkMacSystemFont, sans-serif',
    fontFamilyMonospace: '"IBM Plex Mono", "JetBrains Mono", ui-monospace, monospace',
    headings: {
        fontFamily: '"Archivo Narrow", "Oswald", Impact, sans-serif',
        fontWeight: "700",
        sizes: {
            h1: { fontSize: "40px", lineHeight: "1" },
            h2: { fontSize: "26px", lineHeight: "1.05" },
            h3: { fontSize: "20px", lineHeight: "1.1" },
            h4: { fontSize: "16px", lineHeight: "1.15" },
        },
    },
});
