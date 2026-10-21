import type { ReactNode } from "react";
import { AppShell } from "@mantine/core";
import { Header } from "./Header";
import { Footer } from "./Footer";

/**
 * Page frame shared by the route Layout and RouteErrorBoundary: header on
 * top, the page, and the footer at the end of the content (pushed to the
 * bottom of the viewport on short pages).
 *
 * Header height follows --header-height (72px, 64px under 48em); padding
 * follows --page-pad so the shell tightens on phones
 * (docs/features/feature-mobile-usability.md). The footer cancels the main
 * padding so it spans the full width.
 */
export function AppFrame({ children }: { children: ReactNode }) {
    return (
        <AppShell header={{ height: "var(--header-height)" }} padding="var(--page-pad)" withBorder={false}>
            <AppShell.Header className="app-header-shell">
                <Header />
            </AppShell.Header>
            <AppShell.Main style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ flex: 1, minWidth: 0 }}>{children}</div>
                <div
                    style={{
                        margin: "var(--page-pad) calc(var(--page-pad) * -1) calc(var(--page-pad) * -1)",
                    }}
                >
                    <Footer />
                </div>
            </AppShell.Main>
        </AppShell>
    );
}
