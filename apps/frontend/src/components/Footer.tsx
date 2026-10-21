import { Link } from "react-router-dom";
import { useAppSettings } from "../shared/api/queries";

/** Build version, injected by vite.config.ts (short commit SHA or "dev"). */
const APP_VERSION = __APP_VERSION__;

/**
 * Legal page link: an external URL from the app settings wins (opens in a new
 * tab); otherwise the dashboard's own route renders the stored text.
 */
function LegalLink({ url, to, label }: { url: string | null | undefined; to: string; label: string }) {
    const external = url?.trim();
    if (external) {
        return (
            <a href={external} target="_blank" rel="noopener">
                {label}
            </a>
        );
    }
    return <Link to={to}>{label}</Link>;
}

/**
 * Footer of the IDT design (docs/DESIGN.md → Shell): ink with a violet top
 * edge in both colour schemes, inverse logo, version, legal and docs links.
 * Rendered by the Layout on every route and by RouteErrorBoundary.
 */
export function Footer() {
    const { data: settings } = useAppSettings();

    return (
        <footer className="app-footer">
            <img
                className="app-footer__logo"
                src="/logo-idt-inverse.png"
                height={26}
                alt="Initiative Deutschlandtakt"
            />
            <span>Schienendashboard · Fassung {APP_VERSION}</span>
            <nav className="app-footer__links" aria-label="Rechtliches und Dokumentation">
                <LegalLink url={settings?.impressum_url} to="/impressum" label="Impressum" />
                <LegalLink url={settings?.datenschutz_url} to="/datenschutz" label="Datenschutz" />
                <Link to="/documentation">Dokumentation</Link>
            </nav>
        </footer>
    );
}
