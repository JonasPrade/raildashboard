import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { describe, it, expect } from "vitest";

import { ExternalLinkButton } from "./ExternalLinkButton";

const LONG =
    "https://www.deutschebahn.com/de/presse/pressestart_zentrales_uebersicht/BMV-und-DB-InfraGO-entwickeln-Strategie-der-Korridorsanierungen-umfassend-weiter-14064596";

describe("ExternalLinkButton", () => {
    it("shows the host instead of the raw URL and keeps the URL in href and title", () => {
        render(<MantineProvider><ExternalLinkButton url={LONG} /></MantineProvider>);
        const link = screen.getByRole("link", { name: /Link öffnen · deutschebahn\.com/ });
        expect(link).toHaveAttribute("href", LONG);
        expect(link).toHaveAttribute("title", LONG);
        expect(link).toHaveAttribute("target", "_blank");
        expect(screen.queryByText(LONG)).toBeNull();
    });

    it("prefers a given label", () => {
        render(<MantineProvider><ExternalLinkButton url={LONG} label="Pressemitteilung" /></MantineProvider>);
        expect(screen.getByRole("link", { name: /Pressemitteilung/ })).toHaveAttribute("href", LONG);
    });

    it("falls back to a plain label for unparsable URLs", () => {
        render(<MantineProvider><ExternalLinkButton url="kein link" /></MantineProvider>);
        expect(screen.getByRole("link", { name: "Link öffnen" })).toBeInTheDocument();
    });
});
