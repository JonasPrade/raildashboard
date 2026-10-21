import { Skeleton, Stack } from "@mantine/core";

import classes from "./LoadingState.module.css";

export type LoadingStateProps = {
    /** Number of placeholder bars (text-like variant). Default 3. */
    rows?: number;
    /** Block variant: one bar of this height (chart, map, image). */
    height?: number | string;
    /** Accessible label. Default „Lädt …“. */
    label?: string;
};

const ROW_WIDTHS = ["100%", "92%", "76%", "88%", "64%", "96%", "82%", "70%"];

/**
 * Loading state (Anwendungsebene „Lädt“): flat placeholder bars in the shape
 * of the content they stand for. No spinner, no shimmer.
 */
export function LoadingState({ rows = 3, height, label = "Lädt …" }: LoadingStateProps) {
    return (
        <div role="status" aria-busy="true" aria-label={label} data-state="loading">
            {height !== undefined ? (
                <Skeleton
                    data-testid="loading-bar"
                    height={height}
                    radius={0}
                    animate={false}
                    className={classes.bar}
                />
            ) : (
                <Stack gap={10}>
                    {Array.from({ length: Math.max(1, rows) }, (_, i) => (
                        <Skeleton
                            key={i}
                            data-testid="loading-bar"
                            height={13}
                            width={ROW_WIDTHS[i % ROW_WIDTHS.length]}
                            radius={0}
                            animate={false}
                            className={classes.bar}
                        />
                    ))}
                </Stack>
            )}
        </div>
    );
}
