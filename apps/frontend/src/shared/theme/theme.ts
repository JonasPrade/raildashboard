import {
    Accordion,
    ActionIcon,
    Alert,
    Autocomplete,
    Avatar,
    Badge,
    Button,
    Card,
    Checkbox,
    Chip,
    CloseButton,
    Code,
    Combobox,
    Container,
    createTheme,
    defaultVariantColorsResolver,
    Drawer,
    HoverCard,
    Input,
    InputWrapper,
    Kbd,
    Menu,
    Modal,
    MultiSelect,
    Notification,
    Pagination,
    Paper,
    Pill,
    Popover,
    Progress,
    Radio,
    rem,
    SegmentedControl,
    Select,
    Skeleton,
    Stepper,
    Switch,
    Table,
    Tabs,
    TagsInput,
    Title,
    Tooltip,
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

// ── Colour semantics (Anwendungsebene) ─────────────────────────────────────
// Every Mantine colour name that occurs in the code belongs to one DS family.
// Components resolve their colours from the family, never from Mantine's own
// light/dark palette, so both schemes come from the DS aliases in tokens.css.
type Family = "primary" | "red" | "cyan" | "ink" | "gray" | "green" | "amber";

const FAMILY: Record<string, Family> = {
    violet: "primary",
    indigo: "primary",
    grape: "primary",
    red: "red",
    pink: "red",
    cyan: "cyan",
    teal: "ink",
    blue: "ink",
    dark: "ink",
    gray: "gray",
    green: "green",
    lime: "green",
    yellow: "amber",
    orange: "amber",
};

/** DS family of a Mantine colour prop (`"red"`, `"red.6"`); null for CSS colours. */
export function colorFamily(color: string | undefined, primaryColor = "violet"): Family | null {
    const name = (color ?? primaryColor).split(".")[0];
    return FAMILY[name] ?? null;
}

// Border width comes from the component (`--idt-bw`: 2px on Button/ActionIcon,
// 1px on Badge and everything else), the colour from the family.
const bw = "var(--idt-bw, 1px)";

/** Line colour of a family (light badge frame, outline frame). */
const LINE: Record<Family, string> = {
    primary: "var(--accent-primary)",
    red: "var(--idt-danger)",
    cyan: "var(--idt-cyan-active)",
    ink: "var(--border-frame)",
    gray: "var(--text-muted)",
    green: "var(--idt-success)",
    amber: "var(--idt-warning)",
};

/** Filled surface and its text per family; text reaches 4.5:1 in both schemes. */
const FILLED: Record<Family, { bg: string; hover: string; color: string }> = {
    primary: { bg: "var(--accent-primary)", hover: "var(--accent-primary-hover)", color: "var(--text-on-accent)" },
    red: { bg: "var(--idt-danger-fill)", hover: "var(--idt-danger-fill-hover)", color: "var(--text-on-accent)" },
    cyan: { bg: "var(--idt-cyan)", hover: "var(--idt-cyan-hover)", color: "var(--idt-ink)" },
    ink: { bg: "var(--surface-inverse)", hover: "var(--idt-inverse-hover)", color: "var(--text-on-inverse)" },
    gray: { bg: "var(--text-muted)", hover: "var(--text-strong)", color: "var(--surface)" },
    green: { bg: "var(--idt-success-fill)", hover: "var(--idt-success-fill)", color: "var(--text-on-accent)" },
    amber: { bg: "var(--idt-warning)", hover: "var(--idt-warning)", color: "var(--idt-ink)" },
};

/** Text colour of the borderless variants (subtle, transparent). */
const QUIET: Record<Family, string> = {
    primary: "var(--text-strong)",
    red: "var(--idt-danger-text)",
    cyan: "var(--text-strong)",
    ink: "var(--text-strong)",
    gray: "var(--text-muted)",
    green: "var(--text-strong)",
    amber: "var(--text-strong)",
};

const frame = {
    background: "transparent",
    hover: "var(--surface-alt)",
    color: "var(--text-strong)",
    border: `${bw} solid var(--border-frame)`,
};

const variantColorResolver: VariantColorsResolver = (input) => {
    const family = colorFamily(input.color, input.theme.primaryColor);
    const variant = input.variant ?? "filled";

    if (variant === "default") return { ...frame, hoverColor: "var(--text-strong)" };
    // CSS colours (`color="var(--…)"`, hex) and gradient/white/dot keep Mantine's logic.
    if (!family || !["filled", "light", "outline", "subtle", "transparent"].includes(variant)) {
        return defaultVariantColorsResolver(input);
    }

    switch (variant) {
        case "filled": {
            const f = FILLED[family];
            return { background: f.bg, hover: f.hover, color: f.color, hoverColor: f.color, border: `${bw} solid transparent` };
        }
        case "light": {
            // Tag on a tint: violet/cyan get their soft tint, the rest paper-2;
            // the frame carries the colour, the text stays ink.
            const bg = family === "primary" ? "var(--idt-violet-soft)" : family === "cyan" ? "var(--idt-cyan-soft)" : "var(--surface-alt)";
            return {
                background: bg,
                hover: `color-mix(in srgb, ${bg}, var(--text-strong) 8%)`,
                color: "var(--text-strong)",
                hoverColor: "var(--text-strong)",
                border: `${bw} solid ${LINE[family]}`,
            };
        }
        case "outline":
            if (family === "red") {
                return {
                    background: "transparent",
                    hover: "color-mix(in srgb, var(--idt-danger) 10%, transparent)",
                    color: "var(--idt-danger-text)",
                    hoverColor: "var(--idt-danger-text)",
                    border: `${bw} solid var(--idt-danger)`,
                };
            }
            return { ...frame, hoverColor: "var(--text-strong)" };
        case "subtle":
            return {
                background: "transparent",
                hover: "var(--surface-alt)",
                color: QUIET[family],
                hoverColor: QUIET[family],
                border: `${bw} solid transparent`,
            };
        default: // transparent
            return { background: "transparent", hover: "transparent", color: QUIET[family], hoverColor: QUIET[family], border: `${bw} solid transparent` };
    }
};

/** `idt-tone-<family>` for components whose look depends on the colour prop. Buttons
 *  also carry `idt-v-<variant>`: Mantine drops data-variant on disabled buttons. */
const tone = (color: string | undefined, fallback = "none") => `idt-tone-${colorFamily(color) ?? fallback}`;

// Combobox dropdown of every select-like field (Anwendungsebene → Auswahlfelder).
const comboboxClassNames = {
    dropdown: "idt-combobox-dropdown",
    option: "idt-combobox-option",
    options: "idt-combobox-options",
    empty: "idt-combobox-empty",
    groupLabel: "idt-combobox-group-label",
    optionsDropdownCheckIcon: "idt-combobox-check",
};
const comboboxProps = { offset: 0, shadow: "none" } as const;

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
            h2: { fontSize: rem(19), lineHeight: "1.25" }, // section, 2px ink rule (components.css)
            h3: { fontSize: rem(17), lineHeight: "1.3" },
            h4: { fontSize: rem(16), lineHeight: "1.4" },
        },
    },
    spacing: { xs: rem(4), sm: rem(8), md: rem(16), lg: rem(24), xl: rem(32) },
    // Component rules after the Anwendungsebene (docs/features/feature-idt-design.md →
    // "Stufe 4 — Bausteine"). Colours come from variantColorResolver above, shape
    // and states from the classes in components.css.
    components: {
        // Page gutters follow the --page-pad token, so every Container tightens
        // on phones (docs/features/feature-mobile-usability.md).
        Container: Container.extend({ defaultProps: { px: "var(--page-pad)", size: 1400 } }),

        Button: Button.extend({
            classNames: (_theme, props) => ({
                root: `idt-button ${tone(props.color)} idt-v-${props.variant ?? "filled"}`,
                loader: "idt-button-loader",
            }),
        }),
        ActionIcon: ActionIcon.extend({
            defaultProps: { variant: "default" },
            classNames: (_theme, props) => ({ root: `idt-actionicon ${tone(props.color)} idt-v-${props.variant ?? "default"}` }),
        }),
        CloseButton: CloseButton.extend({ classNames: { root: "idt-close" } }),

        // Fields: Input/InputWrapper style every text-like field (TextInput, Textarea,
        // NumberInput, Select, MultiSelect, Autocomplete, PasswordInput, ColorInput,
        // FileInput, NativeSelect, TagsInput, PillsInput).
        Input: Input.extend({
            classNames: { wrapper: "idt-input-wrapper", input: "idt-input", section: "idt-input-section" },
        }),
        InputWrapper: InputWrapper.extend({
            classNames: {
                label: "idt-input-label",
                description: "idt-input-description",
                error: "idt-input-error",
                required: "idt-input-required",
            },
        }),
        Select: Select.extend({
            defaultProps: { checkIconPosition: "right", comboboxProps },
            classNames: comboboxClassNames,
        }),
        MultiSelect: MultiSelect.extend({
            defaultProps: { checkIconPosition: "right", comboboxProps },
            classNames: comboboxClassNames,
        }),
        Autocomplete: Autocomplete.extend({ defaultProps: { comboboxProps }, classNames: comboboxClassNames }),
        TagsInput: TagsInput.extend({ defaultProps: { comboboxProps }, classNames: comboboxClassNames }),
        Combobox: Combobox.extend({ defaultProps: { offset: 0, shadow: "none" }, classNames: comboboxClassNames }),
        Pill: Pill.extend({ classNames: { root: "idt-pill", remove: "idt-pill-remove" } }),

        Checkbox: Checkbox.extend({
            classNames: { root: "idt-checkbox", input: "idt-checkbox-input", icon: "idt-checkbox-icon", label: "idt-check-label" },
        }),
        Radio: Radio.extend({
            defaultProps: { radius: 0 },
            classNames: { root: "idt-radio", radio: "idt-radio-input", icon: "idt-radio-icon", label: "idt-check-label" },
        }),
        Switch: Switch.extend({
            defaultProps: { radius: 0 },
            classNames: { root: "idt-switch", track: "idt-switch-track", thumb: "idt-switch-thumb", label: "idt-check-label" },
        }),
        SegmentedControl: SegmentedControl.extend({
            defaultProps: { radius: 0 },
            classNames: { root: "idt-sc", indicator: "idt-sc-indicator", control: "idt-sc-control", label: "idt-sc-label" },
        }),
        Chip: Chip.extend({ defaultProps: { radius: 0 }, classNames: { label: "idt-chip-label" } }),

        // Tables: no zebra (forced off), row hover on paper-2. The 2px outer frame
        // comes from the wrapper `.idt-table-frame` (ResponsiveTable).
        Table: Table.extend({
            defaultProps: { striped: false, highlightOnHover: true, withRowBorders: true },
            classNames: { table: "idt-table" },
        }),

        Modal: Modal.extend({
            defaultProps: { centered: true, padding: 18 },
            classNames: {
                root: "idt-modal",
                overlay: "idt-modal-overlay",
                inner: "idt-modal-inner",
                content: "idt-modal-content",
                header: "idt-modal-header",
                title: "idt-modal-title",
                close: "idt-modal-close",
                body: "idt-modal-body",
            },
        }),
        Drawer: Drawer.extend({
            defaultProps: { padding: 18 },
            classNames: {
                root: "idt-drawer",
                overlay: "idt-modal-overlay",
                inner: "idt-drawer-inner",
                content: "idt-drawer-content",
                header: "idt-modal-header",
                title: "idt-modal-title",
                close: "idt-modal-close",
                body: "idt-drawer-body",
            },
        }),

        // W3: frame on paper for every colour; the colour is only the inner edge.
        Alert: Alert.extend({
            classNames: (_theme, props) => ({
                root: `idt-alert ${tone(props.color, "primary")}`,
                title: "idt-alert-title",
                message: "idt-alert-message",
                icon: "idt-alert-icon",
                closeButton: "idt-alert-close",
            }),
        }),
        Badge: Badge.extend({
            classNames: (_theme, props) => ({ root: `idt-badge ${tone(props.color)}`, section: "idt-badge-section" }),
        }),
        // notifications.show({ color }) → green/teal get an ink check instead of a
        // green bar, red gets the 4px danger edge. No caller changes needed.
        Notification: Notification.extend({
            classNames: (_theme, props) => ({
                root: `idt-notification ${tone(props.color, "primary")}`,
                icon: "idt-notification-icon",
                title: "idt-notification-title",
                description: "idt-notification-description",
                closeButton: "idt-notification-close",
            }),
        }),

        Tabs: Tabs.extend({ classNames: { root: "idt-tabs", list: "idt-tabs-list", tab: "idt-tab" } }),
        Paper: Paper.extend({ classNames: { root: "idt-paper" } }),
        Card: Card.extend({ classNames: { root: "idt-paper" } }),
        Title: Title.extend({ classNames: { root: "idt-title" } }),

        Popover: Popover.extend({ defaultProps: { shadow: "none" }, classNames: { dropdown: "idt-popover" } }),
        HoverCard: HoverCard.extend({ defaultProps: { shadow: "none" }, classNames: { dropdown: "idt-popover" } }),
        Menu: Menu.extend({
            defaultProps: { shadow: "none" },
            classNames: { dropdown: "idt-popover idt-menu", item: "idt-menu-item", label: "idt-menu-label", divider: "idt-menu-divider" },
        }),
        Tooltip: Tooltip.extend({ classNames: { tooltip: "idt-tooltip" } }),

        Pagination: Pagination.extend({ classNames: { control: "idt-pagination-control", dots: "idt-pagination-dots" } }),
        Stepper: Stepper.extend({
            classNames: {
                root: "idt-stepper",
                steps: "idt-stepper-steps",
                step: "idt-step",
                stepIcon: "idt-step-icon",
                stepCompletedIcon: "idt-step-completed",
                stepLabel: "idt-step-label",
                stepDescription: "idt-step-description",
                separator: "idt-step-separator",
                verticalSeparator: "idt-step-separator-vertical",
            },
        }),
        Progress: Progress.extend({ classNames: { root: "idt-progress", section: "idt-progress-section" } }),
        // Loading = placeholder bars on paper-3, no shimmer (Anwendungsebene → Zustände).
        Skeleton: Skeleton.extend({ defaultProps: { animate: false, radius: 0 }, classNames: { root: "idt-skeleton" } }),

        Accordion: Accordion.extend({
            classNames: { item: "idt-accordion-item", control: "idt-accordion-control", label: "idt-accordion-label", chevron: "idt-accordion-chevron" },
        }),
        Avatar: Avatar.extend({ defaultProps: { radius: 0 } }),
        Code: Code.extend({ classNames: { root: "idt-code" } }),
        Kbd: Kbd.extend({ classNames: { root: "idt-kbd" } }),
    },
});
