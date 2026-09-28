import { useMediaQuery } from "@mantine/hooks";

/**
 * The two breakpoints the whole app agrees on. They match the Mantine defaults
 * (`sm` = 48em, `md` = 62em) and the media queries in `app.css` / `tokens.css`,
 * so a layout decision made in CSS and one made in JS never disagree.
 *
 * Plan: docs/features/feature-mobile-usability.md
 */
export const MOBILE_QUERY = "(max-width: 48em)";
export const COMPACT_QUERY = "(max-width: 62em)";

/**
 * `true` on phone-sized viewports (< 768px): single column, bottom sheets,
 * full-width dialogs.
 *
 * `useMediaQuery` reports `undefined` before the first match is evaluated; that
 * is normalised to `false` so the desktop layout is the fallback and a wide
 * screen never flashes the mobile shell.
 */
export function useIsMobile(): boolean {
    return useMediaQuery(MOBILE_QUERY, false, { getInitialValueInEffect: false }) ?? false;
}

/**
 * `true` on phones and small tablets (< 992px): burger navigation, stacked
 * filter rows, no side-by-side control panels.
 */
export function useIsCompact(): boolean {
    return useMediaQuery(COMPACT_QUERY, false, { getInitialValueInEffect: false }) ?? false;
}
