import {
    Container,
    createTheme,
    defaultVariantColorsResolver,
    rem,
    type MantineColorsTuple,
    type VariantColorsResolver,
} from "@mantine/core";

// Mantine scales mixed from the DS colours (docs/features/feature-idt-design.md →
// "Mantine-Theme"). Index 0 lightest, 9 darkest; the DS token sits at the index
// Mantine uses (6 = filled, 0 = light, 7/8 = hover/active).
const violet: MantineColorsTuple = ["#e8e3ff", "#d8caf3", "#c3b1f4", "#ae99f6", "#9981f7", "#8368f9", "#6e50fa", "#5a3de6", "#4a2fcc", "#1c2854"];
const cyan: MantineColorsTuple = ["#d6f8ff", "#bbe1e3", "#96d5db", "#70c9d4", "#00dcfa", "#25b2c5", "#00a6be", "#008396", "#00606e", "#003d45"];
const teal: MantineColorsTuple = ["#efeae5", "#cacecc", "#aeb8b8", "#91a2a4", "#748c90", "#57767c", "#3a6068", "#2c4e55", "#00373c", "#002326"];
const gray: MantineColorsTuple = ["#fbede6", "#f3e2da", "#e2d3cb", "#c9b6ac", "#a89a92", "#7d7470", "#585857", "#3a6068", "#00373c", "#002326"];
const red: MantineColorsTuple = ["#fce8e2", "#f4c7c2", "#eeada9", "#e89390", "#e27977", "#dc5f5e", "#d64545", "#a03a3b", "#6b3031", "#362527"];
const green: MantineColorsTuple = ["#edede4", "#c3d9c8", "#a2c9b2", "#82ba9d", "#61aa87", "#409a71", "#1f8a5b", "#176e4c", "#10523c", "#08362c"];
const amber: MantineColorsTuple = ["#f7ebdd", "#e4d1b0", "#d5bd8d", "#c6a86a", "#e8a100", "#a97f23", "#9a6b00", "#745707", "#4d420e", "#262e16"];

// A filled primary surface follows the DS aliases in both schemes: violet with
// paper text in light, #ad9bff with ink text in dark. Mantine would otherwise
// derive the text colour once from the light scale (always paper).
const variantColorResolver: VariantColorsResolver = (input) => {
    const resolved = defaultVariantColorsResolver(input);
    const color = input.color ?? input.theme.primaryColor;
    if (input.variant === "filled" && color === input.theme.primaryColor) {
        return {
            ...resolved,
            background: "var(--accent-primary)",
            hover: "var(--accent-primary-hover)",
            color: "var(--text-on-accent)",
        };
    }
    return resolved;
};

export const theme = createTheme({
    primaryColor: "violet",
    primaryShade: 6,
    autoContrast: true, // paper or ink text per surface (cyan gets ink)
    luminanceThreshold: 0.35,
    variantColorResolver,
    defaultRadius: 0,
    radius: { xs: "0", sm: "0", md: "0", lg: "0", xl: "0" },
    colors: {
        violet,
        cyan,
        teal,
        gray,
        red,
        green,
        // Mantine default names that occur in the code, mapped onto DS scales:
        blue: teal,
        indigo: violet,
        grape: violet,
        pink: red,
        orange: amber,
        yellow: amber,
        lime: green,
        dark: teal,
        // Direction-F scale names still used as `color=` props; they are rewritten
        // to names in stages 3/4 (feature-idt-design.md, Q13) and these aliases go then.
        preussen: violet,
        gold: amber,
        ink: teal,
    },
    black: "#00373c",
    white: "#fff6f0",
    fontFamily: "'InterVariable', 'Inter', system-ui, sans-serif",
    fontFamilyMonospace: "'InterVariable', 'Inter', system-ui, sans-serif",
    fontSizes: { xs: rem(13), sm: rem(13.5), md: rem(16), lg: rem(19), xl: rem(21) },
    lineHeights: { xs: "1.4", sm: "1.45", md: "1.5", lg: "1.3", xl: "1.2" },
    headings: {
        fontFamily: "'InterVariable', 'Inter', system-ui, sans-serif",
        fontWeight: "700",
        sizes: {
            h1: { fontSize: rem(21), lineHeight: "1.2" }, // view title
            h2: { fontSize: rem(19), lineHeight: "1.25" }, // section (2px ink rule in stage 4)
            h3: { fontSize: rem(17), lineHeight: "1.3" },
            h4: { fontSize: rem(16), lineHeight: "1.4" },
        },
    },
    spacing: { xs: rem(4), sm: rem(8), md: rem(16), lg: rem(24), xl: rem(32) },
    components: {
        // Page gutters follow the --page-pad token, so every Container tightens
        // on phones (docs/features/feature-mobile-usability.md).
        Container: Container.extend({ defaultProps: { px: "var(--page-pad)", size: 1400 } }),
        // Component rules follow in stage 4 (table in the feature file).
    },
});
